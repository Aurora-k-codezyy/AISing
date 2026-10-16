from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, commerce, jobs, local_songs
from app.core.config import get_settings
from app.core.database import create_tables
from app.core.logging_config import configure_logging
from app.core.database import SessionLocal
from app.services.bootstrap import ensure_defaults
from app.workers.worker import BackgroundWorker


worker = BackgroundWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_dir / "server.log", settings.log_level)
    create_tables()
    with SessionLocal() as db:
        ensure_defaults(db, settings)
    if settings.worker_enabled:
        await worker.start()
    try:
        yield
    finally:
        if settings.worker_enabled:
            await worker.stop()


app = FastAPI(title="AI Sing MVP", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(commerce.router)
app.include_router(admin.router)
app.include_router(jobs.oss_router)
app.include_router(jobs.router)
app.include_router(local_songs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

