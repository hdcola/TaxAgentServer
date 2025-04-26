from datetime import datetime
from pydantic import BaseModel, EmailStr, HttpUrl, ConfigDict
from typing import Optional

# --- Request Models ---
class FirebaseToken(BaseModel):
    """Model for receiving the Firebase ID token."""
    token: str

# --- User Models ---
class UserBase(BaseModel):
    """Base Pydantic model for user fields."""
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[HttpUrl | str] = None # Allow string or HttpUrl
    created_at: Optional[datetime] = None 
    updated_at: Optional[datetime] = None 
    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    """Model used when creating a user (might include password if needed)."""
    firebase_uid: str

class UserResponse(UserBase):
    """User information sent back to the frontend."""
    id: str # Include your internal ID

class UserInDB(UserBase):
     """User model as fully represented in DB (used internally)."""
     id: str
     firebase_uid: str

# --- Token Models ---
class TokenPayload(BaseModel):
    """Expected structure of the data within the internal JWT."""
    sub: Optional[str] = None

class InternalTokenData(BaseModel):
    """Data used to *create* the internal JWT payload."""
    sub: str # Subject (your internal user ID)
    email: Optional[EmailStr] = None
    firebase_uid: Optional[str] = None

class InternalTokenResponse(BaseModel):
    """Response containing your internal token and user info."""
    token: str
    user: UserResponse

class AuthApiResponse(BaseModel):
    """Standard API response structure."""
    data: Optional[InternalTokenResponse] = None
    status: int = 200
    message: str = "Success"