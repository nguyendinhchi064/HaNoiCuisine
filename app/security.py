from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from app.models import models
from passlib.context import CryptContext
import os


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "600"))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(user: models.User, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": str(user.id),       
        "exp": expire,
        "email": user.email,          
        "role": user.role if hasattr(user, "role") else "user",
        "is_active": user.is_active,
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)