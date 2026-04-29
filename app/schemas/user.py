from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import date
from typing import Optional, List

# ----- Базовые схемы -----
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# ----- Схемы ответа -----
class UserResponse(UserBase):
    id: UUID
    is_member: bool
    is_admin: bool
    
    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: UUID
    username: str
    is_fav_tracks_public: bool
    is_fav_playlists_public: bool
    is_fav_artists_public: bool
    is_fav_albums_public: bool
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    is_fav_tracks_public: Optional[bool] = None
    is_fav_playlists_public: Optional[bool] = None
    is_fav_artists_public: Optional[bool] = None
    is_fav_albums_public: Optional[bool] = None

# ----- Токен -----
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class FavoriteTrackIds(BaseModel):
    track_ids: List[UUID]

class FavoriteArtistIds(BaseModel):
    artist_ids: List[UUID]