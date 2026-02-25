"""
PyFlow – Download Manager
─────────────────────────
• Async queue with up to 3 simultaneous downloads
• yt-dlp Python library is primary; falls back to yt-dlp binary if needed
• ffmpeg discovered automatically (PATH → script directory)
• Background yt-dlp self-update on startup
• Full error handling – server never hangs
"""

import asyncio
import os
import subprocess
import sys
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from utils import (
    get_download_directory,
    find_ffmpeg,
    find_ytdlp_binary,
    format_size,
    format_time,
)

logger = logging.getLogger(__name__)

# ─── Try importing yt-dlp library ────────────────────────────────────────────
try:
    import yt_dlp
    _YTDLP_VERSION = yt_dlp.version.__version__
    logger.info(f"yt-dlp library loaded  v{_YTDLP_VERSION}")
except ImportError:
    yt_dlp = None
    _YTDLP_VERSION = "not installed"
    logger.warning("yt-dlp library not found – will attempt binary fallback")


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class DownloadTask:
    """Represents a single download item in the queue."""
    task_id: str
    url: str
    title: str
    download_type: str          # "video" | "audio"
    quality: str
    format_type: str
    is_playlist: bool
    status: str = "Queued"      # Queued | Downloading | Processing | Completed | Failed | Cancelled
    progress: float = 0.0
    speed: str = "–"
    eta: str = "–"
    file_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


# ─── Download Manager ─────────────────────────────────────────────────────────

class DownloadManager:
    """
    Manages the download queue.

    Design decisions
    ----------------
    * max_concurrent = 3  (requirement F-E)
    * yt-dlp library is preferred; binary fallback if library unavailable
    * ffmpeg path injected into yt-dlp options so post-processing always works
    * Background task auto-updates yt-dlp on startup
    * Never blocks the event loop – all I/O runs in an executor
    """

    MAX_CONCURRENT = 3

    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir: Path = download_dir or get_download_directory()
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Tool paths
        self._ffmpeg_path, ffmpeg_msg = find_ffmpeg()
        self._ytdlp_binary, ytdlp_msg = find_ytdlp_binary()
        logger.info(ffmpeg_msg)
        logger.info(ytdlp_msg)

        # yt-dlp version string exposed to UI
        self.ytdlp_version: str = _YTDLP_VERSION

        # Queue and concurrency
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, DownloadTask] = {}
        self.completed_tasks: List[DownloadTask] = []
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self._shutdown = False

        logger.info(f"DownloadManager ready  dir={self.download_dir}  "
                    f"max_concurrent={self.MAX_CONCURRENT}")

    # ─── Public API ──────────────────────────────────────────────────────────

    async def add_download(
        self,
        url: str,
        download_type: str,
        is_playlist: bool,
        quality: str,
        format_type: str,
        title: str,
    ) -> str:
        """Enqueue a new download and return its task_id."""
        # Strip playlist params for single-video requests
        if not is_playlist:
            url = self._strip_playlist_params(url)

        task_id = str(uuid.uuid4())[:8]
        task = DownloadTask(
            task_id=task_id,
            url=url,
            title=title,
            download_type=download_type,
            quality=quality,
            format_type=format_type,
            is_playlist=is_playlist,
        )
        self.active_tasks[task_id] = task
        await self.queue.put(task)
        logger.info(f"Queued  [{task_id}]  {title}")
        return task_id

    async def process_queue(self):
        """Launch worker coroutines and run until shutdown."""
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.MAX_CONCURRENT)
        ]
        # Also start background updater
        updater = asyncio.create_task(self._background_update_ytdlp())
        await asyncio.gather(*workers, updater, return_exceptions=True)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task that is still queued or active."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            task.status = "Cancelled"
            logger.info(f"Cancelled [{task_id}]")
            return True
        return False

    def shutdown(self):
        """Signal all workers to stop after finishing current downloads."""
        self._shutdown = True
        logger.info("DownloadManager shutdown requested")

    # ─── Workers ─────────────────────────────────────────────────────────────

    async def _worker(self, worker_id: int):
        """Pull tasks from the queue and process them one at a time."""
        logger.debug(f"Worker-{worker_id} started")
        while not self._shutdown:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # Skip tasks that were cancelled while waiting in queue
            if task.status == "Cancelled":
                self.queue.task_done()
                continue

            async with self.semaphore:
                await self._process_task(task)

            self.queue.task_done()

        logger.debug(f"Worker-{worker_id} stopped")
        
     # ─── Task Processing ─────────────────────────────────────────────────────
    async def _process_task(self, task: DownloadTask):
        """Download a single task – tries library first, then binary."""
        try:
            task.status = "Downloading"
            logger.info(f"Starting [{task.task_id}] {task.title}")

            if yt_dlp is not None:
                await self._download_via_library(task)
            elif self._ytdlp_binary:
                await self._download_via_binary(task)
            else:
                raise RuntimeError(
                    "Neither yt-dlp library nor binary is available. "
                    "Install yt-dlp: pip install yt-dlp"
                )

            task.status = "Completed"
            task.progress = 100.0
            logger.info(f"Completed [{task.task_id}] {task.title}")

        except asyncio.CancelledError:
            task.status = "Cancelled"
        except Exception as exc:
            task.status = "Failed"
            task.error = str(exc)
            logger.error(f"Failed [{task.task_id}] {task.title}: {exc}", exc_info=True)
        finally:
            # Move to completed list regardless of outcome
            self.completed_tasks.append(task)
            self.active_tasks.pop(task.task_id, None)

    # ─── Library Download ─────────────────────────────────────────────────────

    async def _download_via_library(self, task: DownloadTask):
        """Use the yt-dlp Python library (preferred path)."""
        opts = self._build_ydl_options(task)

        def _progress_hook(d):
            if d["status"] == "downloading":
                if "downloaded_bytes" in d and "total_bytes" in d and d["total_bytes"]:
                    task.progress = d["downloaded_bytes"] / d["total_bytes"] * 100
                elif "_percent_str" in d:
                    try:
                        task.progress = float(d["_percent_str"].strip().rstrip("%"))
                    except ValueError:
                        pass
                task.speed = d.get("_speed_str", "–")
                task.eta   = d.get("_eta_str",   "–")
            elif d["status"] == "finished":
                task.status   = "Processing"
                task.progress = 100.0
                task.file_path = d.get("filename")

        opts["progress_hooks"] = [_progress_hook]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_ydl, task.url, opts)

    def _run_ydl(self, url: str, opts: dict):
        """Blocking yt-dlp call – runs in thread-pool executor."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
            
            
    # ─── Binary Fallback ──────────────────────────────────────────────────────
    async def _download_via_binary(self, task: DownloadTask):
        """
        Fallback: run the yt-dlp standalone binary via subprocess.
        Progress is not as granular here, but it works.
        """
        logger.info(f"Using yt-dlp binary for [{task.task_id}]")
        cmd = self._build_binary_command(task)
        loop = asyncio.get_event_loop()

        def _run():
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.download_dir),
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr[:500] or "yt-dlp binary failed")

        await loop.run_in_executor(None, _run)
        task.progress = 100.0
        
    # ─── yt-dlp Binary Command Builder ────────────────────────────────────────
    def _build_binary_command(self, task: DownloadTask) -> list:
        """Build the CLI argument list for the yt-dlp binary."""
        cmd = [self._ytdlp_binary]

        if task.download_type == "audio":
            cmd += ["-x", "--audio-format", task.format_type,
                    "--audio-quality", task.quality,
                    "--add-metadata"]
        else:
            height = task.quality.replace("p", "")
            if height == "best":
                cmd += ["-f", "bestvideo+bestaudio/best"]
            elif height in ["2160", "1440"]:
                cmd += ["-f", f"bestvideo[height<={height}][format={task.format_type}]+bestaudio/best"]
                cmd += ["--merge-output-format", task.format_type]
                cmd += ["--add-metadata"]
                
            else:
                cmd += ["-f", f"bestvideo[height<={height}][format={task.format_type}]+bestaudio/best"]
                cmd += ["--merge-output-format", task.format_type]
                

        if self._ffmpeg_path:
            cmd += ["--ffmpeg-location", str(Path(self._ffmpeg_path).parent)]

        cmd += [
        
            "-o", "%(title)s.%(ext)s",
            task.url,
        ]
        return cmd

    # ─── yt-dlp Options Builder ───────────────────────────────────────────────

    def _build_ydl_options(self, task: DownloadTask) -> dict:
        """Build a complete yt-dlp option dict for the library."""
        out_tmpl = str(self.download_dir / "%(title)s.%(ext)s")

        opts: dict = {
            "outtmpl":       out_tmpl,
            "quiet":         True,
            "no_warnings":   True,
            "noprogress":    True,
            "extract_flat":  False,
            "writethumbnail": False,
            "logger":        None,
        }

        # Inject ffmpeg location so post-processing always works
        if self._ffmpeg_path:
            opts["ffmpeg_location"] = str(Path(self._ffmpeg_path).parent)

        if task.download_type == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio",
                 "preferredcodec": task.format_type,
                 "preferredquality": task.quality},
                {"key": "FFmpegMetadata"},
            ]
        else:
            if task.quality == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                h = task.quality.replace("p", "")
                fmt = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            opts["format"] = fmt
            opts["merge_output_format"] = task.format_type

        opts["noplaylist"] = not task.is_playlist
        return opts

    # ─── Background yt-dlp Updater ────────────────────────────────────────────

    async def _background_update_ytdlp(self):
        """
        On startup, silently update both the yt-dlp library and binary
        (if present).  This keeps the downloader working even when
        YouTube changes its page structure.
        """
        await asyncio.sleep(5)   # Let server fully start first
        logger.info("Background yt-dlp update started")

        loop = asyncio.get_event_loop()

        # Update Python library
        def _update_library():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp",
                     "--quiet", "--disable-pip-version-check"],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    # Re-read version
                    import importlib
                    import yt_dlp as _ydl
                    importlib.reload(_ydl.version)
                    self.ytdlp_version = _ydl.version.__version__
                    logger.info(f"yt-dlp library updated  → v{self.ytdlp_version}")
                else:
                    logger.warning(f"yt-dlp library update failed: {result.stderr[:200]}")
            except Exception as e:
                logger.warning(f"yt-dlp library update error: {e}")

        await loop.run_in_executor(None, _update_library)

        # Update binary if it exists and supports self-update
        if self._ytdlp_binary:
            def _update_binary():
                try:
                    result = subprocess.run(
                        [self._ytdlp_binary, "-U"],
                        capture_output=True, text=True, timeout=60,
                    )
                    logger.info(f"yt-dlp binary update: {result.stdout.strip()[:100]}")
                except Exception as e:
                    logger.warning(f"yt-dlp binary update error: {e}")

            await loop.run_in_executor(None, _update_binary)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_playlist_params(url: str) -> str:
        """Remove 'list' and 'index' query params for single-video URLs."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        params.pop("list", None)
        params.pop("index", None)
        clean_query = urlencode(params, doseq=True)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, clean_query, parsed.fragment
        ))
