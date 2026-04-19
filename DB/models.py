import uuid
from sqlalchemy import (
    Column, Text, Integer, BigInteger, Date, Boolean,
    ForeignKey, DateTime, Float, Enum,
    CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

from pgvector.sqlalchemy import Vector

Base = declarative_base()


# ---------------- ENUM ----------------

source_enum = Enum(
    "None", "Fav", "Search", "Recomendations",
    "Album", "Playlist", "Artist",
    name="source_enum",
    create_type=False
)


# ---------------- MAIN ----------------

class Track(Base):
    __tablename__ = "track"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    release_date = Column(Date, nullable=False)

    duration = Column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint("duration > 0"),
    )

    likes = Column(BigInteger, default=0, nullable=False)
    plays = Column(BigInteger, default=0, nullable=False)

    parts_plays = Column(Vector(100))
    feature_vector = Column(Vector(150))

    history = relationship("History", back_populates="track", lazy="selectin")

    fav_links = relationship("FavTracks", back_populates="track", passive_deletes=True, lazy="selectin")
    playlist_links = relationship("PlaylistTracks", back_populates="track", passive_deletes=True, lazy="selectin")
    album_links = relationship("AlbumTracks", back_populates="track", passive_deletes=True, lazy="selectin")
    artist_links = relationship("ArtistTracks", back_populates="track", passive_deletes=True, lazy="selectin")

    @property
    def artists(self):
        return [l.artist for l in self.artist_links]

    @property
    def albums(self):
        return [l.album for l in self.album_links]

    @property
    def playlists(self):
        return [l.playlist for l in self.playlist_links]


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)

    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)

    is_fav_tracks_public = Column(Boolean, nullable=False)
    is_fav_playlists_public = Column(Boolean, nullable=False)
    is_fav_artists_public = Column(Boolean, nullable=False)
    is_fav_albums_public = Column(Boolean, nullable=False)

    is_member = Column(Boolean, nullable=False)
    is_admin = Column(Boolean, nullable=False)

    history = relationship("History", back_populates="user", lazy="selectin")

    fav_tracks = relationship("FavTracks", back_populates="user", passive_deletes=True, lazy="selectin")
    fav_playlists = relationship("FavPlaylists", back_populates="user", passive_deletes=True, lazy="selectin")
    fav_albums = relationship("FavAlbums", back_populates="user", passive_deletes=True, lazy="selectin")
    fav_artists = relationship("FavArtists", back_populates="user", passive_deletes=True, lazy="selectin")

    playlists = relationship("UserPlaylists", back_populates="user", passive_deletes=True, lazy="selectin")

    member = relationship("Member", back_populates="user", uselist=False, passive_deletes=True)
    admin = relationship("Admin", back_populates="user", uselist=False, passive_deletes=True)

    @property
    def favorite_tracks(self):
        return [l.track for l in sorted(self.fav_tracks, key=lambda x: x.idx)]

    @property
    def favorite_playlists(self):
        return [l.playlist for l in sorted(self.fav_playlists, key=lambda x: x.idx)]

    @property
    def favorite_albums(self):
        return [l.album for l in sorted(self.fav_albums, key=lambda x: x.idx)]

    @property
    def favorite_artists(self):
        return [l.artist for l in sorted(self.fav_artists, key=lambda x: x.idx)]

    @property
    def owned_playlists(self):
        return [l.playlist for l in sorted(self.playlists, key=lambda x: x.idx)]


class Playlist(Base):
    __tablename__ = "playlist"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    duration = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("duration > 0"),
    )

    likes = Column(BigInteger, default=0, nullable=False)
    plays = Column(BigInteger, default=0, nullable=False)

    is_public = Column(Boolean, nullable=False)

    track_links = relationship("PlaylistTracks", back_populates="playlist", passive_deletes=True, lazy="selectin")
    fav_links = relationship("FavPlaylists", back_populates="playlist", passive_deletes=True, lazy="selectin")
    user_links = relationship("UserPlaylists", back_populates="playlist", passive_deletes=True, lazy="selectin")

    @property
    def tracks(self):
        return [l.track for l in sorted(self.track_links, key=lambda x: x.idx)]


class AlbumTypes(Base):
    __tablename__ = "album_types"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)

    albums = relationship("Album", back_populates="album_type", lazy="selectin")


class Album(Base):
    __tablename__ = "album"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    release_date = Column(Date, nullable=False)

    duration = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("duration > 0"),
    )

    likes = Column(BigInteger, default=0, nullable=False)
    plays = Column(BigInteger, default=0, nullable=False)

    album_type_id = Column(UUID(as_uuid=True), ForeignKey("album_types.id"))

    album_type = relationship("AlbumTypes", back_populates="albums")

    track_links = relationship("AlbumTracks", back_populates="album", passive_deletes=True, lazy="selectin")
    artist_links = relationship("ArtistAlbums", back_populates="album", passive_deletes=True, lazy="selectin")
    fav_links = relationship("FavAlbums", back_populates="album", passive_deletes=True, lazy="selectin")

    @property
    def tracks(self):
        return [l.track for l in sorted(self.track_links, key=lambda x: x.idx)]

    @property
    def artists(self):
        return [l.artist for l in self.artist_links]


class Artist(Base):
    __tablename__ = "artist"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)

    formation_date = Column(Date, nullable=False)
    disbandment_date = Column(Date)

    likes = Column(BigInteger, default=0, nullable=False)
    plays = Column(BigInteger, default=0, nullable=False)

    track_links = relationship("ArtistTracks", back_populates="artist", passive_deletes=True, lazy="selectin")
    album_links = relationship("ArtistAlbums", back_populates="artist", passive_deletes=True, lazy="selectin")
    member_links = relationship("ArtistMembers", back_populates="artist", passive_deletes=True, lazy="selectin")
    fav_links = relationship("FavArtists", back_populates="artist", passive_deletes=True, lazy="selectin")

    @property
    def tracks(self):
        return [l.track for l in sorted(self.track_links, key=lambda x: x.idx)]

    @property
    def albums(self):
        return [l.album for l in self.album_links]

    @property
    def members(self):
        return [l.member for l in self.member_links]


# ---------------- HISTORY ----------------

class History(Base):
    __tablename__ = "history"

    time = Column(DateTime(timezone=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id"), primary_key=True)

    completion_percent = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("completion_percent >= 0 AND completion_percent <= 1"),
        Index("ix_history_user", "user_id"),
        Index("ix_history_track", "track_id"),
    )

    source = Column(source_enum, nullable=False)
    source_details = Column(JSONB, default=dict)

    user = relationship("Users", back_populates="history")
    track = relationship("Track", back_populates="history")


# ---------------- MEMBER / ADMIN ----------------

class Member(Base):
    __tablename__ = "member"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    pseudonim = Column(Text)
    full_name = Column(Text, nullable=False)
    birth_date = Column(Date, nullable=False)
    biography = Column(Text)

    user = relationship("Users", back_populates="member")
    artist_links = relationship("ArtistMembers", back_populates="member", passive_deletes=True, lazy="selectin")
    roles = relationship("MemberRoles", back_populates="member", passive_deletes=True, lazy="selectin")

    @property
    def artists(self):
        return [l.artist for l in self.artist_links]

    @property
    def roles_list(self):
        return [l.role for l in self.roles]


class Admin(Base):
    __tablename__ = "admin"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)

    role = Column(Text, nullable=False)
    description = Column(Text)

    hiring_date = Column(Date, nullable=False)
    dismissal_date = Column(Date)

    user = relationship("Users", back_populates="admin")
    logs = relationship("Log", back_populates="admin", passive_deletes=True, lazy="selectin")
    privileges = relationship("AdminPrivileges", back_populates="admin", passive_deletes=True, lazy="selectin")

    @property
    def privileges_list(self):
        return [l.privilege for l in self.privileges]


# ---------------- ASSOCIATION ----------------

class PlaylistTracks(Base):
    __tablename__ = "playlist_tracks"

    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlist.id"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id"), primary_key=True)

    idx = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("playlist_id", "idx"),
        Index("ix_playlist_tracks_playlist", "playlist_id"),
    )

    playlist = relationship("Playlist", back_populates="track_links")
    track = relationship("Track", back_populates="playlist_links")