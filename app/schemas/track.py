from pydantic import BaseModel
from uuid import UUID
from datetime import date


class TrackResponse(BaseModel):
    id: UUID
    name: str
    release_date: date
    duration: int
    likes: int
    plays: int

    class Config:
        from_attributes = True  # важно для SQLAlchemy