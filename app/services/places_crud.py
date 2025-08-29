from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, literal, asc, desc
from sqlalchemy.orm import selectinload
from datetime import time as _time
from app.models import models
from app.schemas import places_schemas
from geoalchemy2.types import Geometry

try:
    from app.services.geocoding import geocode_address  # returns {"lat": ..., "lon": ...}
except Exception:  
    geocode_address = None


def slugify(name: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")
    return s.lower()

def upsert_categories_by_slugs(db: Session, slugs: Optional[List[str]]) -> List[models.Category]:
    if not slugs:
        return []
    existing = (
        db.query(models.Category)
        .filter(models.Category.slug.in_([s.lower() for s in slugs]))
        .all()
    )
    found = {c.slug: c for c in existing}
    result = []
    for s in slugs:
        s = s.lower()
        if s in found:
            result.append(found[s])
        else:
            cat = models.Category(slug=s, title=s.replace("-", " ").title())
            db.add(cat)
            result.append(cat)
    db.flush()
    return result

def set_point(place: models.Place, lon: float, lat: float):
    # Geography(Point, 4326) — NOTE: lon first!
    place.geom = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)

def _parse_hhmm(s: str) -> _time:
    # accepts "09:00" or "09:00:00"
    return _time.fromisoformat(s if len(s) > 5 else f"{s}:00")

def _build_opening_hours(data: Optional[List[dict]]) -> List[models.OpeningHour]:
    if not data:
        return []
    out: List[models.OpeningHour] = []
    for oh in data:
        out.append(
            models.OpeningHour(
                weekday=int(oh["weekday"]),
                opens=_parse_hhmm(oh["opens"]),
                closes=_parse_hhmm(oh["closes"]),
            )
        )
    return out

def _build_menus(data: Optional[List[dict]]) -> List[models.Menu]:
    if not data:
        return []
    menus: List[models.Menu] = []
    for m in data:
        menu = models.Menu(title=m.get("title"))
        items = []
        for it in (m.get("items") or []):
            items.append(
                models.MenuItem(
                    name=it["name"],
                    description=it.get("description"),
                    price=it.get("price"),
                    tags=it.get("tags"),
                )
            )
        menu.items = items
        menus.append(menu)
    return menus

def _geocode_for_place(address: Optional[str], ward: Optional[str], district: Optional[str], city: Optional[str]):
    if geocode_address is None:
        return None, None
    if not (address or ward or district or city):
        return None, None
    geo = geocode_address(address=address or "", ward=ward, district=district, city=city or "Hà Nội")
    if not geo:
        return None, None
    return float(geo["lat"]), float(geo["lon"])

def create_place(
    db: Session, *, name: str, description: Optional[str] = None, address: Optional[str] = None, ward: Optional[str] = None,
    district: Optional[str] = None, city: Optional[str] = "Hà Nội", phone: Optional[str] = None, website: Optional[str] = None, price_level: Optional[int] = None,
    rating: Optional[float] = None, is_public: bool = False, status: str = "pending", lat: float | None = None, lon: float | None = None,
    category_slugs: Optional[List[str]] = None, opening_hours: Optional[List[dict]] = None, menus: Optional[List[dict]] = None, created_by: Optional[int] = None,
) -> models.Place:
    # 1) find existing (case-insensitive) by (name, address, city)
    existing = (
        db.query(models.Place)
        .filter(
            func.lower(models.Place.name) == name.lower(),
            func.lower(models.Place.address) == (address or "").lower(),
            func.lower(models.Place.city) == (city or "Hà Nội").lower(),
        )
        .first()
    )

    if existing:
        # Prefer explicit coords; else geocode if geom missing
        if lat is not None and lon is not None:
            set_point(existing, lon, lat)
        elif existing.geom is None:
            glat, glon = _geocode_for_place(address, ward, district, city)
            if glat is not None and glon is not None:
                set_point(existing, glon, glat)

        # Upsert categories only if provided
        if category_slugs is not None:
            existing.categories = upsert_categories_by_slugs(db, category_slugs)

        # Optional: update simple fields on upsert
        if description is not None: existing.description = description
        if phone is not None:       existing.phone = phone
        if website is not None:     existing.website = website
        if price_level is not None: existing.price_level = price_level
        if rating is not None:      existing.rating = rating
        if is_public is not None:   existing.is_public = is_public
        if status is not None:      existing.status = status
        if created_by:              existing.updated_by = created_by

        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing  # ← IMPORTANT: do not create a new row

    # 2) create a brand-new place
    place = models.Place(
        name=name,
        description=description,
        address=address,
        ward=ward,
        district=district,
        city=city,
        phone=phone,
        website=website,
        price_level=price_level,
        rating=rating,
        is_public=is_public,
        status=status,
        slug=slugify(name),
        created_by=created_by,
        updated_by=created_by,
    )

    # 3) coords: prefer provided; else geocode; then set geom
    if lat is None or lon is None:
        glat, glon = _geocode_for_place(address, ward, district, city)
        lat = lat if lat is not None else glat
        lon = lon if lon is not None else glon
    if lat is not None and lon is not None:
        set_point(place, lon, lat)

    # 4) relations
    place.categories = upsert_categories_by_slugs(db, category_slugs)
    place.opening_hours = _build_opening_hours(opening_hours)
    place.menus = _build_menus(menus)

    # 5) persist
    db.add(place)
    db.commit()
    db.refresh(place)
    return place

def update_place(
    db: Session,
    place: models.Place,
    *,
    payload: dict,
    updater_id: Optional[int] = None,
) -> models.Place:
    for k, v in payload.items():
        if k in {"lat", "lon", "category_slugs"}:
            continue
        if hasattr(place, k) and v is not None:
            setattr(place, k, v)

    if payload.get("name"):
        place.slug = slugify(payload["name"])

    # If caller gives lat/lon → set; else if address fields updated → try geocode
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is not None and lon is not None:
        set_point(place, lon, lat)
    elif any(k in payload for k in ("address", "ward", "district", "city")):
        glat, glon = _geocode_for_place(
            address=place.address, ward=place.ward, district=place.district, city=place.city
        )
        if glat is not None and glon is not None:
            set_point(place, glon, glat)

    if "category_slugs" in payload:
        place.categories = upsert_categories_by_slugs(db, payload.get("category_slugs"))

    if updater_id:
        place.updated_by = updater_id

    db.add(place)
    db.commit()
    db.refresh(place)
    return place

def delete_place(db: Session, place: models.Place) -> None:
    db.delete(place)
    db.commit()

def get_place(db: Session, place_id: int) -> Optional[models.Place]:
    return db.get(models.Place, place_id)

def get_place_by_slug(db: Session, slug: str) -> Optional[models.Place]:
    return db.query(models.Place).filter(models.Place.slug == slug).first()

def list_places_nearby(
    db: Session, *,
    lon: float | None, lat: float | None,
    radius_m: int | None = None,
    only_public: bool = True, only_approved: bool = True,
    limit: int = 20, offset: int = 0, **filters
):
    q = db.query(models.Place)

    if only_public:
        q = q.filter(models.Place.is_public.is_(True))
    if only_approved:
        q = q.filter(models.Place.status == 'approved')

    if lon is not None and lat is not None:
        ref = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        q = q.filter(models.Place.geom.isnot(None))
        if radius_m:
            q = q.filter(func.ST_DWithin(models.Place.geom, ref, radius_m))
        dist = func.ST_Distance(models.Place.geom, ref).label("distance_m")
        q = q.add_columns(
            dist,
            func.ST_X(models.Place.geom.cast(Geometry("POINT", 4326))).label("lon"),
            func.ST_Y(models.Place.geom.cast(Geometry("POINT", 4326))).label("lat"),
        ).order_by(asc(dist))
    else:
        # Không có điểm tham chiếu: vẫn trả lon/lat để hiển thị
        q = q.add_columns(
            func.null().label("distance_m"),
            func.ST_X(models.Place.geom.cast(Geometry("POINT", 4326))).label("lon"),
            func.ST_Y(models.Place.geom.cast(Geometry("POINT", 4326))).label("lat"),
        ).order_by(desc(models.Place.rating).nullslast())

    rows = q.limit(limit).offset(offset).all()

    out = []
    for r in rows:
        if hasattr(r, "_mapping"):
            m = r._mapping
            place = next((v for v in m.values() if isinstance(v, models.Place)), None)
            out.append((place, m.get("distance_m"), m.get("lon"), m.get("lat")))
        elif isinstance(r, tuple) and len(r) >= 4:
            place, distance_m, plon, plat = r[:4]
            out.append((place, distance_m, plon, plat))
        else:
            # fallback
            place = r[0] if isinstance(r, tuple) else r
            out.append((place, None, None, None))
    return out

def _to_placeout_row(row) -> places_schemas.PlaceOut:
    if hasattr(row, "_mapping"):
        m = row._mapping
        place = next((v for v in m.values() if isinstance(v, models.Place)), None)
        lon = m.get("lon")
        lat = m.get("lat")
    else:
        place, lon, lat = row

    return places_schemas.PlaceOut(
        id=place.id,
        name=place.name,
        description=place.description,
        address=place.address,
        ward=place.ward,
        district=place.district,
        city=place.city,
        phone=place.phone,
        website=place.website,
        price_level=place.price_level,
        rating=float(place.rating) if place.rating is not None else None,
        is_public=place.is_public,
        status=place.status,
        slug=place.slug,
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
        created_by=place.created_by,
        updated_by=place.updated_by,
        created_at=place.created_at,
        updated_at=place.updated_at,
        category_slugs=[c.slug for c in place.categories],
    )
