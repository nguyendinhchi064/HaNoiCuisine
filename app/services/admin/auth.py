from sqladmin.authentication import AuthenticationBackend
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi import Request
from app.database import SessionLocal
from app.models import models
from app.security import verify_password

class AdminAuth(AuthenticationBackend):
    """Session-based auth for SQLAdmin using your Users table."""
    def __init__(self, secret_key: str):
        self.middlewares = [Middleware(SessionMiddleware, secret_key=secret_key)]

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = (form.get("username") or "").lower().strip()
        password = form.get("password") or ""
        with SessionLocal() as db:
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user or not user.is_active:
                return False
            if not verify_password(password, user.password_hash):
                return False
            request.session.update({"admin_user_id": int(user.id)})
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def is_authenticated(self, request: Request) -> bool:
        return "admin_user_id" in request.session

    async def authenticate(self, request: Request) -> bool:
        path = request.url.path
        method = request.method.upper()
        if path.endswith("/login") and method == "POST":
            return await self.login(request)
        if path.endswith("/logout"):
            await self.logout(request)
            return False
        return await self.is_authenticated(request)
