# PyFlow Project Structure

```
pyflow-downloader/
│
├── README.md                          # Main project documentation
├── INSTALL.md                         # Step-by-step installation guide
├── LICENSE                            # MIT License with disclaimer
│
├── chrome-extension/                  # Chrome Extension (Frontend)
│   ├── manifest.json                  # Extension configuration (V3)
│   ├── README.md                      # Extension-specific docs
│   │
│   ├── popup.html                     # Main popup interface
│   ├── popup.css                      # Popup styling (dark theme)
│   ├── popup.js                       # Popup logic & API calls
│   │
│   ├── content.js                     # YouTube page injection
│   ├── content.css                    # Injected button styling
│   │
│   └── icons/                         # Extension icons (16x16, 48x48, 128x128)
│       └── (add your .png icons here)
│
└── python-cli/                        # Python CLI Application (Backend)
    ├── README.md                      # CLI-specific documentation
    ├── requirements.txt               # Python dependencies
    │
    ├── main.py                        # Entry point (orchestrator)
    ├── server.py                      # FastAPI REST API server
    ├── download_manager.py            # Async download queue + yt-dlp wrapper
    ├── ui.py                          # Rich terminal UI manager
    ├── utils.py                       # Helper functions
    │
    ├── start.sh                       # Unix/Linux/macOS startup script
    └── start.bat                      # Windows startup script
```

## File Descriptions

### Root Level
- **README.md**: Complete project overview, features, and quick start
- **INSTALL.md**: Detailed installation instructions with troubleshooting
- **LICENSE**: MIT license with usage disclaimer

### Chrome Extension
- **manifest.json**: Extension metadata, permissions, and configuration
- **popup.html**: Main UI - video preview, download controls
- **popup.css**: Modern dark theme with glassmorphism effects
- **popup.js**: 
  - Detects YouTube videos/playlists
  - Communicates with Python server (fetch API)
  - Handles user preferences (Chrome storage)
- **content.js**: 
  - Injects download button into YouTube pages
  - Observes URL changes (SPA detection)
  - Shows modal overlay for instructions
- **content.css**: Styles for injected button and modal

### Python CLI
- **main.py**: 
  - Initializes all components
  - Starts FastAPI server in background thread
  - Runs download worker and UI loop concurrently
  
- **server.py**:
  - FastAPI application
  - CORS middleware for extension requests
  - Endpoints: /health, /add-download, /queue, /cancel
  
- **download_manager.py**:
  - Async queue system (asyncio.Queue)
  - DownloadTask dataclass
  - yt-dlp wrapper with progress hooks
  - Semaphore for concurrency control
  - Builds yt-dlp options based on quality/format
  
- **ui.py**:
  - Rich library integration
  - Live updating table
  - Shows active downloads with progress bars
  - Displays recently completed tasks
  
- **utils.py**:
  - Cross-platform path handling
  - Format size/time helpers
  - Filename sanitization
  - Dependency checking
  
- **start.sh / start.bat**:
  - Automated startup scripts
  - Dependency verification
  - Installation helpers

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        User Action                          │
│  (Opens extension popup on YouTube video page)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chrome Extension                          │
│  - popup.js detects video URL                               │
│  - Checks server status (GET /health)                       │
│  - Shows video preview with options                         │
│  - User configures: quality, format, playlist mode          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST /add-download
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                            │
│  - Receives JSON request                                    │
│  - Validates URL and parameters                             │
│  - Creates DownloadTask                                     │
│  - Adds to async queue                                      │
│  - Returns task_id                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Download Manager                            │
│  - Worker picks task from queue                             │
│  - Builds yt-dlp options                                    │
│  - Runs yt-dlp in thread executor                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │         │
                    ▼         ▼
        ┌──────────────┐  ┌──────────────┐
        │   yt-dlp     │  │   FFmpeg     │
        │  (Download)  │  │ (Processing) │
        └──────┬───────┘  └──────┬───────┘
               │                 │
               │   Progress      │
               │   Hooks         │
               ▼                 ▼
        ┌─────────────────────────────┐
        │      UI Manager             │
        │  - Updates live table       │
        │  - Shows progress bars      │
        │  - Displays speed/ETA       │
        └─────────────────────────────┘
                    │
                    ▼
            ┌──────────────┐
            │   Terminal   │
            │   Display    │
            └──────────────┘
```

## Technology Stack

### Frontend (Chrome Extension)
- **Language**: JavaScript (ES6+)
- **UI**: HTML5 + CSS3 (Glassmorphism design)
- **APIs**: 
  - Chrome Extension API (Manifest V3)
  - Fetch API for HTTP requests
  - Chrome Storage API for preferences

### Backend (Python CLI)
- **Language**: Python 3.10+
- **Web Framework**: FastAPI
- **Server**: Uvicorn (ASGI)
- **Download Engine**: yt-dlp
- **Media Processing**: FFmpeg (subprocess)
- **Concurrency**: asyncio + ThreadPoolExecutor
- **Terminal UI**: Rich library
- **Data Validation**: Pydantic

## Key Features Implementation

### 1. Playlist Detection
- Extension parses URL for `list=` parameter
- Shows segmented control toggle
- Sends `is_playlist` boolean to server
- Server configures yt-dlp accordingly

### 2. Quality Selection
- User selects from: 4K, 1080p, 720p, 480p, 360p, best
- Extension sends quality string
- Server builds format string for yt-dlp:
  - `bestvideo[height<=1080]+bestaudio` for 1080p
  - `bestvideo+bestaudio/best` for "best"

### 3. Format Conversion
- User selects output format (mp4, mkv, webm, mp3, etc.)
- For video: `merge_output_format` parameter
- For audio: FFmpegExtractAudio postprocessor
- FFmpeg runs in separate semaphore-controlled workers

### 4. Progress Tracking
- yt-dlp progress hooks update DownloadTask
- UI Manager polls tasks at 4Hz
- Rich library renders live table
- Shows: progress bar, speed, ETA

### 5. Non-blocking Architecture
- FastAPI runs in background thread
- Download workers are async coroutines
- Blocking yt-dlp calls use `run_in_executor`
- Semaphore limits concurrent downloads
- UI updates don't block downloads

## Installation Requirements

### Minimum
- Python 3.10+
- 100 MB disk space (for application)
- 2 GB RAM
- Chrome 88+

### Recommended
- Python 3.11+
- SSD with ample space for downloads
- 4+ GB RAM
- Fast internet connection

## Dependencies

### Python Packages
- `yt-dlp` >= 2024.1.0 - YouTube downloader
- `fastapi` >= 0.109.0 - Web framework
- `uvicorn` >= 0.27.0 - ASGI server
- `pydantic` >= 2.5.0 - Data validation
- `rich` >= 13.7.0 - Terminal UI

### System Dependencies
- `ffmpeg` - Media processing (must be in PATH)

## Cross-Platform Compatibility

### Windows
- Uses backslashes in paths
- Downloads to `%USERPROFILE%\Downloads\PyFlow`
- Startup script: `start.bat`
- FFmpeg: Manual installation required

### macOS
- Uses forward slashes
- Downloads to `~/Downloads/PyFlow`
- Startup script: `start.sh`
- FFmpeg: Installable via Homebrew

### Linux
- Standard Unix paths
- Downloads to `~/Downloads/PyFlow`
- Startup script: `start.sh`
- FFmpeg: Available in package managers

## Security Considerations

1. **Local-only**: All communication over localhost
2. **No external servers**: Downloads processed locally
3. **No data collection**: Extension stores only user preferences
4. **CORS protection**: Server accepts only from extension
5. **Input validation**: All URLs and parameters validated

## Performance Optimizations

1. **Async architecture**: Non-blocking I/O
2. **Semaphore limits**: Prevents CPU/bandwidth overload
3. **Thread pool**: Blocking operations don't stall event loop
4. **Debounced UI**: Updates at 4Hz, not on every change
5. **Efficient format selection**: yt-dlp downloads optimal format

## Future Enhancement Ideas

- [ ] Authentication for age-restricted videos
- [ ] Subtitle download support
- [ ] Custom download directory selection
- [ ] Download history/database
- [ ] Resume interrupted downloads
- [ ] Scheduled downloads
- [ ] Batch URL import
- [ ] Bandwidth limiting
- [ ] Custom yt-dlp options UI
- [ ] WebUI alternative to CLI
