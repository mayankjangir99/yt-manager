from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import UploadLog

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("")
def list_logs(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    return [
        {"id": x.id, "video_id": x.video_id, "level": x.level,
         "message": x.message, "created_at": x.created_at.isoformat()}
        for x in db.query(UploadLog).order_by(UploadLog.created_at.desc()).limit(limit).all()
    ]
