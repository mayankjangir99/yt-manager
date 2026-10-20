from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from .database import Base, engine
from .config import allowed_frontend_origins, settings
from .routers import videos, settings as settings_router, youtube, logs
from .services.scheduler_service import run_due_jobs
from .services.settings_service import get_settings
from .database import SessionLocal

scheduler = BackgroundScheduler(timezone=settings.timezone)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if not scheduler.running:
        scheduler.add_job(run_due_jobs, "interval", seconds=30, id="upload_jobs", max_instances=1, coalesce=True)
        scheduler.start()
    db = SessionLocal()
    try:
        cfg = get_settings(db)
        if cfg.get("watch_folder_enabled") and cfg.get("folder_path"):
            try:
                settings_router.watcher.start(cfg["folder_path"])
            except Exception:
                pass
    finally:
        db.close()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
    settings_router.watcher.stop()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(videos.router)
app.include_router(settings_router.router)
app.include_router(youtube.router)
app.include_router(logs.router)

@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name}
