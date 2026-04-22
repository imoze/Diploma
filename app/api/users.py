from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from uuid import UUID

from app.db.session import get_db
from app.db.models import Users, FavTracks, ArtistTracks, Artist, Track
from app.schemas.user import UserProfileResponse, UserProfileUpdate
from app.schemas.track import SimilarTrackResponse, ArtistBriefForTrack
from app.core.deps import get_current_user, get_current_user_optional
from app.core.security import hash_password

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