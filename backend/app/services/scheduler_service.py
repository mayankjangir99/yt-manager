import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session
from ..models import Video, UploadLog
from .settings_service import get_settings
from .youtube_service import upload_video

def log(db, message, level="info", video_id=None):
    db.add(UploadLog(video_id=video_id, message=message, level=level))
    db.commit()

def choose_next_slot(db: Session, video: Video):
    cfg = get_settings(db)
    tz_name = cfg.get("timezone", "Asia/Kolkata")
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    now = datetime.now(tz)
    per_week = cfg["shorts_per_week"] if video.video_type == "short" else cfg["long_videos_per_week"]
    if per_week <= 0:
        return None
    time_text = cfg["shorts_time"] if video.video_type == "short" else cfg["long_videos_time"]
    try:
        hour, minute = map(int, time_text.split(":"))
    except Exception:
        hour, minute = 18, 0
    allowed_days = set(cfg.get("publish_days", list(range(7))))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    for offset in range(0, 60):
        day = candidate + timedelta(days=offset)
        if day.weekday() not in allowed_days:
            continue
        # Weekly quota is a target/limit for newly assigned jobs.
        week_start = (day - timedelta(days=day.weekday())).date()
        week_end = week_start + timedelta(days=7)
        count = 0
        for item in db.query(Video).filter(Video.scheduled_at.is_not(None)).all():
            when = item.scheduled_at
            if when and when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when:
                local_date = when.astimezone(tz).date()
                if week_start <= local_date < week_end and item.video_type == video.video_type:
                    count += 1
        if count < per_week:
            return candidate.astimezone(timezone.utc)
        # Find a day in a later week if this week's quota is full.
    return None

def schedule_video(db: Session, video: Video, at: datetime | None = None):
    if at is None:
        at = choose_next_slot(db, video)
    if at is None:
        raise ValueError("No available schedule slot. Check publishing days and weekly limits.")
    if at.tzinfo is None:
        raise ValueError("Schedule time must include timezone.")
    video.scheduled_at = at
    video.status = "scheduled"
    video.last_error = None
    db.commit()
    log(db, f"Scheduled for {at.isoformat()}", video_id=video.id)
    return video

def run_due_jobs():
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Scheduled jobs are uploaded in advance to YouTube with publishAt.
        pending = db.query(Video).filter(
            Video.status == "scheduled",
            Video.youtube_video_id.is_(None),
            Video.scheduled_at.is_not(None),
            Video.scheduled_at > now + timedelta(minutes=2),
        ).order_by(Video.scheduled_at.asc()).limit(2).all()
        cfg = get_settings(db)
        for video in pending:
            try:
                if not cfg.get("auto_publish", False):
                    continue
                video.status = "uploading"
                db.commit()
                vid = upload_video(video, video.scheduled_at)
                video.youtube_video_id = vid
                video.status = "scheduled_on_youtube"
                video.last_error = None
                db.commit()
                log(db, f"Uploaded to YouTube and scheduled (video ID: {vid})", video_id=video.id)
            except Exception as exc:
                video.status = "failed"
                video.last_error = str(exc)[:2000]
                db.commit()
                log(db, f"Upload failed: {exc}", "error", video.id)
    finally:
        db.close()
