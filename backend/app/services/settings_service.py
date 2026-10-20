import json
from sqlalchemy.orm import Session
from ..models import AppSetting

DEFAULTS = {
    "folder_path": "",
    "folder_default_type": "long",
    "watch_folder_enabled": False,
    "auto_metadata": True,
    "auto_schedule": True,
    "auto_publish": False,
    "shorts_per_week": 5,
    "long_videos_per_week": 2,
    "shorts_time": "18:00",
    "long_videos_time": "12:00",
    "publish_days": [0, 1, 2, 3, 4, 5, 6],
    "timezone": "Asia/Kolkata",
    "default_visibility": "private",
}

def get_settings(db: Session):
    result = DEFAULTS.copy()
    for item in db.query(AppSetting).all():
        try:
            result[item.key] = json.loads(item.value_json)
        except json.JSONDecodeError:
            pass
    return result

def update_settings(db: Session, updates: dict):
    current = get_settings(db)
    for key, value in updates.items():
        if value is not None and key in DEFAULTS:
            current[key] = value
            row = db.get(AppSetting, key)
            encoded = json.dumps(value)
            if row:
                row.value_json = encoded
            else:
                db.add(AppSetting(key=key, value_json=encoded))
    db.commit()
    return get_settings(db)
