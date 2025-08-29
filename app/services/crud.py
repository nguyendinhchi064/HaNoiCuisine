from sqlalchemy.orm import Session
from app.models import models
from app.security import hash_password, verify_password

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, *, name: str | None, email: str, phone: str | None, password: str):
    user = models.User(
    name=name,
    email=email.lower(),
    phone=phone,
    password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email.lower())
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if hasattr(models.User, "is_active") and not user.is_active: 
        return None
    return user