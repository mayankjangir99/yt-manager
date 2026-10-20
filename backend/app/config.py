from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    app_name: str = "AI YouTube Channel Manager"
    database_url: str = "sqlite:///./youtube_manager.db"
    # Vite may be opened as either localhost or 127.0.0.1.  Those are
    # separate browser origins, so both must be allowed by CORS.
  frontend_origins: str = "https://yt-manager-ashen.vercel.app"
    backend_origin: str = "https://yt-manager-528b.onrender.com"
    timezone: str = "Asia/Kolkata"
    storage_dir: str = "storage"
    google_client_secret_file: str = "youtube_client_secret.json"
    google_token_file: str = "youtube_token.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

def allowed_frontend_origins() -> list[str]:
    return [origin.strip().rstrip("/") for origin in settings.frontend_origins.split(",") if origin.strip()]
def backend_path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p
