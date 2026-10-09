from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username for login", min_length=1)
    password: str = Field(..., description="Password for login", min_length=1)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    success: bool = True
    access_token: str
    token_type: str = "bearer"
    user: UserOut
