from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.db.models import Users, Member, ArtistMembers, Artist, Track, ArtistTracks, Album, ArtistAlbums
from app.core.security import decode_access_token

security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Users:
    """Получает текущего пользователя по JWT токену"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_id = decode_access_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(Users).filter(Users.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Users | None:
    """Получает пользователя если он авторизован, иначе None"""
    
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = decode_access_token(token)
    
    if not user_id:
        return None
    
    return db.query(Users).filter(Users.id == user_id).first()

def get_current_member(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Member:
    """Получает Member текущего пользователя, иначе 403."""
    if not current_user.is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member"
        )
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        # Если is_member=True, но записи нет – создаём? По логике, member создаётся при привязке к артисту.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member profile not found"
        )
    return member

def require_artist_membership(
    artist_id: UUID,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
) -> Artist:
    """Проверяет, что member связан с артистом, и возвращает артиста."""
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Проверяем наличие связи member -> artist
    link = db.query(ArtistMembers).filter(
        ArtistMembers.artist_id == artist_id,
        ArtistMembers.member_id == current_member.id
    ).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this artist"
        )
    return artist

def require_artist_membership_for_album(
    album_id: UUID,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
) -> Album:
    """Проверяет, что member связан хотя бы с одним артистом альбома, и возвращает альбом."""
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Получаем всех артистов альбома
    artist_links = db.query(ArtistAlbums).filter(ArtistAlbums.album_id == album_id).all()
    artist_ids = [link.artist_id for link in artist_links]

    # Проверяем, есть ли у member связь с любым из этих артистов
    member_artist_link = db.query(ArtistMembers).filter(
        ArtistMembers.member_id == current_member.id,
        ArtistMembers.artist_id.in_(artist_ids)
    ).first()

    if not member_artist_link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of any artist associated with this album"
        )
    return album

def require_track_membership(
    track_id: UUID,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db)
) -> Track:
    """Возвращает трек, если member связан хотя бы с одним его артистом, иначе 403."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Получаем ID артистов трека
    artist_links = db.query(ArtistTracks).filter(ArtistTracks.track_id == track_id).all()
    artist_ids = [link.artist_id for link in artist_links]

    # Проверяем, есть ли у member связь с любым из этих артистов
    member_link = db.query(ArtistMembers).filter(
        ArtistMembers.member_id == current_member.id,
        ArtistMembers.artist_id.in_(artist_ids)
    ).first()

    if not member_link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of any artist associated with this track"
        )
    return track