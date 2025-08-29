from pydantic import BaseModel, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserBase(BaseModel):
    name: str | None = None
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: int
    name: str
    email: str
    is_active: bool
    class Config:
        from_attributes = True