from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tracks import router as tracks_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.playlists import router as playlists_router
from app.api.artists import router as artists_router
from app.api.albums import router as albums_router

app = FastAPI(title="U:V API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:5500"],  # Для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "U:V is alive"}

app.include_router(tracks_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(playlists_router)
app.include_router(artists_router)
app.include_router(albums_router)