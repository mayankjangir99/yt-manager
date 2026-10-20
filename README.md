# AI YouTube Channel Manager (GUI-only)

Separate React + Vite frontend and FastAPI backend. Includes manual uploads, local folder watching, editable metadata, saved scheduling rules, SQLite persistence, Google OAuth, and YouTube uploads.

## Requirements
- Python 3.11+
- Node.js 20+
- A Google Cloud project with YouTube Data API v3 enabled
- OAuth client credentials for a Web application

## 1. Configure Google OAuth
In Google Cloud Console:
1. Create/select a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen and add your Google account as a test user if the app is in Testing.
3. Create an OAuth client ID of type **Web application**.
4. Add this authorized redirect URI exactly: `http://127.0.0.1:8081/api/youtube/oauth/callback`
5. Download the OAuth client JSON and save it as `backend/youtube_client_secret.json`.

Check current YouTube API project/audit restrictions before relying on public automatic publishing. New/unverified projects may be restricted to private uploads.

## 2. Backend setup (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8081
```

## 3. Frontend setup (second terminal)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
Open http://localhost:5173

## 4. First-run workflow
1. Open Settings and connect YouTube.
2. Choose the folder to watch (the path must be on the computer running the backend).
3. Set allowed publishing days, time slots, and weekly limits.
4. Use Upload Video for manual uploads, or place supported video files in the watched folder.
5. Review/edit metadata and enable automatic scheduling. Enable auto-publish only if you want the system to schedule videos without review.

## Important behavior
- Files discovered in a watched folder are added to the queue; they are not uploaded until automation is enabled.
- Auto metadata generation uses deterministic starter templates. Connect an AI provider later if you want AI-written titles/descriptions.
- Automatic public publishing is off by default.
- For scheduled YouTube uploads, the backend uploads the video as private and sets `publishAt` to a future time. YouTube's API/project restrictions apply.
- Keep `youtube_client_secret.json`, OAuth tokens, and `.env` private. Do not commit them to GitHub.
- This is a starter implementation, not a hardened multi-user production service. Do not expose the local backend directly to the public internet.
