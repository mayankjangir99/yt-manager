import json, shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Video, UploadLog
from ..schemas import VideoUpdate, ScheduleRequest
from ..config import backend_path, settings
from ..services.scheduler_service import schedule_video, log
from ..services.settings_service import get_settings
from ..services.youtube_service import upload_video

router = APIRouter(prefix="/api/videos", tags=["videos"])
ALLOWED = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

def serialize(v: Video):
    return {
        "id": v.id, "filename": v.filename, "file_path": v.file_path,
        "title": v.title, "description": v.description,
        "tags": json.loads(v.tags_json or "[]"), "video_type": v.video_type,
        "category_id": v.category_id, "thumbnail_path": v.thumbnail_path,
        "source": v.source, "status": v.status,
        "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None,
        "youtube_video_id": v.youtube_video_id, "last_error": v.last_error,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }

@router.get("")
def list_videos(db: Session = Depends(get_db)):
    return [serialize(v) for v in db.query(Video).order_by(Video.created_at.desc()).all()]

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    video_type: str = Form("short"),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, "Unsupported video format.")
    storage = backend_path(settings.storage_dir) / "videos"
    storage.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "video.mp4").name
    target = storage / safe_name
    if target.exists():
        target = storage / f"{Path(safe_name).stem}_{int(__import__('time').time())}{suffix}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    cfg = get_settings(db)
    stem = target.stem.replace("_", " ").replace("-", " ")
    video = Video(
        filename=target.name, file_path=str(target.resolve()),
        title=stem[:100], description="", tags_json="[]",
        video_type=video_type if video_type in ("short", "long") else "short",
        source="manual", status="draft",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    if cfg.get("auto_metadata"):
        video.description = f"{stem}\\n\\nSubscribe for more videos."
        video.tags_json = '["youtube", "video"]'
        db.commit()
    log(db, "Manual upload added to library", video_id=video.id)
    return serialize(video)

@router.patch("/{video_id}")
def update_video(video_id: int, payload: VideoUpdate, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    values = payload.model_dump(exclude_unset=True)
    if "tags" in values:
        video.tags_json = json.dumps(values.pop("tags") or [])
    if "title" in values and values["title"] and len(values["title"]) > 100:
        raise HTTPException(400, "YouTube titles must be 100 characters or fewer.")
    for key, value in values.items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return serialize(video)

@router.post("/{video_id}/schedule")
def schedule(video_id: int, payload: ScheduleRequest, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    try:
        result = schedule_video(db, video, payload.scheduled_at)
        return serialize(result)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.post("/{video_id}/auto-schedule")
def auto_schedule(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    try:
        return serialize(schedule_video(db, video))
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.post("/{video_id}/upload-now")
def upload_now(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    if video.youtube_video_id:
        raise HTTPException(400, "This video has already been uploaded.")
    try:
        video.status = "uploading"
        db.commit()
        cfg = get_settings(db)
        visibility = cfg.get("default_visibility", "private")
        if visibility not in ("private", "unlisted", "public"):
            visibility = "private"
        vid = upload_video(video, privacy_status=visibility)
        video.youtube_video_id = vid
        video.status = "uploaded_private"
        video.last_error = None
        db.commit()
        log(db, f"Uploaded as private (video ID: {vid})", video_id=video.id)
        return serialize(video)
    except Exception as exc:
        video.status = "failed"
        video.last_error = str(exc)[:2000]
        db.commit()
        log(db, f"Upload failed: {exc}", "error", video.id)
        raise HTTPException(500, f"Upload failed: {exc}")

@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    if video.youtube_video_id:
        raise HTTPException(400, "Cannot delete a library item after it has been uploaded to YouTube.")
    db.delete(video)
    db.commit()
    return {"ok": True}
