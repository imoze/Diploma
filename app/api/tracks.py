from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import date
from typing import Optional, List
from uuid import UUID
import shutil
import os
from pathlib import Path
import joblib
import librosa
from uuid6 import uuid7

from app.db.session import get_db
from app.db.models import Users, PlaylistTracks, Track, Artist, Album, ArtistTracks, AlbumTracks, Member, ArtistMembers, FavTracks
from app.schemas.common import MessageResponse
from app.schemas.track import TrackCreate, TrackResponse, TrackUpdate
from app.core.deps import get_current_member, require_track_membership, get_current_user
from AudioAnalysis.NewTrackAnalysis import AnalyseTrack

UPLOAD_DIR = Path("Tracks/NewUploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SCALER_PATH = Path("models/scaler.pkl")
PCA_PATH = Path("models/pca.pkl")
scaler = joblib.load(SCALER_PATH) if SCALER_PATH.exists() else None
pca = joblib.load(PCA_PATH) if PCA_PATH.exists() else None

def process_track_background(track_id: UUID, file_path: str):
    """Фоновая задача: вычисляет длительность и feature_vector, обновляет трек."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Длительность через librosa
        y, sr = librosa.load(file_path)
        duration = int(librosa.get_duration(y=y, sr=sr))

        # Вектор
        vector = None
        if scaler and pca:
            vector = AnalyseTrack(scaler, pca, file_path)[0].tolist()

        track = db.query(Track).filter(Track.id == track_id).first()
        if track:
            track.duration = duration
            if vector:
                track.feature_vector = vector
            db.commit()
    except Exception as e:
        print(f"Background processing error for track {track_id}: {e}")
    finally:
        db.close()

def build_track_response(track: Track, db: Session) -> TrackResponse:
    artist_links = db.query(ArtistTracks).filter(
        ArtistTracks.track_id == track.id
    ).order_by(ArtistTracks.idx).all()
    artists = [link.artist for link in artist_links]

    album_links = db.query(AlbumTracks).filter(
        AlbumTracks.track_id == track.id
    ).all()
    albums = [link.album for link in album_links]
    
    return TrackResponse(
        id=track.id,
        name=track.name,
        release_date=track.release_date,
        duration=track.duration,
        likes=track.likes,
        plays=track.plays,
        artists=artists,
        albums=albums
    )


router = APIRouter(prefix="/api/tracks", tags=["tracks"])

@router.get("/", response_model=list[TrackResponse])
def get_tracks(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Track)
    if q:
        query = query.filter(Track.name.ilike(f"%{q}%"))
    tracks = query.limit(50).all()
    return [build_track_response(t, db) for t in tracks]


@router.post("/", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def create_track(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    release_date: date = Form(...),
    artist_ids: str = Form(...),          # UUID через запятую
    feat_artist_ids: Optional[str] = Form(None),
    album_ids: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    # Парсим списки UUID
    def parse_ids(ids_str: Optional[str]) -> List[UUID]:
        if not ids_str:
            return []
        return [UUID(uid.strip()) for uid in ids_str.split(',') if uid.strip()]

    main_artists = parse_ids(artist_ids)
    feat_artists = parse_ids(feat_artist_ids)
    albums = parse_ids(album_ids)

    if not main_artists:
        raise HTTPException(status_code=400, detail="At least one main artist required")

    # Проверка прав: member должен быть связан хотя бы с одним основным артистом
    member_artist_links = db.query(ArtistMembers).filter(
        ArtistMembers.member_id == current_member.id
    ).all()
    member_artist_ids = {link.artist_id for link in member_artist_links}
    if not member_artist_ids.intersection(main_artists):
        raise HTTPException(
            status_code=403,
            detail="You must be a member of at least one of the main artists"
        )

    # Проверка существования артистов и альбомов
    all_artist_ids = main_artists + feat_artists
    for aid in all_artist_ids:
        if not db.query(Artist).filter(Artist.id == aid).first():
            raise HTTPException(status_code=400, detail=f"Artist {aid} not found")
    for alb_id in albums:
        if not db.query(Album).filter(Album.id == alb_id).first():
            raise HTTPException(status_code=400, detail=f"Album {alb_id} not found")

    # Сохраняем файл
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext != '.mp3':
        raise HTTPException(status_code=400, detail="Only MP3 files are allowed")

    track_id = uuid7()
    file_path = UPLOAD_DIR / f"{track_id}{file_ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Создаём запись трека (duration временно 0)
    track = Track(
        id=track_id,
        name=name,
        release_date=release_date,
        duration=0,
        likes=0,
        plays=0,
        track_path=str(file_path)
    )
    db.add(track)
    db.flush()

    # Связи с артистами
    for idx, aid in enumerate(main_artists):
        db.add(ArtistTracks(artist_id=aid, track_id=track.id, idx=idx, is_feat=False))
    for idx, aid in enumerate(feat_artists):
        db.add(ArtistTracks(artist_id=aid, track_id=track.id, idx=len(main_artists)+idx, is_feat=True))

    # Связи с альбомами
    for alb_id in albums:
        max_idx = db.query(func.max(AlbumTracks.idx)).filter(AlbumTracks.album_id == alb_id).scalar() or -1
        db.add(AlbumTracks(album_id=alb_id, track_id=track.id, idx=max_idx+1))
        # Обновим длительность альбома позже, когда будет известна длительность трека

    db.commit()
    db.refresh(track)

    # Запускаем фоновую обработку
    background_tasks.add_task(process_track_background, track.id, str(file_path))

    # Формируем ответ (пока без артистов и альбомов, но можно вернуть базовые поля)
    return TrackResponse(
        id=track.id,
        name=track.name,
        release_date=track.release_date,
        duration=track.duration,
        likes=track.likes,
        plays=track.plays,
        artists=[],   # можно заполнить, но необязательно
        albums=[]
    )

@router.patch("/{track_id}", response_model=TrackResponse)
def update_track(
    track_id: UUID,
    track_update: TrackUpdate,
    track: Track = Depends(require_track_membership),
    db: Session = Depends(get_db)
):
    """Обновить метаданные трека (доступно member'ам артистов трека)."""
    if track_update.name is not None:
        track.name = track_update.name
    if track_update.release_date is not None:
        track.release_date = track_update.release_date
    db.commit()
    db.refresh(track)
    return build_track_response(track, db)

@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(
    track_id: UUID,
    track: Track = Depends(require_track_membership),
    db: Session = Depends(get_db)
):
    """Удалить трек (доступно member'ам артистов трека)."""
    # 1. Удаляем все связи с альбомами (загружаем объекты и удаляем через сессию)
    album_links = db.query(AlbumTracks).filter(AlbumTracks.track_id == track_id).all()
    for link in album_links:
        db.delete(link)
    
    # 2. Удаляем связи с плейлистами
    playlist_links = db.query(PlaylistTracks).filter(PlaylistTracks.track_id == track_id).all()
    for link in playlist_links:
        db.delete(link)
    
    # 3. Удаляем связи с артистами
    artist_links = db.query(ArtistTracks).filter(ArtistTracks.track_id == track_id).all()
    for link in artist_links:
        db.delete(link)
    
    # 4. Удаляем файл с диска
    if track.track_path and os.path.exists(track.track_path):
        os.remove(track.track_path)
    
    # 5. Удаляем сам трек
    db.delete(track)
    db.commit()
    return


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: UUID, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return build_track_response(track, db)


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


@router.post("/{track_id}/like", response_model=MessageResponse)
def like_track(
    track_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить трек в избранное."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(FavTracks).filter(
        FavTracks.user_id == current_user.id,
        FavTracks.track_id == track_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track already in favorites")

    # Определяем следующий idx
    max_idx = db.query(func.max(FavTracks.idx)).filter(
        FavTracks.user_id == current_user.id
    ).scalar() or -1

    fav = FavTracks(
        user_id=current_user.id,
        track_id=track_id,
        idx=max_idx + 1
    )
    db.add(fav)
    track.likes += 1
    db.commit()
    return {"message": "Track added to favorites"}

@router.delete("/{track_id}/like", response_model=MessageResponse)
def unlike_track(
    track_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить трек из избранного."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    fav = db.query(FavTracks).filter(
        FavTracks.user_id == current_user.id,
        FavTracks.track_id == track_id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Track not in favorites")

    db.delete(fav)
    track.likes -= 1
    db.commit()

    # Переиндексация оставшихся избранных треков пользователя
    remaining = db.query(FavTracks).filter(
        FavTracks.user_id == current_user.id
    ).order_by(FavTracks.idx).all()
    for i, f in enumerate(remaining):
        f.idx = i
    db.commit()

    return {"message": "Track removed from favorites"}