from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import os

app = FastAPI(title="Snap Media Backend")

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"

class DownloadStatus(BaseModel):
    status: str = "pending"
    progress: float = 0.0
    speed: str = "0 B/s"
    direct_link: Optional[str] = None
    file_size: Optional[str] = None
    error: Optional[str] = None

download_tasks: dict = {}

def update_progress(d):
    if d.get("status") == "downloading":
        # Hook receives no task id in this simple MVP.
        # The download endpoint updates its task after extraction.
        pass

def get_yt_dlp_opts(quality: str):
    opts = {
        "format": quality,
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [update_progress],
        "nooverwrites": True,
        # Datacenter IPs (Render, AWS, etc.) get YouTube's bot-check far more
        # than residential/mobile IPs. These clients skip the web sign-in
        # wall in most cases and don't require a JS runtime.
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "tv"],
            }
        },
    }

    # Optional: point this at a cookies.txt file for cases where the
    # player_client fallback above still gets blocked. Never commit the
    # cookies file itself to git -- upload it as a Render "Secret File"
    # (Render mounts it on disk) and set YTDLP_COOKIES_PATH to that path,
    # e.g. /etc/secrets/cookies.txt
    cookie_path = os.environ.get("YTDLP_COOKIES_PATH")
    if cookie_path and os.path.exists(cookie_path):
        opts["cookiefile"] = cookie_path

    return opts

@app.post("/download")
async def download_media(req: DownloadRequest):
    task_key = f"{req.url}|{req.quality}"
    download_tasks[task_key] = DownloadStatus(status="downloading", progress=0)

    try:
        os.makedirs("downloads", exist_ok=True)
        with yt_dlp.YoutubeDL(get_yt_dlp_opts(req.quality)) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename) if os.path.exists(filename) else None
        download_tasks[task_key] = DownloadStatus(
            status="ready",
            progress=100.0,
            direct_link=filename,
            file_size=str(size) if size is not None else None,
        )
    except Exception as e:
        download_tasks[task_key] = DownloadStatus(
            status="error", error=str(e)
        )

    return download_tasks[task_key]

@app.get("/health")
async def health():
    return {"status": "ok", "tasks": len(download_tasks)}
