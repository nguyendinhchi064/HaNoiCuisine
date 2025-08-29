from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from geoalchemy2.types import Geometry
from app.database import get_db
from app.services.geocoding import geocode_address
from app.models import models
from app.schemas import places_schemas
from app.services import places_crud
from app.services.places_crud import _to_placeout_row

router = APIRouter(prefix="/places", tags=["places"])

def _to_placeout_with_distance(row, db: Optional[Session] = None) -> places_schemas.PlaceOut:
    if isinstance(row, tuple):
        place, distance_m = row
    else:
        place, distance_m = row, None

    lat = lon = None
    if db is not None and place.geom is not None:
        coord = db.query(
            func.ST_X(models.Place.geom.cast(Geometry("POINT", 4326))).label("lon"),
            func.ST_Y(models.Place.geom.cast(Geometry("POINT", 4326))).label("lat"),
        ).filter(models.Place.id == place.id).first()
        if coord:
            lon = float(coord.lon)
            lat = float(coord.lat)

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
        lat=lat, lon=lon,
        created_by=place.created_by,
        updated_by=place.updated_by,
        created_at=place.created_at,
        updated_at=place.updated_at,
        category_slugs=[c.slug for c in place.categories],
        distance_m=float(distance_m) if distance_m is not None else None,
    )


@router.post("/", response_model=places_schemas.PlaceOut, status_code=status.HTTP_201_CREATED)
def create_place(payload: places_schemas.PlaceCreate, db: Session = Depends(get_db)):
    place = places_crud.create_place(
        db,
        name=payload.name,
        description=payload.description,
        address=payload.address,
        ward=payload.ward,
        district=payload.district,
        city=payload.city,
        phone=payload.phone,
        website=payload.website,
        price_level=payload.price_level,
        rating=payload.rating,
        is_public=payload.is_public or False,
        status=payload.status or "pending",
        lat=payload.lat,
        lon=payload.lon,
        category_slugs=payload.category_slugs,
        opening_hours=[oh.model_dump() for oh in (payload.opening_hours or [])],
        menus=[m.model_dump() for m in (payload.menus or [])],
        created_by=None,
    )
    # now helper reads ST_X/ST_Y from DB
    return _to_placeout_with_distance((place, None), db)

@router.get("/", response_model=List[places_schemas.PlaceOut])
def list_places(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Tìm theo tên/địa chỉ"),
    category: Optional[str] = Query(None, description="Category slug"),
    min_price: Optional[int] = Query(None, ge=1, le=5),
    max_price: Optional[int] = Query(None, ge=1, le=5),
    only_public: bool = True,
    only_approved: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = (
        db.query(
            models.Place,
            func.ST_X(models.Place.geom.cast(Geometry("POINT", 4326))).label("lon"),
            func.ST_Y(models.Place.geom.cast(Geometry("POINT", 4326))).label("lat"),
        )
    )
    if only_public:
        query = query.filter(models.Place.is_public.is_(True))
    if only_approved:
        query = query.filter(models.Place.status == 'approved')

    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.Place.name.ilike(like)) | (models.Place.address.ilike(like))
        )

    if category:
        query = (
            query.join(models.PlaceCategory, models.PlaceCategory.place_id == models.Place.id)
                 .join(models.Category, models.Category.id == models.PlaceCategory.category_id)
                 .filter(models.Category.slug == category)
        )

    if min_price is not None:
        query = query.filter(models.Place.price_level >= min_price)
    if max_price is not None:
        query = query.filter(models.Place.price_level <= max_price)


    query = query.order_by(models.Place.created_at.desc())

    rows = query.limit(limit).offset(offset).all()
    return [_to_placeout_row(r) for r in rows]

@router.get("/map")
def list_places_geojson(
    lon: float, lat: float,
    limit: int = 200,
    radius_km: float | None = None,
    db: Session = Depends(get_db)
):
    radius_m = int(radius_km * 1000) if radius_km else None
    rows = places_crud.list_places_nearby(
        db, lon=lon, lat=lat, radius_m=radius_m,
        only_public=True, only_approved=True,
        limit=limit, offset=0
    )

    features = []
    for place, distance_m, plon, plat in rows:
        if plon is None or plat is None:
            continue  
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(plon), float(plat)]},
            "properties": {
                "id": place.id,
                "name": place.name,
                "address": place.address,
                "district": place.district,
                "city": place.city,
                "distance_m": round(float(distance_m)) if distance_m is not None else None
            },
        })
    return {"type": "FeatureCollection", "features": features}

@router.get("/{place_id}", response_model=places_schemas.PlaceOut)
def get_place(place_id: int, db: Session = Depends(get_db)):
    place = places_crud.get_place(db, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return _to_placeout_with_distance((place, None), db)

@router.patch("/{place_id}", response_model=places_schemas.PlaceOut)
def patch_place(place_id: int, payload: places_schemas.PlaceUpdate, db: Session = Depends(get_db)):
    place = places_crud.get_place(db, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    updated = places_crud.update_place(db,place,payload=payload.model_dump(exclude_unset=True),updater_id=None,)
    return _to_placeout_with_distance((updated, None))

@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place(place_id: int, db: Session = Depends(get_db)):
    place = places_crud.get_place(db, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    places_crud.delete_place(db, place)
    return
