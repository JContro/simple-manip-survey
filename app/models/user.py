from typing import Optional
from pydantic import BaseModel, Field, EmailStr 
from datetime import datetime

class UserBase(BaseModel):
    """Base user model with common attributes."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(...)

class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """Model for updating a user."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)

class UserInDB(UserBase):
    """Model for user in database."""
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class UserResponse(UserBase):
    """Model for user response."""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }