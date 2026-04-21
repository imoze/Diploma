from uuid6 import uuid7
from sqlalchemy import (
    Column, Text, Integer, BigInteger, Date, Boolean,
    ForeignKey, DateTime, Float, Enum,
    CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


# ---------------- ENUM ----------------

source_enum = Enum(
    "None", "Fav", "Search", "Recommendations",
    "Album", "Playlist", "Artist",
    name="source_enum",
    create_type=False
)


# ---------------- MAIN ----------------

class Track(Base):
    __tablename__ = "track"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(Text, nullable=False)
    release_date = Column(Date, nullable=False)

    duration = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("duration > 0"),)

    likes = Column(BigInteger, default=0, nullable=False)
    plays = Column(BigInteger, default=0, nullable=False)

    feature_vector = Column(Vector(150))
    track_path = Column(Text, nullable=False)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)

    duration = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("duration > 0"),)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(Text, nullable=False)
    release_date = Column(Date, nullable=False)

    duration = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("duration > 0"),)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
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

    time = Column(DateTime, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id"), primary_key=True)

    completion_percent = Column(Float, nullable=False)
    __table_args__ = (CheckConstraint("completion_percent >= 0 AND completion_percent <= 1"),)

    source = Column(source_enum, nullable=False)
    source_details = Column(JSONB)

    user = relationship("Users", back_populates="history")
    track = relationship("Track", back_populates="history")


# ---------------- OTHER ----------------

class Role(Base):
    __tablename__ = "role"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(Text, nullable=False)

    member_links = relationship("MemberRoles", back_populates="role")
    artist_links = relationship("ArtistMembers", back_populates="role")


class Privilege(Base):
    __tablename__ = "privilege"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    function_procedure = Column(Text, nullable=False)

    admin_links = relationship("AdminPrivileges", back_populates="privilege")


class Log(Base):
    __tablename__ = "log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admin.id"))

    action = Column(Text, nullable=False)
    table_name = Column(Text, nullable=False)

    previous_value = Column(JSONB, nullable=False)
    new_value = Column(JSONB, nullable=False)

    datetime = Column(DateTime)

    admin = relationship("Admin", back_populates="logs")


class Member(Base):
    __tablename__ = "member"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    pseudonim = Column(Text)
    full_name = Column(Text, nullable=False)
    birth_date = Column(Date, nullable=False)
    biography = Column(Text)

    user = relationship("Users", back_populates="member")
    artist_links = relationship("ArtistMembers", back_populates="member", passive_deletes=True)
    roles = relationship("MemberRoles", back_populates="member", passive_deletes=True)


class Admin(Base):
    __tablename__ = "admin"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)

    role = Column(Text, nullable=False)
    description = Column(Text)

    hiring_date = Column(Date, nullable=False)
    dismissal_date = Column(Date)

    user = relationship("Users", back_populates="admin")
    logs = relationship("Log", back_populates="admin")
    privileges = relationship("AdminPrivileges", back_populates="admin")


# ---------------- ASSOCIATION ----------------

class FavTracks(Base):
    __tablename__ = "fav_tracks"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id", ondelete="CASCADE"), primary_key=True)
    idx = Column(Integer, nullable=False)

    user = relationship("Users", back_populates="fav_tracks")
    track = relationship("Track", back_populates="fav_links")


class FavPlaylists(Base):
    __tablename__ = "fav_playlists"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlist.id", ondelete="CASCADE"), primary_key=True)
    idx = Column(Integer, nullable=False)

    user = relationship("Users", back_populates="fav_playlists")
    playlist = relationship("Playlist", back_populates="fav_links")


class FavAlbums(Base):
    __tablename__ = "fav_albums"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    album_id = Column(UUID(as_uuid=True), ForeignKey("album.id", ondelete="CASCADE"), primary_key=True)
    idx = Column(Integer, nullable=False)

    user = relationship("Users", back_populates="fav_albums")
    album = relationship("Album", back_populates="fav_links")


class FavArtists(Base):
    __tablename__ = "fav_artists"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True)
    idx = Column(Integer, nullable=False)

    user = relationship("Users", back_populates="fav_artists")
    artist = relationship("Artist", back_populates="fav_links")


class UserPlaylists(Base):
    __tablename__ = "user_playlists"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlist.id", ondelete="CASCADE"), primary_key=True)

    idx = Column(Integer, nullable=False)
    is_feat = Column(Boolean, nullable=False)

    user = relationship("Users", back_populates="playlists")
    playlist = relationship("Playlist", back_populates="user_links")


class PlaylistTracks(Base):
    __tablename__ = "playlist_tracks"

    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlist.id", ondelete="CASCADE"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id", ondelete="CASCADE"), primary_key=True)

    idx = Column(Integer, nullable=False)

    playlist = relationship("Playlist", back_populates="track_links")
    track = relationship("Track", back_populates="playlist_links")


class AlbumTracks(Base):
    __tablename__ = "album_tracks"

    album_id = Column(UUID(as_uuid=True), ForeignKey("album.id", ondelete="CASCADE"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id", ondelete="CASCADE"), primary_key=True)

    idx = Column(Integer, nullable=False)

    album = relationship("Album", back_populates="track_links")
    track = relationship("Track", back_populates="album_links")


class ArtistTracks(Base):
    __tablename__ = "artist_tracks"

    artist_id = Column(UUID(as_uuid=True), ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("track.id", ondelete="CASCADE"), primary_key=True)

    idx = Column(Integer, nullable=False)
    is_feat = Column(Boolean, nullable=False)

    artist = relationship("Artist", back_populates="track_links")
    track = relationship("Track", back_populates="artist_links")


class ArtistAlbums(Base):
    __tablename__ = "artist_albums"

    artist_id = Column(UUID(as_uuid=True), ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True)
    album_id = Column(UUID(as_uuid=True), ForeignKey("album.id", ondelete="CASCADE"), primary_key=True)

    idx = Column(Integer, nullable=False)
    is_feat = Column(Boolean, nullable=False)

    artist = relationship("Artist", back_populates="album_links")
    album = relationship("Album", back_populates="artist_links")


class ArtistMembers(Base):
    __tablename__ = "artist_members"

    artist_id = Column(UUID(as_uuid=True), ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("member.id", ondelete="CASCADE"), primary_key=True)

    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), nullable=False)

    joining_date = Column(Date, nullable=False)
    leaving_date = Column(Date)

    artist = relationship("Artist", back_populates="member_links")
    member = relationship("Member", back_populates="artist_links")
    role = relationship("Role", back_populates="artist_links")


class MemberRoles(Base):
    __tablename__ = "member_roles"

    member_id = Column(UUID(as_uuid=True), ForeignKey("member.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), primary_key=True)

    member = relationship("Member", back_populates="roles")
    role = relationship("Role", back_populates="member_links")


class AdminPrivileges(Base):
    __tablename__ = "admin_privileges"

    admin_id = Column(UUID(as_uuid=True), ForeignKey("admin.id", ondelete="CASCADE"), primary_key=True)
    privilege_id = Column(UUID(as_uuid=True), ForeignKey("privilege.id", ondelete="CASCADE"), primary_key=True)

    grant_time = Column(DateTime, nullable=False)
    revoke_time = Column(DateTime)

    admin = relationship("Admin", back_populates="privileges")
    privilege = relationship("Privilege", back_populates="admin_links")