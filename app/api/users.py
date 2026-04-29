from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.db.models import Album, Playlist, Users, FavPlaylists, FavAlbums, FavTracks, FavArtists, ArtistTracks, Artist, Track
from app.schemas.user import UserProfileResponse, UserProfileUpdate, FavoriteTrackIds, FavoriteArtistIds, FavoriteAlbumIds, FavoritePlaylistIds
from app.schemas.track import TrackResponse, SimilarTrackResponse, ArtistBriefForTrack
from app.schemas.playlist import PlaylistResponse
from app.schemas.artist import ArtistBrief
from app.schemas.album import AlbumResponse
from app.core.deps import get_current_user, get_current_user_optional
from app.core.security import hash_password
from app.api.tracks import build_track_response
from app.api.playlists import build_playlist_response
from app.api.albums import build_album_response

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(current_user: Users = Depends(get_current_user)):
    """Получение своего профиля"""
    return current_user

@router.patch("/me/profile", response_model=UserProfileResponse)
def update_my_profile(
    profile_data: UserProfileUpdate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление своего профиля"""
    
    # Проверяем уникальность username если он меняется
    if profile_data.username and profile_data.username != current_user.username:
        existing = db.query(Users).filter(
            Users.username == profile_data.username
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = profile_data.username
    
    # Обновляем настройки приватности
    if profile_data.is_fav_tracks_public is not None:
        current_user.is_fav_tracks_public = profile_data.is_fav_tracks_public
    
    if profile_data.is_fav_playlists_public is not None:
        current_user.is_fav_playlists_public = profile_data.is_fav_playlists_public
    
    if profile_data.is_fav_artists_public is not None:
        current_user.is_fav_artists_public = profile_data.is_fav_artists_public
    
    if profile_data.is_fav_albums_public is not None:
        current_user.is_fav_albums_public = profile_data.is_fav_albums_public
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(
    user_id: UUID,
    current_user: Users | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Получение публичного профиля другого пользователя"""
    
    user = db.query(Users).filter(Users.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/me/wave", response_model=list[SimilarTrackResponse])
def get_my_wave(
    limit: int = 20,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Рекомендации на основе лайкнутых треков пользователя."""
    # Получаем ID лайкнутых треков и их векторы
    fav_query = db.query(Track.id, Track.feature_vector).join(
        FavTracks, FavTracks.track_id == Track.id
    ).filter(
        FavTracks.user_id == current_user.id,
        Track.feature_vector.is_not(None)
    )
    fav_tracks = fav_query.all()

    if not fav_tracks:
        # Если нет лайков, возвращаем случайные треки (или пустой список)
        random_tracks = db.query(Track).filter(
            Track.feature_vector.is_not(None)
        ).order_by(func.random()).limit(limit).all()
        result = []
        for t in random_tracks:
            artists = db.query(Artist).join(ArtistTracks).filter(ArtistTracks.track_id == t.id).all()
            result.append(SimilarTrackResponse(
                id=t.id, name=t.name, duration=t.duration,
                artists=[ArtistBriefForTrack.model_validate(a) for a in artists],
                similarity=0.0
            ))
        return result

    # Вычисляем средний вектор (в Python для простоты)
    import numpy as np
    vectors = [np.array(t.feature_vector) for t in fav_tracks]
    mean_vector = np.mean(vectors, axis=0).tolist()
    vector_str = f"[{','.join(map(str, mean_vector))}]"

    # Получаем ID уже лайкнутых треков для исключения
    liked_ids = [t.id for t in fav_tracks]

    # SQL запрос для поиска ближайших
    sql = text("""
        SELECT 
            t.id, t.name, t.duration,
            1 - (t.feature_vector <=> CAST(:vector AS vector)) AS similarity
        FROM track t
        WHERE t.feature_vector IS NOT NULL
          AND t.id != ALL(:exclude_ids)
        ORDER BY t.feature_vector <=> CAST(:vector AS vector)
        LIMIT :limit
    """)

    result = db.execute(sql, {
        "vector": vector_str,
        "exclude_ids": liked_ids,
        "limit": limit
    })

    rows = result.fetchall()
    response = []
    for r in rows:
        # Получаем артистов трека
        artists = db.query(Artist).join(ArtistTracks).filter(ArtistTracks.track_id == r.id).all()
        similarity = round(r.similarity * 100, 1)  # процент
        response.append(SimilarTrackResponse(
            id=r.id, name=r.name, duration=r.duration,
            artists=[ArtistBriefForTrack.model_validate(a) for a in artists],
            similarity=similarity
        ))
    return response

@router.get("/me/favorites/ids", response_model=FavoriteTrackIds)
def get_my_favorite_track_ids(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает список ID треков, добавленных в избранное текущим пользователем."""
    fav_links = db.query(FavTracks).filter(FavTracks.user_id == current_user.id).all()
    track_ids = [link.track_id for link in fav_links]
    return {"track_ids": track_ids}

@router.get("/me/favorites/artist-ids", response_model=FavoriteArtistIds)
def get_my_favorite_artist_ids(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavArtists).filter(FavArtists.user_id == current_user.id).all()
    artist_ids = [link.artist_id for link in fav_links]
    return {"artist_ids": artist_ids}

@router.get("/me/favorites/album-ids", response_model=FavoriteAlbumIds)
def get_my_favorite_album_ids(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavAlbums).filter(FavAlbums.user_id == current_user.id).all()
    album_ids = [link.album_id for link in fav_links]
    return {"album_ids": album_ids}

@router.get("/me/favorites/playlist-ids", response_model=FavoritePlaylistIds)
def get_my_favorite_playlist_ids(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavPlaylists).filter(FavPlaylists.user_id == current_user.id).all()
    playlist_ids = [link.playlist_id for link in fav_links]
    return {"playlist_ids": playlist_ids}

@router.get("/", response_model=list[UserProfileResponse])
def search_users(
    q: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Поиск пользователей по username (подстрока)."""
    query = db.query(Users)
    if q:
        query = query.filter(Users.username.ilike(f"%{q}%"))
    users = query.limit(limit).all()
    return users

@router.get("/me/favorites/tracks", response_model=List[TrackResponse])
def get_my_favorite_tracks(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavTracks).filter(FavTracks.user_id == current_user.id).order_by(FavTracks.idx).all()
    track_ids = [link.track_id for link in fav_links]
    tracks = db.query(Track).filter(Track.id.in_(track_ids)).all() if track_ids else []
    # Возвращаем в порядке добавления
    track_map = {t.id: t for t in tracks}
    ordered = [track_map[tid] for tid in track_ids if tid in track_map]
    return [build_track_response(t, db) for t in ordered]

@router.get("/me/favorites/playlists", response_model=List[PlaylistResponse])
def get_my_favorite_playlists(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavPlaylists).filter(FavPlaylists.user_id == current_user.id).order_by(FavPlaylists.idx).all()
    playlist_ids = [link.playlist_id for link in fav_links]
    playlists = db.query(Playlist).filter(Playlist.id.in_(playlist_ids)).all() if playlist_ids else []
    pmap = {p.id: p for p in playlists}
    ordered = [pmap[pid] for pid in playlist_ids if pid in pmap]
    return [build_playlist_response(p, db) for p in ordered]

@router.get("/me/favorites/artists", response_model=List[ArtistBrief])
def get_my_favorite_artists(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavArtists).filter(FavArtists.user_id == current_user.id).order_by(FavArtists.idx).all()
    artist_ids = [link.artist_id for link in fav_links]
    artists = db.query(Artist).filter(Artist.id.in_(artist_ids)).all() if artist_ids else []
    amap = {a.id: a for a in artists}
    ordered = [amap[aid] for aid in artist_ids if aid in amap]
    return ordered

@router.get("/me/favorites/albums", response_model=List[AlbumResponse])
def get_my_favorite_albums(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav_links = db.query(FavAlbums).filter(FavAlbums.user_id == current_user.id).order_by(FavAlbums.idx).all()
    album_ids = [link.album_id for link in fav_links]
    albums = db.query(Album).filter(Album.id.in_(album_ids)).all() if album_ids else []
    amap = {a.id: a for a in albums}
    ordered = [amap[aid] for aid in album_ids if aid in amap]
    return [build_album_response(a, db) for a in ordered]