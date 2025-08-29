import os, json, httpx
from fastapi import HTTPException
import redis

_r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)

def fetch_weather_cached(lat: float, lon: float, ttl_sec: int = 900) -> dict:
    key = f"weather:{round(lat,3)}:{round(lon,3)}"
    cached = _r.get(key)
    if cached:
        return json.loads(cached)

    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENWEATHER_API_KEY is not set")

    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "vi"}
    with httpx.Client(timeout=10) as client:
        r = client.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        if r.status_code == 401:
            raise HTTPException(status_code=401, detail="OpenWeather: Unauthorized (check/activate API key)")
        r.raise_for_status()
        payload = r.json()

    _r.setex(key, ttl_sec, json.dumps(payload))
    return payload

def parse_weather(payload: dict) -> tuple[float, float, int, str]:
    temp = float(payload["main"]["temp"])
    feels = float(payload["main"]["feels_like"])
    hum = int(payload["main"]["humidity"])
    cond = (payload["weather"][0]["main"] or "").lower()
    return temp, feels, hum, cond

def bucket_from(feels_like_c: float, condition: str) -> str:
    c = condition.lower()
    if "rain" in c or "drizzle" in c or "thunderstorm" in c: return "rain"
    if feels_like_c >= 32: return "hot"
    if 27 <= feels_like_c < 32: return "warm"
    if 20 <= feels_like_c < 27: return "cool"
    return "cold"

def suggestion(bucket: str) -> tuple[str, list[str]]:
    m = {
        "hot":  ("Trời nóng — ưu tiên đồ mát: nước mía, sâm lạnh, trà chanh; chè/kem; đồ cuốn.", 
                 ["nước mía","sâm lạnh","trà chanh","chè","kem","gỏi cuốn","bún chả"]),
        "warm": ("Trời ấm — món nhẹ/thanh: bún chả cá, phở cuốn, bún nem; trà trái cây, sữa chua.",
                 ["bún chả cá","phở cuốn","bún nem","trà trái cây","sữa chua"]),
        "cool": ("Se lạnh — món nóng: phở, bún riêu, bún chả; đồ uống nóng.",
                 ["phở","bún riêu","bún chả","cacao","trà nóng"]),
        "cold": ("Lạnh — ấm bụng: lẩu, phở đậm, bún bò Huế; đồ nóng.",
                 ["lẩu","phở","bún bò Huế","trà nóng","cacao"]),
        "rain": ("Mưa — ưu tiên quán gần/có mái hoặc đặt giao.",
                 ["gần đây","giao hàng","phở","bún riêu","cháo","mì nóng"]),
    }
    return m.get(bucket, ("Thời tiết dễ chịu — tuỳ chọn.", ["phở cuốn","bún thịt nướng","chè","trà"]))
