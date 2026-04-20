from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
import os

from app.db.session import get_db
from app.db.models import Track
from app.schemas.track import TrackResponse

router = APIRouter(prefix="/api/tracks", tags=["tracks"])

@router.get("/", response_model=list[TrackResponse])
def get_tracks(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Track)

    if q:
        query = query.filter(Track.name.ilike(f"%{q}%"))

    return query.limit(50).all()


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: UUID, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.get("/{track_id}/similar")
def get_similar_tracks(
    track_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if track.feature_vector is None:
        raise HTTPException(status_code=400, detail="No feature vector")

    sql = text("""
        SELECT id, name, release_date, duration, likes, plays
        FROM track
        WHERE id != :track_id
        ORDER BY feature_vector <=> CAST(:vector AS vector)
        LIMIT :limit
    """)

    vector_str = f"[{','.join(map(str, track.feature_vector.tolist()))}]"

    result = db.execute(sql, {
        "track_id": str(track_id),
        "vector": vector_str,
        "limit": limit
    })

    rows = result.fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "release_date": r.release_date,
            "duration": r.duration,
            "likes": r.likes,
            "plays": r.plays,
        }
        for r in rows
    ]


@router.get("/{track_id}/stream")
def stream_track(track_id: UUID, request: Request, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if not track.track_path:
        raise HTTPException(status_code=404, detail="Track file not found")

    file_path = track.track_path

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    if "range" not in request.headers:
        track.plays += 1
        for artist in track.artists:
            artist.plays += 1
        db.commit()

    def iterfile():
        with open(file_path, mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(iterfile(), media_type="audio/mpeg", headers={"Content-Disposition": f'inline; filename="{track.name}.mp3"'})