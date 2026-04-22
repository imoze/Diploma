from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import date
from typing import Optional, List

from app.db.session import get_db
from app.db.models import Album, AlbumTypes, FavAlbums, Artist, Track, ArtistAlbums, AlbumTracks, ArtistTracks, Member, ArtistMembers
from app.schemas.album import AlbumCreate, AlbumUpdate, AlbumResponse
from app.core.deps import get_current_member, require_artist_membership_for_album


# ---------- Вспомогательная функция для формирования ответа ----------
def build_album_response(album: Album, db: Session) -> AlbumResponse:
    # Тип альбома
    album_type = db.query(AlbumTypes).filter(AlbumTypes.id == album.album_type_id).first()

    # Артисты альбома
    artist_links = db.query(ArtistAlbums).filter(ArtistAlbums.album_id == album.id).all()
    artists = [link.artist for link in artist_links]

    # Треки альбома с их исполнителями
    track_links = db.query(AlbumTracks).filter(AlbumTracks.album_id == album.id).order_by(AlbumTracks.idx).all()
    tracks = []
    for tl in track_links:
        track = tl.track
        # Получаем исполнителей трека
        track_artist_links = db.query(ArtistTracks).filter(ArtistTracks.track_id == track.id).all()
        track_artists = [tal.artist for tal in track_artist_links]
        tracks.append({
            "id": track.id,
            "name": track.name,
            "duration": track.duration,
            "artists": track_artists
        })

    return AlbumResponse(
        id=album.id,
        name=album.name,
        release_date=album.release_date,
        duration=album.duration,
        likes=album.likes,
        plays=album.plays,
        album_type=album_type,
        artists=artists,
        tracks=tracks
    )

# Проверка прав на редактирование альбома (используем в нескольких местах)
def check_album_edit_permission(album_id: UUID, member: Member, db: Session) -> Album:
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Получаем артистов альбома
    album_artist_links = db.query(ArtistAlbums).filter(ArtistAlbums.album_id == album_id).all()
    album_artist_ids = [link.artist_id for link in album_artist_links]

    # Проверяем, что member связан хотя бы с одним из этих артистов
    member_link = db.query(ArtistMembers).filter(
        ArtistMembers.member_id == member.id,
        ArtistMembers.artist_id.in_(album_artist_ids)
    ).first()

    if not member_link:
        raise HTTPException(status_code=403, detail="You don't have permission to modify this album")
    return album


router = APIRouter(prefix="/api/albums", tags=["albums"])

# ---------- GET: список и конкретный ----------
@router.get("/", response_model=list[AlbumResponse])
def get_albums(
    q: str | None = None,
    db: Session = Depends(get_db)
):
    """Получить список альбомов (с возможностью поиска по названию)."""
    query = db.query(Album)
    if q:
        query = query.filter(Album.name.ilike(f"%{q}%"))
    albums = query.order_by(Album.release_date.desc()).limit(50).all()
    return [build_album_response(album, db) for album in albums]

@router.get("/{album_id}", response_model=AlbumResponse)
def get_album(
    album_id: UUID,
    db: Session = Depends(get_db)
):
    """Получить подробную информацию об альбоме."""
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return build_album_response(album, db)


# ---------- POST: создание альбома (только member, привязанный к артистам) ----------
@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(
    album_data: AlbumCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """Создать новый альбом. Требуется, чтобы member был участником хотя бы одного из указанных артистов."""
    # Проверяем существование типа альбома
    album_type = db.query(AlbumTypes).filter(AlbumTypes.id == album_data.album_type_id).first()
    if not album_type:
        raise HTTPException(status_code=400, detail="Invalid album type")

    # Проверяем, что member связан хотя бы с одним артистом из списка
    if not album_data.artist_ids:
        raise HTTPException(status_code=400, detail="At least one artist must be specified")

    # Получаем всех артистов, с которыми связан member
    member_artist_links = db.query(ArtistMembers).filter(
        ArtistMembers.member_id == current_member.id
    ).all()
    member_artist_ids = {link.artist_id for link in member_artist_links}

    # Проверяем пересечение
    if not member_artist_ids.intersection(album_data.artist_ids):
        raise HTTPException(
            status_code=403,
            detail="You must be a member of at least one of the specified artists"
        )

    # Создаём альбом
    album = Album(
        name=album_data.name,
        release_date=album_data.release_date,
        duration=0,  # будет обновляться при добавлении треков
        likes=0,
        plays=0,
        album_type_id=album_data.album_type_id
    )
    db.add(album)
    db.flush()

    # Добавляем связи с артистами
    for idx, artist_id in enumerate(album_data.artist_ids):
        # Проверяем существование артиста
        artist = db.query(Artist).filter(Artist.id == artist_id).first()
        if not artist:
            raise HTTPException(status_code=400, detail=f"Artist {artist_id} not found")
        artist_album = ArtistAlbums(
            artist_id=artist_id,
            album_id=album.id,
            idx=idx,
            is_feat=False  # основной артист альбома
        )
        db.add(artist_album)

    db.commit()
    db.refresh(album)

    return build_album_response(album, db)

# ---------- PATCH: обновление альбома ----------
@router.patch("/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: UUID,
    album_update: AlbumUpdate,
    album: Album = Depends(require_artist_membership_for_album),
    db: Session = Depends(get_db)
):
    """Обновить информацию об альбоме (доступно участникам артистов альбома)."""
    if album_update.name is not None:
        album.name = album_update.name
    if album_update.release_date is not None:
        album.release_date = album_update.release_date
    if album_update.album_type_id is not None:
        # Проверяем существование типа
        album_type = db.query(AlbumTypes).filter(AlbumTypes.id == album_update.album_type_id).first()
        if not album_type:
            raise HTTPException(status_code=400, detail="Invalid album type")
        album.album_type_id = album_update.album_type_id

    db.commit()
    db.refresh(album)
    return build_album_response(album, db)

# ---------- DELETE: удаление альбома ----------
@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: UUID,
    album: Album = Depends(require_artist_membership_for_album),
    db: Session = Depends(get_db)
):
    """Удалить альбом (доступно участникам артистов альбома)."""
    # Проверяем, есть ли треки в альбоме
    track_count = db.query(AlbumTracks).filter(AlbumTracks.album_id == album_id).count()
    if track_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete album with existing tracks. Remove tracks first."
        )

    # 1. Удаляем связи с артистами (artist_albums)
    artist_links = db.query(ArtistAlbums).filter(ArtistAlbums.album_id == album_id).all()
    for link in artist_links:
        db.delete(link)
    
    # 2. Удаляем лайки альбома (fav_albums)
    fav_links = db.query(FavAlbums).filter(FavAlbums.album_id == album_id).all()
    for link in fav_links:
        db.delete(link)
    
    # 3. Удаляем сам альбом
    db.delete(album)
    db.commit()
    return

@router.post("/{album_id}/tracks", status_code=status.HTTP_200_OK)
def add_track_to_album(
    album_id: UUID,
    track_id: UUID,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    album = check_album_edit_permission(album_id, current_member, db)

    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(AlbumTracks).filter(
        AlbumTracks.album_id == album_id,
        AlbumTracks.track_id == track_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track already in album")

    max_idx = db.query(func.max(AlbumTracks.idx)).filter(AlbumTracks.album_id == album_id).scalar() or -1
    db.add(AlbumTracks(album_id=album_id, track_id=track_id, idx=max_idx+1))
    album.duration += track.duration
    db.commit()
    return {"message": "Track added to album"}

@router.delete("/{album_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_track_from_album(
    album_id: UUID,
    track_id: UUID,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    album = check_album_edit_permission(album_id, current_member, db)

    link = db.query(AlbumTracks).filter(
        AlbumTracks.album_id == album_id,
        AlbumTracks.track_id == track_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Track not in album")

    track = db.query(Track).filter(Track.id == track_id).first()
    db.delete(link)
    album.duration -= track.duration

    # Переиндексация оставшихся треков
    remaining = db.query(AlbumTracks).filter(AlbumTracks.album_id == album_id).order_by(AlbumTracks.idx).all()
    for i, pt in enumerate(remaining):
        pt.idx = i

    db.commit()
    return

@router.post("/{album_id}/tracks/reorder", status_code=status.HTTP_200_OK)
def reorder_album_tracks(
    album_id: UUID,
    track_order: List[UUID],
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    album = check_album_edit_permission(album_id, current_member, db)

    album_tracks = db.query(AlbumTracks).filter(AlbumTracks.album_id == album_id).all()
    track_dict = {pt.track_id: pt for pt in album_tracks}

    if set(track_order) != set(track_dict.keys()):
        raise HTTPException(status_code=400, detail="Track list mismatch")

    for idx, track_id in enumerate(track_order):
        track_dict[track_id].idx = idx

    db.commit()
    return {"message": "Order updated"}