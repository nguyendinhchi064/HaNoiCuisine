from sqladmin import Admin
from app.database import engine
from app.services.admin.auth import AdminAuth
from app.services.admin.crud import (
    UserAdmin,
    PlaceAdmin,
    CategoryAdmin,
    PlaceCategoryAdmin,
    OpeningHourAdmin,
    MenuAdmin,
    MenuItemAdmin,
    ReviewAdmin,
    WeatherCacheAdmin,
    PlaceWeatherScoreAdmin,
)
import os

def init_admin(app):
    secret = os.getenv("ADMIN_SECRET", "foodmapisthebest")
    auth = AdminAuth(secret_key=secret)

    admin = Admin(app=app, engine=engine, authentication_backend=auth, base_url="/admin")

    admin.add_view(UserAdmin)
    admin.add_view(PlaceAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(PlaceCategoryAdmin)
    admin.add_view(OpeningHourAdmin)
    admin.add_view(MenuAdmin)
    admin.add_view(MenuItemAdmin)
    admin.add_view(ReviewAdmin)
    admin.add_view(WeatherCacheAdmin)
    admin.add_view(PlaceWeatherScoreAdmin)

    return admin
