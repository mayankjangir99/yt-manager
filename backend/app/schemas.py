from datetime import datetime
from pydantic import BaseModel, Field

class VideoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    description: str | None = None
    tags: list[str] | None = None
    video_type: str | None = None
    category_id: str | None = None
    thumbnail_path: str | None = None

class ScheduleRequest(BaseModel):
    scheduled_at: datetime

class SettingsUpdate(BaseModel):
    folder_path: str | None = None
    folder_default_type: str | None = None
    watch_folder_enabled: bool | None = None
    auto_metadata: bool | None = None
    auto_schedule: bool | None = None
    auto_publish: bool | None = None
    shorts_per_week: int | None = Field(default=None, ge=0, le=28)
    long_videos_per_week: int | None = Field(default=None, ge=0, le=14)
    shorts_time: str | None = None
    long_videos_time: str | None = None
    publish_days: list[int] | None = None
    timezone: str | None = None
    default_visibility: str | None = None
