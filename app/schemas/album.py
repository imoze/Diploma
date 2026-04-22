from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional, List

# ----- Базовые схемы -----
class AlbumBase(BaseModel):
    name: str
    release_date: date
    album_type_id: UUID   # тип альбома (сингл, EP, LP и т.д.)

class AlbumCreate(AlbumBase):
    artist_ids: List[UUID]   # список ID артистов, участвующих в альбоме

class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    release_date: Optional[date] = None
    album_type_id: Optional[UUID] = None

# ----- Схемы ответа -----
class ArtistBriefForAlbum(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

class AlbumTypeResponse(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

class TrackInAlbumResponse(BaseModel):
    id: UUID
    name: str
    duration: int
    artists: List[ArtistBriefForAlbum] = []   # исполнители трека (можно несколько)
    class Config:
        from_attributes = True

class AlbumResponse(BaseModel):
    id: UUID
    name: str
    release_date: date
    duration: int
    likes: int
    plays: int
    album_type: AlbumTypeResponse
    artists: List[ArtistBriefForAlbum] = []
    tracks: List[TrackInAlbumResponse] = []

    class Config:
        from_attributes = True