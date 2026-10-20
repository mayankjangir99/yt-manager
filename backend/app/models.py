from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000), unique=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    video_type: Mapped[str] = mapped_column(String(20), default="short")
    category_id: Mapped[str] = mapped_column(String(10), default="22")
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)

class UploadLog(Base):
    __tablename__ = "upload_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int | None] = mapped_column(ForeignKey("videos.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
