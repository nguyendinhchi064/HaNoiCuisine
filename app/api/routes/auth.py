from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import models
from app.schemas import schemas
from app.services import crud
from app.security import create_access_token
from app.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", response_model=schemas.Token)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(
        db,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password=payload.password,
    )
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login-json", response_model=schemas.Token)
def login_json(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return current_user