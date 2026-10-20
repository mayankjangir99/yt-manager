from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from ..config import allowed_frontend_origins, settings
from ..services import youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

@router.get("/status")
def status():
    try:
        summary = youtube_service.channel_summary()
        return summary
    except Exception:
        return {"connected": youtube_service.load_credentials() is not None, "channel": None}

@router.get("/oauth/start")
def oauth_start():
    try:
        return {"authorization_url": youtube_service.start_oauth_authorization()}
    except Exception as exc:
        raise HTTPException(400, str(exc))

@router.get("/oauth/callback")
def oauth_callback(
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if not state:
        raise HTTPException(400, "OAuth state is missing. Start connection again.")
    code_verifier = youtube_service.consume_oauth_verifier(state)
    if not code_verifier:
        raise HTTPException(400, "OAuth state mismatch or authorization expired. Start connection again.")
    if error:
        detail = error_description or error
        raise HTTPException(400, f"OAuth authorization was not completed: {detail}")
    if not code:
        raise HTTPException(400, "OAuth callback did not include an authorization code.")
    try:
        flow = youtube_service.make_flow(state=state, code_verifier=code_verifier)
        flow.fetch_token(code=code)
        youtube_service.save_credentials(flow.credentials)
        return RedirectResponse(f"{allowed_frontend_origins()[0]}/?youtube=connected")
    except Exception as exc:
        raise HTTPException(400, f"OAuth failed: {exc}")

@router.get("/analytics")
def analytics():
    try:
        youtube = youtube_service.youtube_client()
        channel = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        items = channel.get("items", [])
        if not items:
            return {"channel": None, "videos": []}
        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"] if "contentDetails" in items[0] else None
        return {
            "channel": items[0]["snippet"]["title"],
            "statistics": items[0].get("statistics", {}),
            "note": "For full reports by date, integrate YouTube Analytics reports.query with channel owner authorization."
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))
