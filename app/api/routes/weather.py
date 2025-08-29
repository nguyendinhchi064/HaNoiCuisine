from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo
import datetime

from app.database import get_db
from app.services import weather_crud as crud
from app.schemas.weather_schemas import WeatherTodayOut, PlaceOut
from app.services.weather import fetch_weather_cached, parse_weather, bucket_from, suggestion

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/today", response_model=WeatherTodayOut)
def weather_today(
    db: Session = Depends(get_db),
    lat: float = Query(21.0278),
    lon: float = Query(105.8342),
    radius_km: float | None = Query(3.0),
    ttl_sec: int = Query(900, ge=60, le=7200),  
    include_raw: bool = Query(False),
):
    raw = fetch_weather_cached(lat, lon, ttl_sec=ttl_sec)
    t, f, h, cond = parse_weather(raw)
    bucket = bucket_from(f, cond)
    text, tags = suggestion(bucket)

    places = crud.find_places_for_bucket(db, bucket=bucket, lat=lat, lon=lon, radius_km=radius_km, limit=12)
    out_places = [PlaceOut(
        id=p.id, name=p.name, address=p.address, district=p.district, city=p.city,
        rating=float(p.rating) if p.rating is not None else None
    ) for p in places]

    day = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat()
    return WeatherTodayOut(
        city="Hà Nội", day=day, temp_c=t, feels_like_c=f, humidity=h,
        condition=cond, bucket=bucket, suggestion_text=text, suggestion_tags=tags,
        places=out_places, raw=raw if include_raw else None
    )
