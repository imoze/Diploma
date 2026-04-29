from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, select
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.db.models import Playlist, UserPlaylists, PlaylistTracks, Track, Users, FavPlaylists, Artist, ArtistTracks
from app.schemas.common import MessageResponse
from app.schemas.playlist import (
    PlaylistCreate, PlaylistUpdate, PlaylistResponse,
    PlaylistAddTrack, PlaylistTrackResponse, CollaboratorAdd,
    UserBrief
)
from app.schemas.track import SimilarTrackResponse, ArtistBriefForTrack
from app.core.deps import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/playlists", tags=["playlists"])

# ---------- Вспомогательные функции ----------
def get_playlist_with_access_check(
    playlist_id: UUID,
    current_user: Users | None,
    db: Session,
    require_owner: bool = False,
    require_edit: bool = False
) -> Playlist:
    """Получает плейлист с проверкой прав доступа."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Проверка публичности
    if not playlist.is_public:
        if not current_user:
            raise HTTPException(status_code=403, detail="Private playlist")
        # Проверяем, есть ли пользователь в списке участников (владелец или коллаборатор)
        user_link = db.query(UserPlaylists).filter(
            UserPlaylists.playlist_id == playlist_id,
            UserPlaylists.user_id == current_user.id
        ).first()
        if not user_link:
            raise HTTPException(status_code=403, detail="Access denied")

    # Дополнительные проверки для операций изменения
    if require_owner or require_edit:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        user_link = db.query(UserPlaylists).filter(
            UserPlaylists.playlist_id == playlist_id,
            UserPlaylists.user_id == current_user.id
        ).first()
        if not user_link:
            raise HTTPException(status_code=403, detail="Not a participant")
        if require_owner and user_link.is_feat:   # is_feat=True значит коллаборатор
            raise HTTPException(status_code=403, detail="Only owner can perform this action")

    return playlist

def build_playlist_response(playlist: Playlist, db: Session) -> PlaylistResponse:
    """Формирует полный ответ с владельцем, коллабораторами и треками."""
    # Владелец (is_feat=False)
    owner_link = db.query(UserPlaylists).filter(
        UserPlaylists.playlist_id == playlist.id,
        UserPlaylists.is_feat == False
    ).first()
    owner = owner_link.user if owner_link else None

    # Коллабораторы (is_feat=True)
    collab_links = db.query(UserPlaylists).filter(
        UserPlaylists.playlist_id == playlist.id,
        UserPlaylists.is_feat == True
    ).all()
    collaborators = [link.user for link in collab_links]

    # Треки с сортировкой по idx
    tracks_query = db.query(Track).join(
        PlaylistTracks, Track.id == PlaylistTracks.track_id
    ).filter(
        PlaylistTracks.playlist_id == playlist.id
    ).order_by(PlaylistTracks.idx)
    tracks = tracks_query.all()

    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        created_at=playlist.created_at,
        duration=playlist.duration,
        likes=playlist.likes,
        plays=playlist.plays,
        is_public=playlist.is_public,
        owner=UserBrief.model_validate(owner) if owner else None,
        collaborators=[UserBrief.model_validate(u) for u in collaborators],
        tracks=[PlaylistTrackResponse.model_validate(t) for t in tracks]
    )

# ---------- CRUD ----------

@router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание нового плейлиста текущим пользователем (становится владельцем)."""
    playlist = Playlist(
        name=playlist_data.name,
        created_at=datetime.utcnow(),
        duration=0,
        likes=0,
        plays=0,
        is_public=playlist_data.is_public
    )
    db.add(playlist)
    db.flush()  # получить id

    # Связь владельца
    user_playlist = UserPlaylists(
        user_id=current_user.id,
        playlist_id=playlist.id,
        idx=0,
        is_feat=False   # владелец
    )
    db.add(user_playlist)
    db.commit()
    db.refresh(playlist)

    return build_playlist_response(playlist, db)

@router.get("/", response_model=list[PlaylistResponse])
def get_playlists(
    my: bool = False,
    limit: int = 50,
    current_user: Users | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Получение списка плейлистов: публичных или своих (включая те, где соавтор)."""
    query = db.query(Playlist)

    if my and current_user:
        # Плейлисты, где пользователь участник (владелец или коллаборатор)
        subquery = select(UserPlaylists.playlist_id).where(
            UserPlaylists.user_id == current_user.id
        ).scalar_subquery()
        query = query.filter(Playlist.id.in_(subquery))
    else:
        # Публичные плейлисты и приватные где пользователь владелец или коллаборатор 
        conditions = [Playlist.is_public == True]
        if current_user:
            user_playlists_subquery = select(UserPlaylists.playlist_id).where(
                UserPlaylists.user_id == current_user.id
            ).scalar_subquery()
            conditions.append(Playlist.id.in_(user_playlists_subquery))
        query = query.filter(or_(*conditions))

    playlists = query.order_by(Playlist.likes.desc()).limit(limit).all()
    return [build_playlist_response(p, db) for p in playlists]

@router.get("/{playlist_id}", response_model=PlaylistResponse)
def get_playlist(
    playlist_id: UUID,
    current_user: Users | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Получение конкретного плейлиста с проверкой приватности."""
    playlist = get_playlist_with_access_check(playlist_id, current_user, db)
    return build_playlist_response(playlist, db)

@router.patch("/{playlist_id}", response_model=PlaylistResponse)
def update_playlist(
    playlist_id: UUID,
    playlist_update: PlaylistUpdate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление свойств плейлиста (только владелец)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_owner=True
    )

    if playlist_update.name is not None:
        playlist.name = playlist_update.name
    if playlist_update.is_public is not None:
        playlist.is_public = playlist_update.is_public

    db.commit()
    db.refresh(playlist)
    return build_playlist_response(playlist, db)

@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление плейлиста (только владелец)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_owner=True
    )
    
    # Открепляем все объекты, связанные с этим плейлистом, из сессии
    db.expunge(playlist)
    # Удаляем напрямую через ORM-запрос, полагаясь на каскад в БД
    db.query(Playlist).filter(Playlist.id == playlist_id).delete()
    db.commit()
    return

# ---------- Управление треками ----------
@router.post("/{playlist_id}/tracks", status_code=status.HTTP_200_OK)
def add_track_to_playlist(
    playlist_id: UUID,
    track_data: PlaylistAddTrack,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавление трека в плейлист (владелец или коллаборатор)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_edit=True
    )

    track = db.query(Track).filter(Track.id == track_data.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id,
        PlaylistTracks.track_id == track_data.track_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track already in playlist")

    max_idx = db.query(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id
    ).count()

    playlist_track = PlaylistTracks(
        playlist_id=playlist_id,
        track_id=track_data.track_id,
        idx=max_idx
    )
    db.add(playlist_track)
    playlist.duration += track.duration
    db.commit()

    return {"message": "Track added successfully"}

@router.delete("/{playlist_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_track_from_playlist(
    playlist_id: UUID,
    track_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление трека из плейлиста (владелец или коллаборатор)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_edit=True
    )

    playlist_track = db.query(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id,
        PlaylistTracks.track_id == track_id
    ).first()
    if not playlist_track:
        raise HTTPException(status_code=404, detail="Track not in playlist")

    track = db.query(Track).filter(Track.id == track_id).first()
    db.delete(playlist_track)
    playlist.duration -= track.duration

    # Переиндексация оставшихся треков
    remaining = db.query(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id
    ).order_by(PlaylistTracks.idx).all()
    for i, pt in enumerate(remaining):
        pt.idx = i

    db.commit()
    return

@router.post("/{playlist_id}/tracks/reorder", status_code=status.HTTP_200_OK)
def reorder_playlist_tracks(
    playlist_id: UUID,
    track_order: list[UUID],
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Изменение порядка треков (владелец или коллаборатор)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_edit=True
    )

    playlist_tracks = db.query(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id
    ).all()
    track_dict = {pt.track_id: pt for pt in playlist_tracks}

    if set(track_order) != set(track_dict.keys()):
        raise HTTPException(status_code=400, detail="Track list mismatch")

    for idx, track_id in enumerate(track_order):
        track_dict[track_id].idx = idx

    db.commit()
    return {"message": "Order updated"}

# ---------- Коллаборация ----------
@router.post("/{playlist_id}/collaborators", status_code=status.HTTP_200_OK)
def add_collaborator(
    playlist_id: UUID,
    collab_data: CollaboratorAdd,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавление соавтора в плейлист (только владелец)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_owner=True
    )

    # Определяем пользователя по ID или username
    user_to_add = None
    if collab_data.user_id:
        user_to_add = db.query(Users).filter(Users.id == collab_data.user_id).first()
    elif collab_data.username:
        user_to_add = db.query(Users).filter(Users.username == collab_data.username).first()
    else:
        raise HTTPException(status_code=400, detail="Provide user_id or username")

    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")
    if user_to_add.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as collaborator")

    # Проверяем, не является ли уже участником
    existing = db.query(UserPlaylists).filter(
        UserPlaylists.playlist_id == playlist_id,
        UserPlaylists.user_id == user_to_add.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already in playlist")

    # Добавляем как коллаборатора (is_feat=True)
    collab_link = UserPlaylists(
        user_id=user_to_add.id,
        playlist_id=playlist_id,
        idx=0,  # не важно для коллаборатора
        is_feat=True
    )
    db.add(collab_link)
    db.commit()

    return {"message": f"User {user_to_add.username} added as collaborator"}

@router.delete("/{playlist_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collaborator(
    playlist_id: UUID,
    user_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление соавтора из плейлиста (только владелец)."""
    playlist = get_playlist_with_access_check(
        playlist_id, current_user, db, require_owner=True
    )

    # Нельзя удалить владельца
    owner_link = db.query(UserPlaylists).filter(
        UserPlaylists.playlist_id == playlist_id,
        UserPlaylists.is_feat == False
    ).first()
    if owner_link and owner_link.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove owner")

    collab_link = db.query(UserPlaylists).filter(
        UserPlaylists.playlist_id == playlist_id,
        UserPlaylists.user_id == user_id,
        UserPlaylists.is_feat == True
    ).first()
    if not collab_link:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    db.delete(collab_link)
    db.commit()
    return

@router.post("/{playlist_id}/like", response_model=MessageResponse)
def like_playlist(
    playlist_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    existing = db.query(FavPlaylists).filter(
        FavPlaylists.user_id == current_user.id,
        FavPlaylists.playlist_id == playlist_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Playlist already in favorites")

    max_idx = db.query(func.max(FavPlaylists.idx)).filter(
        FavPlaylists.user_id == current_user.id
    ).scalar() or -1

    fav = FavPlaylists(
        user_id=current_user.id,
        playlist_id=playlist_id,
        idx=max_idx + 1
    )
    db.add(fav)
    playlist.likes += 1
    db.commit()
    return {"message": "Playlist added to favorites"}

@router.delete("/{playlist_id}/like", response_model=MessageResponse)
def unlike_playlist(
    playlist_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    fav = db.query(FavPlaylists).filter(
        FavPlaylists.user_id == current_user.id,
        FavPlaylists.playlist_id == playlist_id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Playlist not in favorites")

    db.delete(fav)
    playlist.likes -= 1
    db.commit()

    remaining = db.query(FavPlaylists).filter(
        FavPlaylists.user_id == current_user.id
    ).order_by(FavPlaylists.idx).all()
    for i, f in enumerate(remaining):
        f.idx = i
    db.commit()

    return {"message": "Playlist removed from favorites"}

@router.post("/{playlist_id}/wave", response_model=list[SimilarTrackResponse])
def get_playlist_wave(
    playlist_id: UUID,
    limit: int = 20,
    current_user: Users | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Бесконечная лента рекомендаций на основе треков плейлиста."""
    playlist = get_playlist_with_access_check(playlist_id, current_user, db)
    
    # Получаем треки плейлиста с векторами
    tracks = db.query(Track).join(PlaylistTracks).filter(
        PlaylistTracks.playlist_id == playlist_id,
        Track.feature_vector.is_not(None)
    ).all()
    
    if not tracks:
        raise HTTPException(status_code=400, detail="Playlist has no tracks with feature vectors")
    
    # Средний вектор
    import numpy as np
    vectors = [np.array(t.feature_vector) for t in tracks]
    mean_vector = np.mean(vectors, axis=0).tolist()
    vector_str = f"[{','.join(map(str, mean_vector))}]"
    
    # ID треков плейлиста для исключения
    playlist_track_ids = [t.id for t in tracks]
    
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
        "exclude_ids": playlist_track_ids,
        "limit": limit
    })
    
    rows = result.fetchall()
    response = []
    for r in rows:
        artists = db.query(Artist).join(ArtistTracks).filter(ArtistTracks.track_id == r.id).all()
        similarity = round(r.similarity * 100, 1)
        response.append(SimilarTrackResponse(
            id=r.id, name=r.name, duration=r.duration,
            artists=[ArtistBriefForTrack.model_validate(a) for a in artists],
            similarity=similarity
        ))
    return response