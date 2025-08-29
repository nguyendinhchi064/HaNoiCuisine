from sqladmin import ModelView
from sqlalchemy import func
from sqlalchemy import inspect as sa_inspect
from geoalchemy2.types import Geometry
from app.models import models

# ---------- helpers ----------
def _pk_columns(model):
    try:
        return list(sa_inspect(model).primary_key)  
    except Exception:
        return []

def _pk_first_attr(model):
    """Return the first PK as a mapped attribute, or None."""
    try:
        pks = _pk_columns(model)
        if not pks:
            return None
        name = pks[0].name
        return getattr(model, name, None)
    except Exception:
        return None

def _attrs(model, names):
    """Return mapped attributes that exist (skip missing)."""
    return [getattr(model, n) for n in names if hasattr(model, n)]

def _safe_sort(model, prefer_names, desc=True):
    cand = _attrs(model, prefer_names)
    if cand:
        return [(cand[0], desc)]
    pk_attr = _pk_first_attr(model)
    return [(pk_attr, desc)] if pk_attr is not None else []


# ---------- Users ----------
class UserAdmin(ModelView, model=models.User):
    identity = "user"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    pk_columns = _pk_columns(models.User)
    column_list = _attrs(models.User, [
        "id", "email", "name", "phone", "role", "is_active", "created_at", "updated_at"
    ])
    column_searchable_list = _attrs(models.User, ["email", "name", "phone"])
    column_default_sort = _safe_sort(models.User, ["created_at", "id"], desc=True)

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Places ----------
class PlaceAdmin(ModelView, model=models.Place):
    identity = "place"
    name_plural = "Places"
    icon = "fa-solid fa-location-dot"

    pk_columns = _pk_columns(models.Place)
    lon_expr = func.ST_X(models.Place.geom.cast(Geometry("POINT", 4326))).label("lon")
    lat_expr = func.ST_Y(models.Place.geom.cast(Geometry("POINT", 4326))).label("lat")

    column_list = (
        _attrs(models.Place, [
            "id", "name", "description", "address", "ward", "district", "city",
            "phone", "website", "price_level", "rating", "slug", "is_public",
            "status", "share_token", "published_at", "created_at", "updated_at"
        ]) + [lon_expr, lat_expr]
    )
    column_searchable_list = _attrs(models.Place, ["name", "address", "ward", "district", "city", "phone", "website", "slug"])
    column_filters = _attrs(models.Place, ["status", "is_public", "city", "district"])
    column_default_sort = _safe_sort(models.Place, ["created_at", "id"], desc=True)

    form_excluded_columns = _attrs(models.Place, ["geom", "created_at", "updated_at", "published_at"])

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Categories ----------
class CategoryAdmin(ModelView, model=models.Category):
    identity = "category"
    name_plural = "Categories"
    icon = "fa-regular fa-list"

    pk_columns = _pk_columns(models.Category)
    column_list = _attrs(models.Category, ["id", "slug", "title"])
    column_searchable_list = _attrs(models.Category, ["slug", "title"])
    column_default_sort = _safe_sort(models.Category, ["id"], desc=True)

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- PlaceCategory (composite PK) ----------
class PlaceCategoryAdmin(ModelView, model=models.PlaceCategory):
    identity = "place-category"
    name_plural = "Place Categories"
    icon = "fa-regular fa-square"

    pk_columns = _pk_columns(models.PlaceCategory) or _attrs(models.PlaceCategory, ["place_id", "category_id"])
    column_list = _attrs(models.PlaceCategory, ["place_id", "category_id"])
    column_default_sort = _safe_sort(models.PlaceCategory, ["place_id"], desc=False)
    column_searchable_list = []

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Opening Hours ----------
class OpeningHourAdmin(ModelView, model=models.OpeningHour):
    identity = "opening-hour"
    name_plural = "Opening Hours"
    icon = "fa-regular fa-clock"

    pk_columns = _pk_columns(models.OpeningHour)
    column_list = _attrs(models.OpeningHour, ["id", "place_id", "weekday", "opens", "closes"])
    column_default_sort = _safe_sort(models.OpeningHour, ["place_id"], desc=False)
    column_searchable_list = []

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Menus ----------
class MenuAdmin(ModelView, model=models.Menu):
    identity = "menu"
    name_plural = "Menus"
    icon = "fa-regular fa-folder"

    pk_columns = _pk_columns(models.Menu)
    column_list = _attrs(models.Menu, ["id", "place_id", "title"])
    column_searchable_list = _attrs(models.Menu, ["title"])
    column_default_sort = _safe_sort(models.Menu, ["id"], desc=True)

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Menu Items (exclude ARRAY 'tags' in form) ----------
class MenuItemAdmin(ModelView, model=models.MenuItem):
    identity = "menu-item"
    name_plural = "Menu Items"
    icon = "fa-regular fa-square-plus"

    pk_columns = _pk_columns(models.MenuItem)
    column_list = _attrs(models.MenuItem, ["id", "menu_id", "name", "description", "price", "tags"])
    column_searchable_list = _attrs(models.MenuItem, ["name", "description"])
    column_default_sort = _safe_sort(models.MenuItem, ["id"], desc=True)

    form_excluded_columns = _attrs(models.MenuItem, ["tags"])

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Reviews ----------
class ReviewAdmin(ModelView, model=models.Review):
    identity = "review"
    name_plural = "Reviews"
    icon = "fa-regular fa-comment"

    pk_columns = _pk_columns(models.Review)
    column_list = _attrs(models.Review, ["id", "place_id", "user_id", "rating", "content", "created_at"])
    column_searchable_list = _attrs(models.Review, ["content"])
    column_default_sort = _safe_sort(models.Review, ["created_at", "id"], desc=True)

    form_excluded_columns = _attrs(models.Review, ["created_at"])

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Weather Cache ----------
class WeatherCacheAdmin(ModelView, model=models.WeatherCache):
    identity = "weather-cache"
    name_plural = "Weather Cache"
    icon = "fa-regular fa-cloud"

    pk_columns = _pk_columns(models.WeatherCache)
    column_list = _attrs(models.WeatherCache, [
        "id", "lat", "lon", "ts_hour", "temp_c", "feels_like_c", "humidity", "condition"
    ])
    column_searchable_list = _attrs(models.WeatherCache, ["condition"])
    column_default_sort = _safe_sort(models.WeatherCache, ["ts_hour", "id"], desc=True)

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True


# ---------- Place Weather Score ----------
class PlaceWeatherScoreAdmin(ModelView, model=models.PlaceWeatherScore):
    identity = "place-weather-score"
    name_plural = "Place Weather Scores"
    icon = "fa-regular fa-sun"

    pk_columns = _pk_columns(models.PlaceWeatherScore) or _attrs(models.PlaceWeatherScore, ["place_id", "weather_bucket"])
    column_list = _attrs(models.PlaceWeatherScore, ["place_id", "weather_bucket", "score"])
    column_searchable_list = _attrs(models.PlaceWeatherScore, ["weather_bucket"])
    column_default_sort = _safe_sort(models.PlaceWeatherScore, ["place_id"], desc=False)

    can_view_details = True
    can_create = True
    can_edit = True
    can_delete = True
