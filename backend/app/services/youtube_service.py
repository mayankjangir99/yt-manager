import json
import os
import secrets
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ..config import settings, backend_path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
OAUTH_PENDING_FILE = "oauth_pending.json"
OAUTH_PENDING_TTL_SECONDS = 10 * 60

def client_secret_path() -> Path:
    return backend_path(settings.google_client_secret_file)

def token_path() -> Path:
    return backend_path(settings.google_token_file)

def make_flow(state: str | None = None, code_verifier: str | None = None):
    secret = client_secret_path()
    if not secret.exists():
        raise RuntimeError(
            f"OAuth client file not found: {secret}. Download a Google OAuth Web client JSON."
        )
    flow = Flow.from_client_secrets_file(
        str(secret), scopes=SCOPES, state=state,
        redirect_uri=f"{settings.backend_origin}/api/youtube/oauth/callback",
        code_verifier=code_verifier,
    )
    return flow

def oauth_pending_path() -> Path:
    return backend_path(OAUTH_PENDING_FILE)

def _read_pending_oauth() -> dict:
    path = oauth_pending_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def _write_pending_oauth(pending: dict) -> None:
    """Atomically persist short-lived PKCE verifiers for local OAuth attempts."""
    path = oauth_pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(pending, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    os.replace(temp_name, path)

def _prune_pending_oauth(pending: dict, now: float) -> dict:
    valid = {}
    for state, item in pending.items():
        created_at = item.get("created_at") if isinstance(item, dict) else None
        if (
            isinstance(item, dict)
            and isinstance(item.get("code_verifier"), str)
            and isinstance(created_at, (int, float))
            and now - created_at <= OAUTH_PENDING_TTL_SECONDS
        ):
            valid[state] = item
    return valid

def start_oauth_authorization() -> str:
    """Create an OAuth URL and retain the one-time PKCE verifier for its callback."""
    # RFC 7636 permits 43-128 URL-safe characters. token_urlsafe(64) is 86 chars.
    code_verifier = secrets.token_urlsafe(64)
    flow = make_flow(code_verifier=code_verifier)
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    if not state:
        raise RuntimeError("OAuth provider did not return an authorization state.")
    now = time.time()
    pending = _prune_pending_oauth(_read_pending_oauth(), now)
    pending[state] = {"code_verifier": code_verifier, "created_at": now}
    _write_pending_oauth(pending)
    return url

def consume_oauth_verifier(state: str) -> str | None:
    """Validate and consume the PKCE verifier for one callback attempt."""
    now = time.time()
    pending = _prune_pending_oauth(_read_pending_oauth(), now)
    item = pending.pop(state, None)
    _write_pending_oauth(pending)
    if not isinstance(item, dict):
        return None
    verifier = item.get("code_verifier")
    return verifier if isinstance(verifier, str) and verifier else None

def save_credentials(creds):
    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    token_path().write_text(json.dumps(payload), encoding="utf-8")

def load_credentials():
    path = token_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    expiry = datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
        expiry=expiry,
    )

def youtube_client():
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Connect your YouTube channel in Settings first.")
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        save_credentials(creds)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload_video(video, scheduled_at=None, privacy_status="private"):
    youtube = youtube_client()
    # Scheduled publication must start as private; immediate uploads may use the saved visibility.
    status = {"privacyStatus": "private" if scheduled_at else privacy_status, "selfDeclaredMadeForKids": False}
    if scheduled_at:
        dt = scheduled_at
        if dt.tzinfo is None:
            raise ValueError("Scheduled time must include a timezone.")
        if dt <= datetime.now(dt.tzinfo):
            raise ValueError("Scheduled time must be in the future.")
        status["publishAt"] = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    body = {
        "snippet": {
            "title": (video.title or video.filename)[:100],
            "description": video.description or "",
            "tags": json.loads(video.tags_json or "[]")[:500],
            "categoryId": video.category_id or "22",
        },
        "status": status,
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video.file_path, mimetype="video/*", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response.get("id")
    if video.thumbnail_path and Path(video.thumbnail_path).exists() and video_id:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(video.thumbnail_path, mimetype="image/jpeg"),
        ).execute()
    return video_id

def channel_summary():
    youtube = youtube_client()
    response = youtube.channels().list(part="snippet,statistics", mine=True).execute()
    items = response.get("items", [])
    if not items:
        return {"connected": True, "channel": None}
    ch = items[0]
    return {
        "connected": True,
        "channel": {
            "title": ch["snippet"]["title"],
            "thumbnail": ch["snippet"]["thumbnails"].get("default", {}).get("url"),
            "subscriber_count": ch["statistics"].get("subscriberCount"),
            "view_count": ch["statistics"].get("viewCount"),
            "video_count": ch["statistics"].get("videoCount"),
        }
    }
