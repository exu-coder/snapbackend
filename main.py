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
        pass  # no real progress shown in your current setup

def get_yt_dlp_opts(quality: str, cookies_from_browser: str | None = None):
    opts = {
        "format": quality,
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [update_progress],
        "nooverwrites": True,
    }
    if cookies_from_browser:
        opts["cookies_from_browser"] = cookies_from_browser
    return opts

@app.post("/download")
async def download_media(req: DownloadRequest):
    task_key = f"{req.url}|{req.quality}"
    download_tasks[task_key] = DownloadStatus(status="downloading", progress=0)

    try:
        os.makedirs("downloads", exist_ok=True)
        
        # 🔥 FIXED: cookies support
        ydl_opts = get_yt_dlp_opts(req.quality, cookies_from_browser="firefox")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
