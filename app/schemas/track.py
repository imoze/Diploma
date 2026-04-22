from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional, List


# --- Вспомогательные краткие схемы ---
class ArtistBriefForTrack(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

class AlbumBriefForTrack(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

# --- Основная схема ответа ---
class TrackResponse(BaseModel):
    id: UUID
    name: str
    release_date: date
    duration: int
    likes: int
    plays: int
    artists: List[ArtistBriefForTrack] = []
    albums: List[AlbumBriefForTrack] = []   # трек может входить в несколько альбомов (сборники)

    class Config:
        from_attributes = True

# --- Схема для создания трека ---
class TrackCreate(BaseModel):
    name: str
    release_date: date
    artist_ids: List[UUID]           # основные исполнители
    feat_artist_ids: Optional[List[UUID]] = []
    album_ids: Optional[List[UUID]] = []   # альбомы, в которые сразу добавить

# --- Схема для обновления (только базовые поля, связи меняются отдельно) ---
class TrackUpdate(BaseModel):
    name: Optional[str] = None
    release_date: Optional[date] = None