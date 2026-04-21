from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.db.models import Users
from app.schemas.user import UserProfileResponse, UserProfileUpdate
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