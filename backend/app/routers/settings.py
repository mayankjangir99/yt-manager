from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import SettingsUpdate
from ..services.settings_service import get_settings, update_settings
from ..services.folder_watcher import FolderWatcher
from ..config import settings as app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
watcher = FolderWatcher()

@router.get("")
def read_settings(db: Session = Depends(get_db)):
    cfg = get_settings(db)
    cfg["watcher_running"] = watcher.observer is not None and watcher.observer.is_alive()
    return cfg

@router.put("")
def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    values = payload.model_dump(exclude_unset=True)
    if "publish_days" in values and values["publish_days"] is not None:
        if any(day not in range(7) for day in values["publish_days"]):
            raise HTTPException(400, "Publishing days must be 0 (Monday) through 6 (Sunday).")
    if "folder_path" in values and values["folder_path"]:
        p = Path(values["folder_path"]).expanduser()
        if not p.exists() or not p.is_dir():
            raise HTTPException(400, "Folder path must exist on the computer running the backend.")
    cfg = update_settings(db, values)
    if cfg.get("watch_folder_enabled") and cfg.get("folder_path"):
        try:
            watcher.start(cfg["folder_path"])
        except Exception as exc:
            raise HTTPException(400, str(exc))
    else:
        watcher.stop()
    cfg["watcher_running"] = watcher.observer is not None and watcher.observer.is_alive()
    return cfg

@router.post("/browse-folder")
def browse_folder():
    # Web browsers cannot open a native directory picker on the backend host securely.
    # User enters/pastes a local path, then backend validates it.
    return {"message": "Enter a folder path that exists on the computer running the backend."}
