# app/models/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

# Pydantic model for creating a new user (request body)
class UserCreate(BaseModel):
    username: str
    email: EmailStr # Use EmailStr for validation
    password: str

# Pydantic model for reading/returning user info (response body)
# Excludes sensitive data like hashed_password
class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility (pydantic v2)
        # orm_mode = True # For Pydantic v1
