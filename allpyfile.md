"""
Utility functions for PyFlow downloader
utils.py contains helper functions for managing download directories, formatting sizes and times, sanitizing filenames, checking dependencies, and printing status information. These functions are used throughout the application to ensure consistent behavior and improve user experience.
"""

import os
import platform
from pathlib import Path


def get_download_directory() -> Path:
    """
    Get the appropriate download directory for the current OS
    
    Returns:
        Path object pointing to the download directory
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows: C:\Users\Username\Downloads\PyFlow
        downloads = Path.home() / "Downloads" / "PyFlow"
    elif system == "Darwin":  # macOS
        # macOS: /Users/Username/Downloads/PyFlow
        downloads = Path.home() / "Downloads" / "PyFlow"
    else:  # Linux and others
        # Linux: /home/username/Downloads/PyFlow or ~/Downloads/PyFlow
        downloads = Path.home() / "Downloads" / "PyFlow"
    
    # Create directory if it doesn't exist
    downloads.mkdir(parents=True, exist_ok=True)
    
    return downloads


def format_size(bytes_size: int) -> str:
    """
    Format bytes into human-readable size
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def format_time(seconds: int) -> str:
    """
    Format seconds into human-readable time
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted string (e.g., "1h 23m")
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from filename
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for all OS
    """
    # Characters that are invalid in filenames
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def get_ffmpeg_path() -> str:
    """
    Get the path to ffmpeg executable
    
    Returns:
        Path to ffmpeg or 'ffmpeg' if in PATH
    """
    # Check if ffmpeg is in PATH
    import shutil
    
    ffmpeg = shutil.which('ffmpeg')
    
    if ffmpeg:
        return ffmpeg
    
    # Common ffmpeg locations
    common_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
        'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    # Default to 'ffmpeg' and hope it's in PATH
    return 'ffmpeg'


def check_dependencies() -> dict:
    """
    Check if required dependencies are installed
    
    Returns:
        Dictionary with dependency status
    """
    status = {}
    
    # Check yt-dlp
    try:
        import yt_dlp
        status['yt-dlp'] = True
    except ImportError:
        status['yt-dlp'] = False
    
    # Check ffmpeg
    import shutil
    status['ffmpeg'] = shutil.which('ffmpeg') is not None
    
    # Check FastAPI
    try:
        import fastapi
        status['fastapi'] = True
    except ImportError:
        status['fastapi'] = False
    
    # Check uvicorn
    try:
        import uvicorn
        status['uvicorn'] = True
    except ImportError:
        status['uvicorn'] = False
    
    # Check rich
    try:
        import rich
        status['rich'] = True
    except ImportError:
        status['rich'] = False
    
    return status


def print_dependency_status():
    """Print status of all dependencies"""
    print("\n📦 Checking Dependencies...")
    print("=" * 50)
    
    deps = check_dependencies()
    
    for dep, installed in deps.items():
        status = "✅ Installed" if installed else "❌ Not Found"
        print(f"{dep:15} {status}")
    
    if not all(deps.values()):
        print("\n⚠️  Some dependencies are missing!")
        print("\nInstall missing dependencies:")
        
        if not deps.get('yt-dlp'):
            print("  pip install yt-dlp")
        if not deps.get('fastapi'):
            print("  pip install fastapi")
        if not deps.get('uvicorn'):
            print("  pip install uvicorn")
        if not deps.get('rich'):
            print("  pip install rich")
        if not deps.get('ffmpeg'):
            print("  Install ffmpeg from: https://ffmpeg.org/download.html")
    
    print("=" * 50)
    print()







"""
UI Manager - Rich terminal interface with live updating table
ui.py contains the UIManager class which manages the terminal interface using the Rich library. It creates a dynamic layout with a header showing status information, a table for active downloads, and a section for recently completed downloads. The UI updates in real-time as the download manager processes tasks, providing users with an engaging and informative experience while using the PyFlow downloader CLI.
"""

import asyncio
from rich.console import Console
from rich.table import Table 
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.text import Text
import logging
from rich.live import Live
from rich.console import Console


logger = logging.getLogger(__name__)


class UIManager:
    """Manages the terminal UI using Rich library"""
    
    def __init__(self, download_manager, update_interval: float = 0.25):
        self.download_manager = download_manager
        self.update_interval = update_interval
        self.console = Console()
        self._shutdown = False
    
    def _create_header(self) -> Panel:
        """Create header panel with status info"""
        queue_size = self.download_manager.queue.qsize()
        active_count = len(self.download_manager.active_tasks)
        completed_count = len(self.download_manager.completed_tasks)
        
        header_text = Text()
        header_text.append("PyFlow ", style="bold cyan")
        header_text.append("- YouTube Downloader CLI\n", style="bold white")
        header_text.append(f"Queue: ", style="dim")
        header_text.append(f"{queue_size}", style="yellow")
        header_text.append(f" | Active: ", style="dim")
        header_text.append(f"{active_count}", style="green")
        header_text.append(f" | Completed: ", style="dim")
        header_text.append(f"{completed_count}", style="blue")
        
        return Panel(
            header_text,
            title="[bold cyan]Status[/bold cyan]",
            border_style="cyan"
        )
    
    def _create_downloads_table(self) -> Table:
        """Create table showing active downloads"""
        table = Table(
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
            title="[bold]Active Downloads[/bold]",
            title_style="bold cyan",
            expand=True
        )
        
        table.add_column("ID", style="cyan", width=8, no_wrap=True)
        table.add_column("Title", style="white", width=35, no_wrap=True, overflow="ellipsis")
        table.add_column("Type", style="yellow", width=8, no_wrap=True)
        table.add_column("Status", style="green", width=15, no_wrap=True)
        table.add_column("Progress", width=31, no_wrap=True)
        table.add_column("Speed", style="blue", width=15, no_wrap=True)
        table.add_column("ETA", style="magenta", width=8, no_wrap=True)
            
        # Add active tasks
        for task in self.download_manager.active_tasks.values():
            # Truncate title
            title = task.title[:27] + "..." if len(task.title) > 30 else task.title
            
            # Status color
            status_style = {
                "Queued": "yellow",
                "Downloading": "cyan",
                "Processing": "magenta",
                "Completed": "green",
                "Failed": "red",
                "Cancelled": "dim"
            }.get(task.status, "white")
            
            # Progress bar
            progress_text = f"[{'=' * int(task.progress / 5)}{' ' * (20 - int(task.progress / 5))}] {task.progress:.1f}%"
            
            table.add_row(
                task.task_id,
                title,
                task.download_type.upper(),
                f"[{status_style}]{task.status}[/{status_style}]",
                progress_text,
                task.speed,
                task.eta
            )
        
        # Show message if no active downloads
        if not self.download_manager.active_tasks:
            table.add_row(
                "[dim]--[/dim]",
                "[dim]No active downloads[/dim]",
                "[dim]--[/dim]",
                "[dim]--[/dim]",
                "[dim]--[/dim]",
                "[dim]--[/dim]",
                "[dim]--[/dim]"
            )
        
        return table
    
    def _create_completed_table(self) -> Table:
        """Create table showing recently completed downloads"""
        table = Table(
            show_header=True,
            header_style="bold green",
            border_style="dim",
            # padding=(0, 1),
            collapse_padding="True",
            title="[bold]Recently Completed[/bold]",
            title_style="bold green",
            expand=True
        )
        
        table.add_column("ID", style="cyan", width=8, no_wrap=True)
        table.add_column("Title", style="white", width=50, no_wrap=True, overflow="ellipsis")
        table.add_column("Type", style="yellow", width=10, no_wrap=True)
        table.add_column("Status", style="green", width=15, no_wrap=True)
        
        # Show last 5 completed
        recent = self.download_manager.completed_tasks[-5:]
        
        for task in reversed(recent):
            title = task.title[:50] + "..." if len(task.title) > 50 else task.title
            
            status_style = "green" if task.status == "Completed" else "red"
            
            table.add_row(
                task.task_id,
                title,
                task.download_type.upper(),
                f"[{status_style}]✓ {task.status}[/{status_style}]"
            )
        
        if not recent:
            table.add_row(
                "[dim]--[/dim]",
                "[dim]No completed downloads yet[/dim]",
                "[dim]--[/dim]",
                "[dim]--[/dim]"
            )
        
        return table
    
    def _create_layout(self) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="downloads", ratio=1),
            Layout(name="completed", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["header"].update(self._create_header())
        layout["downloads"].update(self._create_downloads_table())
        layout["completed"].update(self._create_completed_table())
        
        footer_text = Text()
        footer_text.append("📁 Downloads: ", style="dim")
        footer_text.append(str(self.download_manager.download_dir), style="cyan")
        footer_text.append(" | Press Ctrl+C to exit", style="dim")
        
        layout["footer"].update(Panel(footer_text, border_style="dim"))
        
        return layout
    
 
    async def run(self):
        """Run the UI update loop"""
        with Live(
            self._create_layout(),
            console=self.console,
            refresh_per_second=4,
            screen=True
        ) as live:
            while not self._shutdown:
                try:
                    await asyncio.sleep(self.update_interval)
                    live.update(self._create_layout())
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"UI error: {e}")
    
    def shutdown(self):
        """Shutdown the UI manager"""
        self._shutdown = True






"""
FastAPI server for handling download requests from Chrome Extension
server.py contains the FastAPI application that serves as the backend for the PyFlow downloader. It defines endpoints for adding new download tasks, checking server health, retrieving queue status, and cancelling downloads. The server processes incoming requests from the Chrome Extension, validates them, and interacts with the DownloadManager to manage the download workflow effectively. The server also includes CORS middleware to allow cross-origin requests from the extension, ensuring seamless communication between the frontend and backend components of the application.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional
import logging

# Configure logging

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DownloadRequest(BaseModel):
    """Schema for download requests from extension"""
    url: str
    download_type: Literal["video", "audio"]
    is_playlist: bool = False
    quality: str = "1080p"
    format: str = "mp4"
    title: Optional[str] = "Untitled"


class DownloadResponse(BaseModel):
    """Response after queuing a download"""
    status: str
    message: str
    task_id: str


def create_app(download_manager):
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="PyFlow Download Server",
        description="Local server for YouTube downloads via yt-dlp",
        version="1.0.0"
    )
    
    # CORS middleware to allow requests from Chrome Extension
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify extension origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for extension to verify server is running"""
        return {
            "status": "online",
            "queue_size": download_manager.queue.qsize(),
            "active_downloads": len(download_manager.active_tasks)
        }
    
    @app.post("/add-download", response_model=DownloadResponse)
    async def add_download(request: DownloadRequest):
        """
        Add a new download task to the queue
        
        Args:
            request: DownloadRequest with URL, type, quality, format, etc.
            
        Returns:
            DownloadResponse with task ID and status
        """
        try:
            logger.info(f"Received download request: {request.title}")
            logger.info(f"URL: {request.url}")
            logger.info(f"Type: {request.download_type}, Quality: {request.quality}, Format: {request.format}")
            logger.info(f"Playlist: {request.is_playlist}")
            
            # Validate URL
            if not ("youtube.com" in request.url or "youtu.be" in request.url):
                raise HTTPException(
                    status_code=400,
                    detail="Only YouTube URLs are supported"
                )
            
            # Add to download queue
            task_id = await download_manager.add_download(
                url=request.url,
                download_type=request.download_type,
                is_playlist=request.is_playlist,
                quality=request.quality,
                format_type=request.format,
                title=request.title
            )
            
            return DownloadResponse(
                status="success",
                message=f"Download queued successfully",
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Error adding download: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error queuing download: {str(e)}"
            )
    
    @app.get("/queue")
    async def get_queue_status():
        """Get current queue status and active downloads"""
        return {
            "queue_size": download_manager.queue.qsize(),
            "active_tasks": [
                {
                    "id": task.task_id,
                    "title": task.title,
                    "status": task.status,
                    "progress": task.progress
                }
                for task in download_manager.active_tasks.values()
            ]
        }
    
    @app.delete("/cancel/{task_id}")
    async def cancel_download(task_id: str):
        """Cancel a specific download task"""
        try:
            success = download_manager.cancel_task(task_id)
            if success:
                return {"status": "success", "message": f"Task {task_id} cancelled"}
            else:
                raise HTTPException(status_code=404, detail="Task not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app










#!/usr/bin/env python3
"""
PyFlow - YouTube Downloader CLI
Main entry point that orchestrates the server, download manager, and UI
main.py initializes the DownloadManager and UIManager, starts the FastAPI server in a background thread, and runs the main event loop to process downloads and update the UI. It also handles graceful shutdown on keyboard interrupt, ensuring that all tasks are properly cleaned up before exiting the application.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import create_app
from download_manager import DownloadManager
from ui import UIManager
import uvicorn
from threading import Thread

# === সমাধান ২: লগিং কনফিগারেশন পরিবর্তন ===
# কনসোলে প্রিন্ট না করে ফাইলে লগ সেভ হবে
logging.basicConfig(
    filename='pyflow.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True # আগের কনফিগারেশন ওভাররাইট করার জন্য
)
# ========================================
# logging.basicConfig(level=logging.INFO)

async def main():
    """Main async entry point"""
    print("🚀 PyFlow - YouTube Downloader CLI")
    print("=" * 50)
    
    # Initialize managers
    download_manager = DownloadManager()
    ui_manager = UIManager(download_manager)
    
    # Create FastAPI app
    app = create_app(download_manager)
    
    # Start FastAPI server in background thread
    def run_server():
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="critical",
            access_log=False    
        )
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("✅ Server started on http://localhost:8000")
    print("📦 Download directory:", download_manager.download_dir)
    print("\n💡 Open your browser and use the PyFlow extension!")
    print("=" * 50)
    print()
    
    # Start download worker
    download_task = asyncio.create_task(download_manager.process_queue())
    
    # Start UI update loop
    ui_task = asyncio.create_task(ui_manager.run())
    
    try:
        # Keep running until interrupted
        await asyncio.gather(download_task, ui_task)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down PyFlow...")
        download_manager.shutdown()
        ui_manager.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)










 

/* PyFlow Download Button  content.css */
.pyflow-download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 18px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  font-family: "Roboto", "Arial", sans-serif;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-right: 8px;
}

.pyflow-download-btn:hover {
  background: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.5);
  transform: translateY(-1px);
}

.pyflow-download-btn:active {
  transform: translateY(0);
}

.pyflow-download-btn svg {
  width: 20px;
  height: 20px;
}

/* Modal Overlay */
.pyflow-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 10000;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.pyflow-modal.show {
  opacity: 1;
  pointer-events: all;
}

.pyflow-modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
}

/* Modal Content */
.pyflow-modal-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  transition: transform 0.3s ease;
}

.pyflow-modal.show .pyflow-modal-content {
  transform: translate(-50%, -50%) scale(1);
}

/* Modal Header */
.pyflow-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.pyflow-modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.pyflow-close-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.pyflow-close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* Modal Body */
.pyflow-modal-body {
  padding: 24px;
  color: #fff;
}

.pyflow-modal-body p {
  margin: 0 0 20px 0;
  color: #ccc;
  font-size: 14px;
  line-height: 1.6;
}

/* Instructions */
.pyflow-instructions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.pyflow-instruction-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.pyflow-step {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border-radius: 50%;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.pyflow-instruction-item span:last-child {
  font-size: 14px;
  color: #ddd;
}

/* Open Popup Button */
.pyflow-open-popup-btn {
  width: 100%;
  padding: 14px 24px;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
}

.pyflow-open-popup-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
}

.pyflow-open-popup-btn:active {
  transform: translateY(0);
}










// Content script for injecting download button into YouTube pages
// content.js


let downloadButton = null;
let isInjected = false;

// Wait for YouTube to load
function init() {
  // YouTube is a SPA, so we need to observe navigation
  observeUrlChanges();
  injectButton();
}

// Detect URL changes in YouTube SPA
function observeUrlChanges() {
  let lastUrl = location.href;
  
  const observer = new MutationObserver(() => {
    const currentUrl = location.href;
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl;
      isInjected = false;
      setTimeout(injectButton, 1000); // Wait for YouTube UI to render
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Inject download button into YouTube's action bar
function injectButton() {
  if (isInjected) return;
  
  // Check if we're on a video page
  const urlParams = new URLSearchParams(window.location.search);
  if (!urlParams.has('v')) {
    return;
  }

  // Try to find YouTube's action menu (below video, next to like/share buttons)
  const actionBar = findActionBar();
  
  if (!actionBar) {
    // Retry after a delay
    setTimeout(injectButton, 500);
    return;
  }

  // Create download button
  downloadButton = createDownloadButton();
  
  // Insert into action bar
  actionBar.insertBefore(downloadButton, actionBar.firstChild);
  isInjected = true;
  
  console.log('PyFlow: Download button injected');
}

// Find YouTube's action bar (multiple selectors for compatibility)
function findActionBar() {
  const selectors = [
    '#top-level-buttons-computed', // Primary action bar
    '#top-level-buttons',
    'ytd-menu-renderer.ytd-video-primary-info-renderer',
    '#menu-container #top-level-buttons'
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element;
    }
  }

  return null;
}

// Create the download button element
function createDownloadButton() {
  const button = document.createElement('button');
  button.className = 'pyflow-download-btn';
  button.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
      <polyline points="7 10 12 15 17 10"></polyline>
      <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
    <span>PyFlow</span>
  `;

  // Open extension popup when clicked
  button.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Show modal overlay
    showDownloadModal();
  });

  return button;
}

// Show custom modal overlay (mimics popup UI)
function showDownloadModal() {
  // Remove existing modal if any
  const existingModal = document.getElementById('pyflow-modal');
  if (existingModal) {
    existingModal.remove();
  }

  // Create modal
  const modal = document.createElement('div');
  modal.id = 'pyflow-modal';
  modal.className = 'pyflow-modal';
  modal.innerHTML = `
    <div class="pyflow-modal-overlay" id="pyflowOverlay"></div>
    <div class="pyflow-modal-content">
      <div class="pyflow-modal-header">
        <h2>PyFlow Download</h2>
        <button class="pyflow-close-btn" id="pyflowCloseBtn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="pyflow-modal-body">
        <p>Click the PyFlow extension icon in your browser toolbar to configure and start the download.</p>
        <div class="pyflow-instructions">
          <div class="pyflow-instruction-item">
            <span class="pyflow-step">1</span>
            <span>Click the PyFlow icon in the extensions area</span>
          </div>
          <div class="pyflow-instruction-item">
            <span class="pyflow-step">2</span>
            <span>Choose quality, format, and download type</span>
          </div>
          <div class="pyflow-instruction-item">
            <span class="pyflow-step">3</span>
            <span>Click Download to send to your local server</span>
          </div>
        </div>
        <button class="pyflow-open-popup-btn" id="pyflowOpenPopup">Open Extension Popup</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Add event listeners
  document.getElementById('pyflowOverlay').addEventListener('click', closeModal);
  document.getElementById('pyflowCloseBtn').addEventListener('click', closeModal);
  document.getElementById('pyflowOpenPopup').addEventListener('click', () => {
    // Instruct user to click extension icon (we can't programmatically open it)
    alert('Please click the PyFlow extension icon in your browser toolbar (usually in the top-right corner)');
  });

  // Animate in
  requestAnimationFrame(() => {
    modal.classList.add('show');
  });
}

function closeModal() {
  const modal = document.getElementById('pyflow-modal');
  if (modal) {
    modal.classList.remove('show');
    setTimeout(() => modal.remove(), 300);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}



// manifest.json


{
  "manifest_version": 3,
  "name": "PyFlow - YouTube Downloader Bridge",
  "version": "1.0.0",
  "description": "Modern YouTube downloader bridge to local Python CLI powered by yt-dlp",
  "permissions": [
    "activeTab",
    "scripting",
    "storage"
  ],
  "host_permissions": [
    "http://localhost:8000/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "content_scripts": [
    {
      "matches": ["*://*.youtube.com/*"],
      "js": ["content.js"],
      "css": ["content.css"],
      "run_at": "document_idle"
    }
  ],
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}




// popup.css

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f0f0f;
  color: #ffffff;
  width: 360px;
  min-height: 400px;
}

.container {
  padding: 20px;
  background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
}

/* Header */


.header {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between; /* নাম বামে এবং বৃত্ত ডানে রাখার জন্য */
}
.header h1 {
  font-size: 18px;
  margin: 0;
}
.status-wrapper {
  position: relative;
  display: inline-block;
  cursor: pointer;
}


.status-dot {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #ef4444; /* ডিফল্ট লাল */
  display: block;
  transition: transform 0.2s ease;
}
.status-wrapper:hover .status-dot {
  transform: scale(1.2);
}
.status-tooltip {
  visibility: hidden;
  width: 80px;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 6px;
  padding: 5px;
  position: absolute;
  z-index: 1;
  bottom: 125%; /* বৃত্তের উপরে দেখাবে */
  right: 0;
  margin-left: -40px;
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 10px;
  white-space: nowrap;
}
.status-wrapper:hover .status-tooltip {
  visibility: visible;
  opacity: 1;
}
.status-tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  right: 5px;
  border-width: 5px;
  border-style: solid;
  border-color: #333 transparent transparent transparent;
}
.status-dot.online {
  background: #22c55e;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

h1 {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Video Preview */
.video-preview {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 12px;
  align-items: center;
}

.thumbnail {
  width: 80px;
  height: 60px;
  border-radius: 8px;
  object-fit: cover;
  background: #1a1a1a;
}

.video-info {
  flex: 1;
  overflow: hidden;
}

.video-info h3 {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

/* Error Message */
.error-message {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ef4444;
  font-size: 14px;
}

/* Controls */
.controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Playlist Toggle */
.playlist-toggle {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toggle-label {
  font-size: 13px;
  color: #888;
  font-weight: 500;
}

.segmented-control {
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 4px;
  position: relative;
}

.segmented-control input[type="radio"] {
  display: none;
}

.segmented-control label {
  padding: 8px 16px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s ease;
  color: #888;
  z-index: 1;
}

.segmented-control input[type="radio"]:checked + label {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  color: #fff;
}

/* Form Groups */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 13px;
  color: #888;
  font-weight: 500;
}

.select-input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 10px 14px;
  color: #fff;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.select-input:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
}

.select-input:focus {
  border-color: #06b6d4;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}

.select-input option {
  background: #1a1a1a;
  color: #fff;
}

/* Download Button */
.download-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: none;
  border-radius: 12px;
  padding: 14px 24px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
}

.download-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
}

.download-btn:active {
  transform: translateY(0);
}

.download-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Toast Notification */
.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(10px);
  color: #fff;
  padding: 12px 20px;
  border-radius: 10px;
  font-size: 13px;
  opacity: 0;
  transition: all 0.3s ease;
  z-index: 1000;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.toast.show {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}


// popup.html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PyFlow - YT-DLP Bridge</title>
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <div class="container">
    <!-- Header with Status -->
    <div class="header">
      <div class="header-main">
        <h1>PyFlow-DLP</h1>
        <div class="status-wrapper">
          <span class="status-dot" id="statusDot"></span>
          <span class="status-tooltip" id="statusText">Checking...</span>
        </div>
      </div>
    </div>
    <!-- Video Preview Card -->
    <div class="video-preview" id="videoPreview" style="display: none;">
      <img id="videoThumbnail" alt="Video Thumbnail" class="thumbnail">
      <div class="video-info">
        <h3 id="videoTitle">Loading...</h3>
      </div>
    </div>

    <!-- Error Message -->
    <div class="error-message" id="errorMessage" style="display: none;">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM11 15H9V13H11V15ZM11 11H9V5H11V11Z" fill="#ef4444"/>
      </svg>
      <span id="errorText">No video detected</span>
    </div>

    <!-- Download Controls -->
    <div class="controls" id="controls">
      <!-- Playlist Toggle (Shows only if playlist detected) -->
      <div class="playlist-toggle" id="playlistToggle" style="display: none;">
        <label class="toggle-label">Download Mode</label>
        <div class="segmented-control">
          <input type="radio" name="playlistMode" id="singleVideo" value="single" checked>
          <label for="singleVideo">Single Video</label>
          <input type="radio" name="playlistMode" id="wholePlaylist" value="playlist">
          <label for="wholePlaylist">Whole Playlist</label>
        </div>
      </div>

      <!-- Type Selector -->
      <div class="form-group">
        <label for="downloadType">Type</label>
        <select id="downloadType" class="select-input">
          <option value="video">Video</option>
          <option value="audio">Audio Only</option>
        </select>
      </div>

      <!-- Quality Selector -->
      <div class="form-group" id="qualityGroup">
        <label for="quality">Quality</label>
        <select id="quality" class="select-input">
          <option value="2160p">4K (2160p)</option>
          <option value="1080p" selected>1080p</option>
          <option value="720p">720p</option>
          <option value="480p">480p</option>
          <option value="360p">360p</option>
          <option value="best">Best Available</option>
        </select>
      </div>

      <!-- Format Selector -->
      <div class="form-group">
        <label for="format">Format</label>
        <select id="format" class="select-input">
          <option value="mp4" selected>MP4</option>
          <option value="mkv">MKV</option>
          <option value="webm">WebM</option>
        </select>
      </div>

      <!-- Download Button -->
      <button class="download-btn" id="downloadBtn">
        <span id="btnText">Download</span>
        <svg id="btnSpinner" class="spinner" style="display: none;" width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="50.265" stroke-dashoffset="25"/>
        </svg>
        <svg id="btnCheck" class="checkmark" style="display: none;" width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M16.6 5L7.5 14.1L3.4 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast">
      <span id="toastText"></span>
    </div>
  </div>

  <script src="popup.js"></script>
</body>
</html>



//popup.js

// Constants
const SERVER_URL = 'http://localhost:8000';
const SERVER_CHECK_ENDPOINT = `${SERVER_URL}/health`;
const DOWNLOAD_ENDPOINT = `${SERVER_URL}/add-download`;

// DOM Elements
let statusDot, statusText, videoPreview, videoThumbnail, videoTitle;
let errorMessage, errorText, controls, playlistToggle;
let downloadType, quality, format, downloadBtn, btnText, btnSpinner, btnCheck;
let toast, toastText;

// State
let currentUrl = '';
let currentTitle = '';
let isPlaylist = false;
let serverOnline = false;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  initElements();
  await checkServerStatus();
  await detectVideo();
  setupEventListeners();
});

function initElements() {
  statusDot = document.getElementById('statusDot');
  statusText = document.getElementById('statusText');
  videoPreview = document.getElementById('videoPreview');
  videoThumbnail = document.getElementById('videoThumbnail');
  videoTitle = document.getElementById('videoTitle');
  errorMessage = document.getElementById('errorMessage');
  errorText = document.getElementById('errorText');
  controls = document.getElementById('controls');
  playlistToggle = document.getElementById('playlistToggle');
  downloadType = document.getElementById('downloadType');
  quality = document.getElementById('quality');
  format = document.getElementById('format');
  downloadBtn = document.getElementById('downloadBtn');
  btnText = document.getElementById('btnText');
  btnSpinner = document.getElementById('btnSpinner');
  btnCheck = document.getElementById('btnCheck');
  toast = document.getElementById('toast');
  toastText = document.getElementById('toastText');
}

// Check if local server is running
async function checkServerStatus() {
  try {
    const response = await fetch(SERVER_CHECK_ENDPOINT, {
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    
    if (response.ok) {
      serverOnline = true;
      statusDot.classList.add('online');
      statusText.textContent = 'Server Online';
    } else {
      throw new Error('Server not responding');
    }
  } catch (error) {
    serverOnline = false;
    statusDot.classList.remove('online');
    statusText.textContent = 'Server Offline';
  }
}

// Detect YouTube video from current tab
async function detectVideo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url) {
      showError('Unable to access tab URL');
      return;
    }

    const url = new URL(tab.url);
    
    // Check if it's a YouTube video page
    if (!url.hostname.includes('youtube.com') || !url.searchParams.has('v')) {
      showError('No YouTube video detected on this page');
      return;
    }

    currentUrl = tab.url;
    currentTitle = tab.title.replace(' - YouTube', '');
    
    // Check for playlist
    isPlaylist = url.searchParams.has('list');
    
    if (isPlaylist) {
      playlistToggle.style.display = 'flex';
    }

    // Get video thumbnail (YouTube thumbnail pattern)
    const videoId = url.searchParams.get('v');
    const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`;
    
    // Show video preview
    videoThumbnail.src = thumbnailUrl;
    videoTitle.textContent = currentTitle;
    videoPreview.style.display = 'flex';
    controls.style.display = 'flex';
    errorMessage.style.display = 'none';
    
  } catch (error) {
    console.error('Error detecting video:', error);
    showError('Error detecting video');
  }
}

function showError(message) {
  errorText.textContent = message;
  errorMessage.style.display = 'flex';
  videoPreview.style.display = 'none';
  controls.style.display = 'none';
}

// Event Listeners
function setupEventListeners() {
  // Update format options based on download type
  downloadType.addEventListener('change', (e) => {
    const type = e.target.value;
    const qualityGroup = document.getElementById('qualityGroup');
    
    if (type === 'audio') {
      // Audio formats
      format.innerHTML = `
        <option value="mp3" selected>MP3</option>
        <option value="m4a">M4A</option>
        <option value="opus">OPUS</option>
        <option value="flac">FLAC</option>
      `;
      quality.innerHTML = `
        <option value="best">Best Audio</option>
        <option value="320">Top Quality (320 kbps)</option>
        <option value="256">High (256 kbps)</option>
        <option value="192">Medium (192 kbps)</option>
        <option value="124">Low (128 kbps)</option>
      `;
      // Hide quality selector for audio
      qualityGroup.style.display = 'flex';
    } else {
      // Video formats
      format.innerHTML = `
        <option value="mp4" selected>MP4</option>
        <option value="mkv">MKV</option>
        <option value="webm">WebM</option>
      `;
      quality.innerHTML = `
        <option value="bast">Bast Quality</option>
        <option value="2160">4K (2160p)</option>
        <option value="1440">2K (1440p)</option>
        <option value="1080" selected>Full HD (1080p)</option>
        <option value="720">HD (720p)</option>
        <option value="480">SD (480p)</option>
        <option value="360">Low (360p)</option>
        <option value="240"></option>
        
      `;
      qualityGroup.style.display = 'flex';
    }
  });

  // Download button
  downloadBtn.addEventListener('click', handleDownload);
}

// Handle download request
async function handleDownload() {
  if (!serverOnline) {
    showToast('❌ Server is offline! Make sure Python CLI is running.');
    return;
  }

  if (!currentUrl) {
    showToast('❌ No video detected');
    return;
  }

  // Disable button and show loading
  downloadBtn.disabled = true;
  btnText.style.display = 'none';
  btnSpinner.style.display = 'block';

  try {
    // Determine if downloading playlist
    const playlistMode = document.querySelector('input[name="playlistMode"]:checked')?.value || 'single';
    const downloadPlaylist = isPlaylist && playlistMode === 'playlist';

    // Build payload
    const payload = {
      url: currentUrl,
      download_type: downloadType.value,
      is_playlist: downloadPlaylist,
      quality: quality.value,
      format: format.value,
      title: currentTitle
    };

    console.log('Sending download request:', payload);

    const response = await fetch(DOWNLOAD_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || 'Server error');
    }

    const result = await response.json();
    console.log('Download request successful:', result);

    // Show success
    btnSpinner.style.display = 'none';
    btnCheck.style.display = 'block';
    btnText.textContent = 'Sent!';
    btnText.style.display = 'block';

    showToast('✅ Download request sent successfully!');

    // Reset button after 2 seconds
    setTimeout(() => {
      btnCheck.style.display = 'none';
      btnText.textContent = 'Download';
      downloadBtn.disabled = false;
    }, 2000);

  } catch (error) {
    console.error('Download error:', error);
    
    btnSpinner.style.display = 'none';
    btnText.style.display = 'block';
    downloadBtn.disabled = false;

    showToast(`❌ Error: ${error.message}`);
  }
}

// Show toast notification
function showToast(message) {
  toastText.textContent = message;
  toast.classList.add('show');
  
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

// Load saved preferences
async function loadPreferences() {
  try {
    const result = await chrome.storage.sync.get(['defaultQuality', 'defaultFormat', 'defaultType']);
    
    if (result.defaultQuality) {
      quality.value = result.defaultQuality;
    }
    if (result.defaultFormat) {
      format.value = result.defaultFormat;
    }
    if (result.defaultType) {
      downloadType.value = result.defaultType;
      downloadType.dispatchEvent(new Event('change'));
    }
  } catch (error) {
    console.error('Error loading preferences:', error);
  }
}

// Save preferences when changed
function savePreference(key, value) {
  chrome.storage.sync.set({ [key]: value }).catch(console.error);
}

function updateStatusUI(online) {
  if (online) {
    statusDot.style.background = '#22c55e'; // সবুজ রঙ
    statusText.textContent = 'Online';
    statusDot.style.boxShadow = '0 0 8px #22c55e';
  } else {
    statusDot.style.background = '#ef4444'; // লাল রঙ
    statusText.textContent = 'Offline';
    statusDot.style.boxShadow = 'none';
  }
}
// Optional: Auto-save preferences
quality.addEventListener('change', (e) => savePreference('defaultQuality', e.target.value));
format.addEventListener('change', (e) => savePreference('defaultFormat', e.target.value));
downloadType.addEventListener('change', (e) => savePreference('defaultType', e.target.value));

// Load preferences on init
loadPreferences();
