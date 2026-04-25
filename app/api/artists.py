from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from uuid import UUID
from datetime import date

from app.db.session import get_db
from app.db.models import Users, Artist, Album, Track, FavArtists, ArtistTracks, ArtistAlbums, ArtistMembers, Member, Role
from app.schemas.common import MessageResponse
from app.schemas.artist import ArtistCreate, ArtistUpdate, ArtistResponse, ArtistBrief
from app.core.deps import get_current_user, get_current_member, require_artist_membership

router = APIRouter(prefix="/api/artists", tags=["artists"])

# ---------- GET: список и конкретный ----------
@router.get("/", response_model=list[ArtistBrief])
def get_artists(
    q: str | None = None,
    limit : int = 50,
    db: Session = Depends(get_db)
):
    """Получить список артистов (с возможностью поиска по имени)."""
    query = db.query(Artist)
    if q:
        query = query.filter(Artist.name.ilike(f"%{q}%"))
    artists = query.order_by(Artist.name).limit(limit).all()
    return artists

@router.get("/{artist_id}", response_model=ArtistResponse)
def get_artist(
    artist_id: UUID,
    db: Session = Depends(get_db)
):
    """Получить подробную информацию об артисте, включая альбомы и популярные треки."""
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Альбомы артиста (отсортированы по дате релиза)
    albums_query = db.query(Album).join(ArtistAlbums).filter(
        ArtistAlbums.artist_id == artist_id
    ).order_by(Album.release_date.desc())
    albums = albums_query.all()

    # Популярные треки артиста (топ-5 по прослушиваниям)
    popular_tracks = db.query(Track).join(ArtistTracks).filter(
        ArtistTracks.artist_id == artist_id
    ).order_by(Track.plays.desc()).limit(5).all()

    # Формируем ответ вручную, т.к. ArtistResponse содержит поля albums и popular_tracks
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        description=artist.description,
        formation_date=artist.formation_date,
        disbandment_date=artist.disbandment_date,
        likes=artist.likes,
        plays=artist.plays,
        albums=albums,
        popular_tracks=popular_tracks
    )

# ---------- POST: создание артиста (только member) ----------
@router.post("/", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED)
def create_artist(
    artist_data: ArtistCreate,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """Создать нового артиста. Текущий member автоматически добавляется как участник с ролью 'Other'."""
    # Проверка на уникальность имени (опционально)
    existing = db.query(Artist).filter(Artist.name == artist_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Artist with this name already exists")

    artist = Artist(
        name=artist_data.name,
        description=artist_data.description,
        formation_date=artist_data.formation_date,
        disbandment_date=artist_data.disbandment_date,
        likes=0,
        plays=0
    )
    db.add(artist)
    db.flush()  # чтобы получить id

    # Находим роль "Other" (по умолчанию)
    other_role = db.query(Role).filter(Role.name == "Other").first()
    if not other_role:
        # Если роли нет – создадим (на всякий случай)
        other_role = Role(name="Other")
        db.add(other_role)
        db.flush()

    # Добавляем текущего member как участника артиста с ролью "Other"
    artist_member = ArtistMembers(
        artist_id=artist.id,
        member_id=current_member.id,
        role_id=other_role.id,
        joining_date=date.today(),
        leaving_date=None
    )
    db.add(artist_member)

    db.commit()
    db.refresh(artist)

    # Возвращаем ответ (без альбомов и треков, т.к. они пусты)
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        description=artist.description,
        formation_date=artist.formation_date,
        disbandment_date=artist.disbandment_date,
        likes=artist.likes,
        plays=artist.plays,
        albums=[],
        popular_tracks=[]
    )

# ---------- PATCH: обновление артиста ----------
@router.patch("/{artist_id}", response_model=ArtistResponse)
def update_artist(
    artist_id: UUID,
    artist_update: ArtistUpdate,
    artist: Artist = Depends(require_artist_membership),  # проверяет права и возвращает артиста
    db: Session = Depends(get_db)
):
    """Обновить информацию об артисте (доступно только участникам)."""
    if artist_update.name is not None:
        # Проверка уникальности нового имени (если меняется)
        existing = db.query(Artist).filter(
            Artist.name == artist_update.name,
            Artist.id != artist_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Artist with this name already exists")
        artist.name = artist_update.name
    if artist_update.description is not None:
        artist.description = artist_update.description
    if artist_update.formation_date is not None:
        artist.formation_date = artist_update.formation_date
    if artist_update.disbandment_date is not None:
        artist.disbandment_date = artist_update.disbandment_date

    db.commit()
    db.refresh(artist)

    # Возвращаем обновлённого артиста с альбомами и треками
    albums = db.query(Album).join(ArtistAlbums).filter(ArtistAlbums.artist_id == artist_id).all()
    popular_tracks = db.query(Track).join(ArtistTracks).filter(
        ArtistTracks.artist_id == artist_id
    ).order_by(Track.plays.desc()).limit(5).all()

    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        description=artist.description,
        formation_date=artist.formation_date,
        disbandment_date=artist.disbandment_date,
        likes=artist.likes,
        plays=artist.plays,
        albums=albums,
        popular_tracks=popular_tracks
    )

# ---------- DELETE: удаление артиста ----------
@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(
    artist_id: UUID,
    artist: Artist = Depends(require_artist_membership),
    db: Session = Depends(get_db)
):
    """Удалить артиста (доступно только участникам)."""
    # Проверяем, есть ли у артиста альбомы или треки
    album_count = db.query(ArtistAlbums).filter(ArtistAlbums.artist_id == artist_id).count()
    track_count = db.query(ArtistTracks).filter(ArtistTracks.artist_id == artist_id).count()
    if album_count > 0 or track_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete artist with existing albums or tracks"
        )

    # 1. Удаляем связи с участниками (artist_members)
    member_links = db.query(ArtistMembers).filter(ArtistMembers.artist_id == artist_id).all()
    for link in member_links:
        db.delete(link)

    # 2. Удаляем связи с избранным (fav_artists)
    fav_links = db.query(FavArtists).filter(FavArtists.artist_id == artist_id).all()
    for link in fav_links:
        db.delete(link)

    # 3. Удаляем самого артиста
    db.delete(artist)
    db.commit()
    return

@router.post("/{artist_id}/like", response_model=MessageResponse)
def like_artist(
    artist_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    existing = db.query(FavArtists).filter(
        FavArtists.user_id == current_user.id,
        FavArtists.artist_id == artist_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Artist already in favorites")

    max_idx = db.query(func.max(FavArtists.idx)).filter(
        FavArtists.user_id == current_user.id
    ).scalar() or -1

    fav = FavArtists(
        user_id=current_user.id,
        artist_id=artist_id,
        idx=max_idx + 1
    )
    db.add(fav)
    artist.likes += 1
    db.commit()
    return {"message": "Artist added to favorites"}

@router.delete("/{artist_id}/like", response_model=MessageResponse)
def unlike_artist(
    artist_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    fav = db.query(FavArtists).filter(
        FavArtists.user_id == current_user.id,
        FavArtists.artist_id == artist_id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Artist not in favorites")

    db.delete(fav)
    artist.likes -= 1
    db.commit()

    remaining = db.query(FavArtists).filter(
        FavArtists.user_id == current_user.id
    ).order_by(FavArtists.idx).all()
    for i, f in enumerate(remaining):
        f.idx = i
    db.commit()

    return {"message": "Artist removed from favorites"}