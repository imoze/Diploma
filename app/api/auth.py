from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.db.models import Users
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    
    # Проверяем уникальность email и username
    existing = db.query(Users).filter(
        or_(
            Users.email == user_data.email,
            Users.username == user_data.username
        )
    ).first()
    
    if existing:
        if existing.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Создаём пользователя
    user = Users(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        # Приватность по умолчанию - всё публично
        is_fav_tracks_public=True,
        is_fav_playlists_public=True,
        is_fav_artists_public=True,
        is_fav_albums_public=True,
        # Обычный пользователь, не админ
        is_member=False,
        is_admin=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Вход в систему"""
    
    # Ищем пользователя по email
    user = db.query(Users).filter(Users.email == user_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Проверяем пароль
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Создаём токен
    token = create_access_token(user.id)
    
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: Users = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user