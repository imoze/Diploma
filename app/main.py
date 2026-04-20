from fastapi import FastAPI
from app.api.tracks import router as tracks_router

app = FastAPI(title="U:V API")


@app.get("/")
def root():
    return {"message": "U:V is alive"}

app.include_router(tracks_router)