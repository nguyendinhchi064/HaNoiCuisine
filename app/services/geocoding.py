import os
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
UA_DEFAULT = "FoodMap/1.0 (contact: admin@example.com)"
HEADERS = {"User-Agent": os.getenv("GEOCODER_UA", UA_DEFAULT)}

def geocode_address(*, address: str, ward: str|None=None, district: str|None=None,
                    city: str|None="Hà Nội", country: str="Vietnam", timeout=5.0):
    if not address and not (ward or district or city):
        return None
    parts = [address, ward, district, city, country]
    params = {"q": ", ".join([p for p in parts if p]),
              "format": "json", "addressdetails": 0, "limit": 1,"countrycodes": "vn"}
    resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
