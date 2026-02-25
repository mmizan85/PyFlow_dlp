# PyFlow Python CLI

High-performance async YouTube downloader with a beautiful terminal UI.

## Features

- ⚡ **Async Architecture** - Non-blocking downloads with concurrent processing
- 🎨 **Rich Terminal UI** - Real-time dashboard with progress bars
- 🔄 **Smart Queue System** - Downloads and processes files in parallel
- 🌐 **REST API** - FastAPI server for Chrome Extension communication
- 📦 **Cross-platform** - Works on Windows, macOS, and Linux
- 🎯 **Powered by yt-dlp** - Industry-leading YouTube downloader
- 🎬 **FFmpeg Integration** - Automatic format conversion and merging

## Architecture

```
┌─────────────────────┐
│  Chrome Extension   │
└──────────┬──────────┘
           │ HTTP POST
           ▼
┌─────────────────────┐
│   FastAPI Server    │ (port 8000)
│   (server.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Download Manager   │
│  (Async Queue)      │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐  ┌──────────┐
│ yt-dlp  │  │  FFmpeg  │
│ Worker  │  │  Worker  │
└─────────┘  └──────────┘
    │             │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  Rich UI    │
    │  (Live      │
    │   Table)    │
    └─────────────┘
```

## Requirements

- Python 3.10+
- ffmpeg (must be in PATH)
- pip packages (see requirements.txt)

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `yt-dlp` - YouTube downloader
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `rich` - Terminal UI
- `pydantic` - Data validation

### 2. Install FFmpeg

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Linux (Fedora):**
```bash
sudo dnf install ffmpeg
```

### 3. Verify Installation

```bash
python -c "from utils import check_dependencies, print_dependency_status; print_dependency_status()"
```

You should see all dependencies marked as ✅ Installed.

## Usage

### Starting the Server

```bash
python main.py
```

You should see:
```
🚀 PyFlow - YouTube Downloader CLI
==================================================
✅ Server started on http://localhost:8000
📦 Download directory: /Users/YourName/Downloads/PyFlow

💡 Open your browser and use the PyFlow extension!
==================================================
```

### Terminal UI

The UI shows:
- **Header**: Queue size, active downloads, completed count
- **Active Downloads Table**: Real-time progress, speed, ETA
- **Completed Table**: Recently finished downloads
- **Footer**: Download directory path

### Stopping the Server

Press `Ctrl+C` to gracefully shutdown.

## Configuration

### Download Settings

Edit `download_manager.py`:

```python
class DownloadManager:
    def __init__(self, max_concurrent_downloads: int = 2):
        # Adjust based on your system
        # Recommended: 2-3 for most systems
```

### Download Directory

By default, downloads go to:
- **Windows**: `C:\Users\YourName\Downloads\PyFlow`
- **macOS**: `/Users/YourName/Downloads/PyFlow`
- **Linux**: `/home/yourname/Downloads/PyFlow`

To change, edit `utils.py`:
```python
def get_download_directory() -> Path:
    return Path.home() / "Downloads" / "PyFlow"
    # Change to your preferred location
```

### Server Port

To change from port 8000, edit `main.py`:
```python
config = uvicorn.Config(
    app,
    host="127.0.0.1",
    port=8000,  # Change this
    ...
)
```

**Note:** If you change the port, update it in the Chrome Extension's `popup.js`:
```javascript
const SERVER_URL = 'http://localhost:8000'; // Update here
```

## File Structure

```
python-cli/
├── main.py                 # Entry point, orchestrates everything
├── server.py              # FastAPI REST API server
├── download_manager.py    # Async queue & yt-dlp wrapper
├── ui.py                  # Rich terminal UI manager
├── utils.py               # Helper functions (paths, formatting)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## API Endpoints

### GET /health
Check if server is running and get status

**Response:**
```json
{
  "status": "online",
  "queue_size": 2,
  "active_downloads": 1
}
```

### POST /add-download
Add a download to the queue

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=xyz",
  "download_type": "video",
  "is_playlist": false,
  "quality": "1080p",
  "format": "mp4",
  "title": "Video Title"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Download queued successfully",
  "task_id": "a1b2c3d4"
}
```

### GET /queue
Get current queue status

**Response:**
```json
{
  "queue_size": 2,
  "active_tasks": [
    {
      "id": "a1b2c3d4",
      "title": "Video Title",
      "status": "Downloading",
      "progress": 45.2
    }
  ]
}
```

### DELETE /cancel/{task_id}
Cancel a download

**Response:**
```json
{
  "status": "success",
  "message": "Task a1b2c3d4 cancelled"
}
```

## How It Works

### Download Flow

1. **Request Received**: Chrome Extension sends POST to `/add-download`
2. **Task Created**: `DownloadManager` creates a `DownloadTask` object
3. **Queue Add**: Task is added to async queue
4. **Worker Picks Up**: One of the worker coroutines picks up the task
5. **Download Starts**: yt-dlp begins downloading
6. **Progress Updates**: UI updates in real-time via progress hooks
7. **Processing**: FFmpeg converts/merges if needed
8. **Complete**: File saved, task moved to completed list

### Concurrency Model

- **Async Queue**: `asyncio.Queue` for task management
- **Semaphore**: Limits concurrent downloads (default: 2)
- **Executor**: Blocking yt-dlp calls run in thread pool
- **Non-blocking**: UI and server remain responsive

### Quality Selection

The quality parameter works as follows:
- `"best"`: Highest available quality
- `"2160p"`, `"1080p"`, etc.: Specific resolution (or next best)
- For audio: Always uses best available quality

### Format Handling

**Video formats:**
- `mp4`: H.264 video + AAC audio (most compatible)
- `mkv`: Matroska container (supports any codec)
- `webm`: VP9/AV1 video + Opus audio

**Audio formats:**
- `mp3`: Standard MP3 audio
- `m4a`: AAC audio in MP4 container
- `opus`: Opus audio (high quality, low size)
- `flac`: Lossless audio

## Troubleshooting

### FFmpeg not found

**Error:**
```
ffmpeg not found in PATH
```

**Solution:**
1. Install ffmpeg (see Installation section)
2. Verify: `ffmpeg -version`
3. Restart terminal/CLI

### yt-dlp errors

**Error:**
```
ERROR: unable to download video data
```

**Possible causes:**
- Video is private/age-restricted
- Video has been removed
- Network connectivity issue
- yt-dlp needs update

**Solution:**
```bash
pip install --upgrade yt-dlp
```

### Port already in use

**Error:**
```
[ERROR] [Errno 48] Address already in use
```

**Solution:**
1. Kill process using port 8000:
   ```bash
   # macOS/Linux
   lsof -ti:8000 | xargs kill -9
   
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```
2. Or change port in `main.py`

### Slow downloads

**Possible causes:**
- Too many concurrent downloads
- Network speed limitation
- CPU bottleneck from FFmpeg

**Solutions:**
1. Reduce `max_concurrent_downloads` to 1-2
2. Choose lower quality settings
3. Disable FFmpeg processing (download only)

### Permission errors

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
1. Check download directory permissions
2. Run with appropriate permissions
3. Change download directory to user-writable location

## Performance Tips

1. **Concurrent Downloads**: 
   - Fast internet + powerful CPU: 3-4
   - Normal systems: 2 (default)
   - Slow systems: 1

2. **Quality vs Speed**:
   - 1080p: Good balance
   - 720p: Faster downloads
   - 4K: Slower, larger files

3. **Format Choice**:
   - MP4: Fast processing
   - MKV: No re-encoding needed
   - Audio only: Fastest

## Advanced Usage

### Custom yt-dlp Options

Edit `download_manager.py` → `_build_ydl_options()`:

```python
opts = {
    'outtmpl': output_template,
    'quiet': False,
    # Add custom options here
    'nocheckcertificate': True,
    'age_limit': 18,
    'geo_bypass': True,
}
```

### Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Custom Progress Hooks

Modify the progress hook in `download_manager.py`:

```python
def progress_hook(d):
    if d['status'] == 'downloading':
        # Your custom logic here
        print(f"Downloaded: {d.get('downloaded_bytes', 0)} bytes")
```

## System Requirements

**Minimum:**
- CPU: Dual-core 2.0 GHz
- RAM: 2 GB
- Storage: 100 MB (application) + download space
- Network: Stable internet connection

**Recommended:**
- CPU: Quad-core 2.5 GHz+
- RAM: 4 GB+
- Storage: SSD with ample space
- Network: High-speed broadband

## Known Limitations

- Maximum 10 concurrent downloads (hard-coded safety limit)
- Live streams not supported
- Playlists with 100+ videos may take significant time
- Age-restricted content requires authentication (not implemented)

## Contributing

To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Educational use only. Respect YouTube's Terms of Service and copyright laws.

---

Part of the PyFlow YouTube Downloader project
