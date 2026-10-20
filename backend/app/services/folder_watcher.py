from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sqlalchemy.exc import IntegrityError
from ..database import SessionLocal
from ..models import Video, UploadLog
from .settings_service import get_settings
from .scheduler_service import schedule_video

SUPPORTED = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

def add_file(path: Path, source="folder"):
    if not path.is_file() or path.suffix.lower() not in SUPPORTED:
        return
    # Wait until the file appears stable (helps avoid importing a file still copying).
    import time
    try:
        size1 = path.stat().st_size
        time.sleep(1)
        size2 = path.stat().st_size
        if size1 != size2 or size2 == 0:
            return
    except OSError:
        return
    db = SessionLocal()
    try:
        existing = db.query(Video).filter(Video.file_path == str(path.resolve())).first()
        if existing:
            return
        cfg = get_settings(db)
        stem = path.stem.replace("_", " ").replace("-", " ").strip()
        video_type = "short" if "short" in path.name.lower() else cfg.get("folder_default_type", "long")
        video = Video(
            filename=path.name, file_path=str(path.resolve()),
            title=stem[:100], description="",
            tags_json="[]", video_type=video_type,
            source=source, status="draft",
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        db.add(UploadLog(video_id=video.id, message="Added to library from watched folder"))
        db.commit()
        if cfg.get("auto_metadata"):
            video.description = f"{stem}\\n\\nSubscribe for more videos."
            video.tags_json = '["youtube", "video"]'
        if cfg.get("auto_schedule"):
            try:
                schedule_video(db, video)
            except Exception as exc:
                video.last_error = str(exc)
        db.commit()
    except IntegrityError:
        db.rollback()
    finally:
        db.close()

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            add_file(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            add_file(Path(event.dest_path))

class FolderWatcher:
    def __init__(self):
        self.observer = None
        self.path = None

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.observer = None
        self.path = None

    def start(self, folder):
        folder_path = Path(folder).expanduser().resolve()
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError("Folder path does not exist or is not a directory on the backend computer.")
        if self.observer and self.path == str(folder_path):
            return
        self.stop()
        handler = Handler()
        self.observer = Observer()
        self.observer.schedule(handler, str(folder_path), recursive=False)
        self.observer.start()
        self.path = str(folder_path)
        # Import files already present in the folder too.
        for path in folder_path.iterdir():
            add_file(path)
