from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from uuid import UUID
from datetime import date as dt_date
from typing import List
import os

from app.db.session import get_db
from app.db.models import Users, Artist, Album, Track, FavArtists, ArtistTracks, ArtistAlbums, ArtistMembers, Member, Role
from app.schemas.common import MessageResponse
from app.schemas.artist import AlbumBrief, TrackBrief, ArtistCreate, ArtistUpdate, ArtistResponse, ArtistBrief
from app.core.deps import get_current_user, get_current_member, require_artist_membership, get_current_user_optional

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
    current_user: Users | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Получить подробную информацию об артисте, включая альбомы и популярные треки.
    Также показывает, является ли текущий пользователь членом этого артиста."""
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Проверяем, является ли текущий пользователь member'ом артиста
    is_member = False
    if current_user and current_user.is_member:
        member = db.query(Member).filter(Member.user_id == current_user.id).first()
        if member:
            link = db.query(ArtistMembers).filter(
                ArtistMembers.artist_id == artist_id,
                ArtistMembers.member_id == member.id
            ).first()
            is_member = link is not None

    # Альбомы артиста (отсортированы по дате релиза)
    albums_query = db.query(Album).join(ArtistAlbums).filter(
        ArtistAlbums.artist_id == artist_id
    ).order_by(Album.release_date.desc())
    albums = albums_query.all()

    # Популярные треки артиста (топ-5 по прослушиваниям)
    popular_tracks = db.query(Track).join(ArtistTracks).filter(
        ArtistTracks.artist_id == artist_id
    ).order_by(Track.plays.desc()).limit(5).all()

    # Формируем ответ с новым полем is_member
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        description=artist.description,
        formation_date=artist.formation_date,
        disbandment_date=artist.disbandment_date,
        likes=artist.likes,
        plays=artist.plays,
        albums=albums,
        popular_tracks=popular_tracks,
        is_member=is_member
    )

# ---------- POST: создание артиста (любой авторизованный пользователь) ----------
@router.post("/", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED)
def create_artist(
    artist_data: ArtistCreate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать нового артиста. Пользователь автоматически становится его членом (member).
    Если у пользователя ещё нет профиля member, он создаётся автоматически."""
    
    # Проверка на уникальность имени
    existing = db.query(Artist).filter(Artist.name == artist_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Artist with this name already exists")

    # Получаем или создаём Member для пользователя
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        member = Member(
            user_id=current_user.id,
            full_name=current_user.username,   # временное имя
            birth_date=dt_date.today()         # заглушка
        )
        db.add(member)
        db.flush()
        # Обновляем флаг is_member
        current_user.is_member = True
        db.add(current_user)
        db.commit()
    else:
        # Если member уже есть, но is_member почему-то false
        if not current_user.is_member:
            current_user.is_member = True
            db.add(current_user)
            db.commit()

    # Создаём артиста
    artist = Artist(
        name=artist_data.name,
        description=artist_data.description,
        formation_date=artist_data.formation_date,
        disbandment_date=artist_data.disbandment_date,
        likes=0,
        plays=0
    )
    db.add(artist)
    db.flush()

    # Находим роль "Other" (по умолчанию)
    other_role = db.query(Role).filter(Role.name == "Other").first()
    if not other_role:
        other_role = Role(name="Other")
        db.add(other_role)
        db.flush()

    # Добавляем текущего пользователя как участника
    artist_member = ArtistMembers(
        artist_id=artist.id,
        member_id=member.id,
        role_id=other_role.id,
        joining_date=dt_date.today(),
        leaving_date=None
    )
    db.add(artist_member)

    # Коммитим все изменения
    db.commit()

    # Финальная проверка, что is_member точно в БД
    user_check = db.query(Users).filter(Users.id == current_user.id).first()
    if user_check and not user_check.is_member:
        user_check.is_member = True
        db.commit()

    db.refresh(artist)

    # Возвращаем ответ (альбомов и треков пока нет)
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        description=artist.description,
        formation_date=artist.formation_date,
        disbandment_date=artist.disbandment_date,
        likes=artist.likes,
        plays=artist.plays,
        albums=[],
        popular_tracks=[],
        is_member=True
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
        popular_tracks=popular_tracks,
        is_member=True   # пользователь, вызвавший метод, уже member
    )

# ---------- DELETE: удаление артиста ----------
@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(
    artist_id: UUID,
    artist: Artist = Depends(require_artist_membership),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Полностью удалить артиста и всё, что с ним связано (треки, альбомы, файлы).
    Используем сырые SQL для гарантированного порядка удаления."""

    # Сначала собираем пути к файлам треков, которые будут удалены
    track_records = db.query(Track.id, Track.track_path).join(ArtistTracks).filter(
        ArtistTracks.artist_id == artist_id
    ).all()
    for track_id, track_path in track_records:
        if track_path and os.path.exists(track_path):
            try:
                os.remove(track_path)
            except Exception as e:
                print(f"Не удалось удалить файл {track_path}: {e}")

    # Последовательность SQL-запросов для удаления всех зависимых данных
    statements = [
        # 1. История прослушиваний для треков артиста
        "DELETE FROM history WHERE track_id IN (SELECT track_id FROM artist_tracks WHERE artist_id = :aid)",
        # 2. Удаляем треки из избранного
        "DELETE FROM fav_tracks WHERE track_id IN (SELECT track_id FROM artist_tracks WHERE artist_id = :aid)",
        # 3. Удаляем треки из плейлистов
        "DELETE FROM playlist_tracks WHERE track_id IN (SELECT track_id FROM artist_tracks WHERE artist_id = :aid)",
        # 4. Удаляем связи треков с альбомами
        "DELETE FROM album_tracks WHERE track_id IN (SELECT track_id FROM artist_tracks WHERE artist_id = :aid)",
        # 5. Удаляем сами треки (теперь ничто на них не ссылается)
        "DELETE FROM track WHERE id IN (SELECT track_id FROM artist_tracks WHERE artist_id = :aid)",
        # 6. Удаляем связи artist_tracks
        "DELETE FROM artist_tracks WHERE artist_id = :aid",
        # 7. Удаляем связи альбомов с треками, которые могли остаться
        "DELETE FROM album_tracks WHERE album_id IN (SELECT album_id FROM artist_albums WHERE artist_id = :aid)",
        # 8. Альбомы из избранного
        "DELETE FROM fav_albums WHERE album_id IN (SELECT album_id FROM artist_albums WHERE artist_id = :aid)",
        # 9. Сами альбомы
        "DELETE FROM album WHERE id IN (SELECT album_id FROM artist_albums WHERE artist_id = :aid)",
        # 10. Связи артист-альбом
        "DELETE FROM artist_albums WHERE artist_id = :aid",
        # 11. Связи с участниками
        "DELETE FROM artist_members WHERE artist_id = :aid",
        # 12. Артист в избранном
        "DELETE FROM fav_artists WHERE artist_id = :aid",
        # 13. Сам артист
        "DELETE FROM artist WHERE id = :aid",
    ]

    for stmt in statements:
        db.execute(text(stmt), {"aid": str(artist_id)})

    # Проверяем, остались ли у пользователя другие артисты
    member_id = db.query(Member.id).filter(Member.user_id == current_user.id).scalar()
    remaining = 0
    if member_id:
        remaining = db.execute(
            text("SELECT COUNT(*) FROM artist_members WHERE member_id = :mid"),
            {"mid": str(member_id)}
        ).scalar()

    if remaining == 0:
        db.execute(
            text("UPDATE users SET is_member = false WHERE id = :uid"),
            {"uid": str(current_user.id)}
        )
        # Обновляем объект current_user в текущей сессии, чтобы не было конфликта
        db.expire(current_user)
        current_user.is_member = False

    db.commit()
    return

# ---------- Лайк/анлайк ----------
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

# ---------- Треки и альбомы артиста ----------
@router.get("/{artist_id}/tracks", response_model=List[TrackBrief])
def get_artist_tracks(
    artist_id: UUID,
    q: str | None = None,          # <-- добавили параметр
    db: Session = Depends(get_db)
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    query = db.query(Track).join(ArtistTracks).filter(
        ArtistTracks.artist_id == artist_id
    )
    if q:
        query = query.filter(Track.name.ilike(f"%{q}%"))

    tracks = query.order_by(Track.plays.desc()).all()
    return tracks

@router.get("/{artist_id}/albums", response_model=List[AlbumBrief])
def get_artist_albums(
    artist_id: UUID,
    q: str | None = None,          # <-- новый параметр
    db: Session = Depends(get_db)
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    query = db.query(Album).join(ArtistAlbums).filter(
        ArtistAlbums.artist_id == artist_id
    )
    if q:
        query = query.filter(Album.name.ilike(f"%{q}%"))

    albums = query.order_by(Album.plays.desc()).all()
    return albums