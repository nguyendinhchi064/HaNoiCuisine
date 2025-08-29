from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ---------- Places ----------
class PlaceBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = "Hà Nội"
    phone: Optional[str] = None
    website: Optional[str] = None
    price_level: Optional[int] = Field(None, ge=1, le=5)
    rating: Optional[float] = Field(None, ge=0, le=5)
    is_public: Optional[bool] = False
    status: Optional[str] = "pending"
    slug: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    category_slugs: Optional[List[str]] = None


class PlaceCreate(PlaceBase):
    # keep all base fields available for the endpoint mapping
    # just add the nested collections
    opening_hours: List[OpeningHourIn] = Field(default_factory=list)
    menus: List[MenuIn] = Field(default_factory=list)

class PlaceUpdate(PlaceBase):
    name: Optional[str] = None
    address: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None

class PlaceOut(PlaceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    class Config:
        from_attributes = True

# ---------- GeoJSON ----------
class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

class OpeningHourIn(BaseModel):
    weekday: int
    opens: str  # "09:00"
    closes: str # "21:00"

class MenuItemIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    tags: Optional[List[str]] = None

class MenuIn(BaseModel):
    title: Optional[str] = None
    items: List[MenuItemIn] = Field(default_factory=list)

