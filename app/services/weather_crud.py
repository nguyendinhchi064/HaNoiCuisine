from typing import Sequence, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import models

def haversine_km(db: Session, lat: float, lon: float):
    point_wkt = func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})")
    return point_wkt

def find_places_for_bucket(
    db: Session,
    bucket: str,
    city_like: str = "hà nội",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    limit: int = 12,
):
    P, S = models.Place, models.PlaceWeatherScore
    q = db.query(P).join(S, S.place_id == P.id).filter(
        S.weather_bucket == bucket,
        P.is_public.is_(True),
        P.status == "approved"
    )

    if hasattr(P, "city") and city_like:
        q = q.filter(func.lower(P.city).like(f"%{city_like.lower()}%"))

    # Distance filter if lat/lon provided
    if lat is not None and lon is not None and radius_km:
        user_pt = haversine_km(db, lat, lon)
        # ST_DWithin(geog1, geog2, meters)
        q = q.filter(func.ST_DWithin(P.geom, user_pt, radius_km * 1000))

        # Optionally order by distance first, then weather score
        q = q.order_by(func.ST_Distance(P.geom, user_pt).asc(), S.score.desc())
    else:
        q = q.order_by(S.score.desc(), P.rating.desc().nullslast())

    return q.limit(limit).all()
