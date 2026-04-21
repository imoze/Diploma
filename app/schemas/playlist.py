from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# ----- Информация о пользователе (кратко) -----
class UserBrief(BaseModel):
    id: UUID
    username: str
    class Config:
        from_attributes = True

# ----- Информация о треке в плейлисте -----
class PlaylistTrackResponse(BaseModel):
    id: UUID
    name: str
    duration: int
    # Можно добавить исполнителей при необходимости
    class Config:
        from_attributes = True

# ----- Базовые схемы -----
class PlaylistBase(BaseModel):
    name: str
    is_public: bool = True

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None

# ----- Полная схема плейлиста -----
class PlaylistResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    duration: int
    likes: int
    plays: int
    is_public: bool
    owner: UserBrief                     # владелец
    collaborators: List[UserBrief] = []  # соавторы (is_feat=True)
    tracks: List[PlaylistTrackResponse] = []

    class Config:
        from_attributes = True

# ----- Схема для добавления трека -----
class PlaylistAddTrack(BaseModel):
    track_id: UUID

# ----- Схема для добавления коллаборатора -----
class CollaboratorAdd(BaseModel):
    user_id: Optional[UUID] = None   # можно указать ID
    username: Optional[str] = None   # или username
    # одно из полей обязательно