from pydantic import BaseModel
from typing import Optional, Any, List

class PlaceOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    rating: Optional[float] = None

class WeatherTodayOut(BaseModel):
    city: str
    day: str
    temp_c: float
    feels_like_c: float
    humidity: int
    condition: str
    bucket: str
    suggestion_text: str
    suggestion_tags: List[str]
    places: List[PlaceOut]
    raw: Any | None = None
