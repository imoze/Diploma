from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional, List

# ----- Базовые схемы -----
class ArtistBase(BaseModel):
    name: str
    description: Optional[str] = None
    formation_date: date
    disbandment_date: Optional[date] = None

class ArtistCreate(ArtistBase):
    pass

class ArtistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    formation_date: Optional[date] = None
    disbandment_date: Optional[date] = None

# ----- Схемы ответа -----
class ArtistBrief(BaseModel):
    id: UUID
    name: str
    formation_date: date
    disbandment_date: Optional[date]
    likes: int
    plays: int

    class Config:
        from_attributes = True

class AlbumBrief(BaseModel):
    id: UUID
    name: str
    release_date: date
    likes: int
    plays: int

    class Config:
        from_attributes = True

class TrackBrief(BaseModel):
    id: UUID
    name: str
    duration: int
    likes: int
    plays: int

    class Config:
        from_attributes = True

class ArtistResponse(ArtistBrief):
    description: Optional[str]
    albums: List[AlbumBrief] = []
    popular_tracks: List[TrackBrief] = []   # например, топ-5 по прослушиваниям

    class Config:
        from_attributes = True