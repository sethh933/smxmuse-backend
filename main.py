from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import FRONTEND_ORIGINS
from routers.comparisons import router as comparisons_router
from routers.leaderboards import router as leaderboards_router
from routers.races import router as races_router
from routers.riders import router as riders_router
from routers.search import router as search_router
from routers.seasons import router as seasons_router
from routers.tracks import router as tracks_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "SMX Muse Leaderboard API is running."}


app.include_router(leaderboards_router)
app.include_router(search_router)
app.include_router(tracks_router)
app.include_router(races_router)
app.include_router(seasons_router)
app.include_router(comparisons_router)
app.include_router(riders_router)
