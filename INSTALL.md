# PyFlow Installation Guide

Complete step-by-step installation instructions for PyFlow YouTube Downloader.

## 📋 Prerequisites Check

Before starting, ensure you have:
- [ ] Google Chrome (or Chromium-based browser)
- [ ] Python 3.10 or higher
- [ ] pip (Python package manager)
- [ ] Internet connection

## 🐍 Part 1: Python CLI Setup

### Step 1: Verify Python Installation

Open your terminal/command prompt and check Python version:

```bash
python --version
# or
python3 --version
```

You should see `Python 3.10.x` or higher. If not, download from [python.org](https://www.python.org/downloads/).

### Step 2: Navigate to Python CLI Directory

```bash
cd path/to/pyflow-downloader/python-cli
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Windows users:** You might need to use `pip3` instead of `pip`.

**If you see permission errors:**
```bash
pip install --user -r requirements.txt
```

### Step 4: Install FFmpeg

#### Windows

1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Choose "ffmpeg-release-essentials.zip"
3. Extract to `C:\ffmpeg`
4. Add to PATH:
   - Open System Properties → Environment Variables
   - Edit "Path" under System Variables
   - Add new entry: `C:\ffmpeg\bin`
   - Click OK

#### macOS

Using Homebrew (recommended):
```bash
brew install ffmpeg
```

If you don't have Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg
```

#### Linux (Fedora/CentOS)

```bash
sudo dnf install ffmpeg
```

### Step 5: Verify FFmpeg Installation

```bash
ffmpeg -version
```

You should see FFmpeg version information.

### Step 6: Test Python CLI

```bash
python main.py
```

You should see:
```
🚀 PyFlow - YouTube Downloader CLI
==================================================
✅ Server started on http://localhost:8000
📦 Download directory: /Users/YourName/Downloads/PyFlow
==================================================
```

**Keep this terminal window open!** The server must be running for the extension to work.

To stop the server: Press `Ctrl+C`

## 🌐 Part 2: Chrome Extension Setup

### Step 1: Open Chrome Extensions Page

1. Open Google Chrome
2. Navigate to `chrome://extensions/`
3. Or click: Menu (⋮) → Extensions → Manage Extensions

### Step 2: Enable Developer Mode

1. Look for "Developer mode" toggle in the top-right corner
2. Turn it ON (should turn blue)

### Step 3: Load the Extension

1. Click "Load unpacked" button
2. Navigate to the `chrome-extension` folder inside `pyflow-downloader`
3. Select the folder and click "Select Folder" (or "Open" on Mac)

### Step 4: Verify Installation

You should see the PyFlow extension in your extensions list:
- Extension name: "PyFlow - YouTube Downloader Bridge"
- Status: Enabled
- Permissions: Listed below the extension

### Step 5: Pin Extension (Optional but Recommended)

1. Click the puzzle piece icon in Chrome toolbar
2. Find "PyFlow - YouTube Downloader Bridge"
3. Click the pin icon to keep it visible

## ✅ Part 3: Testing the Setup

### Test 1: Check Server Connection

1. Make sure Python CLI is running (`python main.py`)
2. Click the PyFlow extension icon in Chrome
3. Check the status indicator:
   - 🟢 Green dot = Server Online ✓
   - 🔴 Red dot = Server Offline ✗

If server is offline:
- Go back to terminal and start Python CLI
- Wait a few seconds and refresh

### Test 2: Try a Download

1. Go to any YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ
2. Click the PyFlow extension icon
3. You should see:
   - Video thumbnail
   - Video title
   - Download options
4. Configure settings and click "Download"
5. Check the Python CLI terminal - you should see:
   ```
   Received download request: Video Title
   Starting download: Video Title
   ```

### Test 3: Check Downloaded File

1. Open your file manager
2. Navigate to Downloads folder
3. Look for "PyFlow" folder
4. Your downloaded video should be there!

**Default locations:**
- Windows: `C:\Users\YourName\Downloads\PyFlow`
- macOS: `/Users/YourName/Downloads/PyFlow`
- Linux: `/home/yourname/Downloads/PyFlow`

## 🔧 Troubleshooting

### Problem: Extension shows "Server Offline"

**Cause:** Python CLI is not running

**Solution:**
```bash
cd python-cli
python main.py
```

### Problem: "pip: command not found"

**Cause:** pip is not installed or not in PATH

**Solution:**
```bash
python -m pip install -r requirements.txt
```

### Problem: "ModuleNotFoundError: No module named 'yt_dlp'"

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install yt-dlp fastapi uvicorn rich
```

### Problem: FFmpeg errors

**Cause:** FFmpeg not installed or not in PATH

**Solution:**
1. Verify installation: `ffmpeg -version`
2. If not found, reinstall FFmpeg (see Step 4)
3. Restart terminal after installation

### Problem: Extension doesn't appear in list

**Cause:** Wrong folder selected or manifest.json error

**Solution:**
1. Make sure you selected the `chrome-extension` folder (not the parent folder)
2. Check that `manifest.json` exists in the folder
3. Try: Remove extension → Reload → Add again

### Problem: "Permission denied" when downloading

**Cause:** No write permission to Downloads folder

**Solution:**
- On macOS/Linux: `chmod 755 ~/Downloads/PyFlow`
- Or change download directory in `utils.py`

### Problem: Port 8000 already in use

**Cause:** Another application is using port 8000

**Solution:**

**Option 1 - Find and kill the process:**
```bash
# macOS/Linux
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

**Option 2 - Change port:**
1. Edit `python-cli/main.py`, line with `port=8000` → change to `port=8001`
2. Edit `chrome-extension/popup.js`, line with `http://localhost:8000` → change to `http://localhost:8001`

### Problem: Downloads are very slow

**Possible causes:**
- Slow internet connection
- Too many concurrent downloads
- Low system resources

**Solutions:**
1. Close other applications
2. Reduce download quality (try 720p instead of 1080p)
3. In `download_manager.py`, change `max_concurrent_downloads` from 2 to 1

## 📱 Alternative: Using Without Extension

You can also use the Python CLI directly without the Chrome extension:

### Using yt-dlp directly (Advanced)

```bash
cd python-cli

# Download a video
python -c "
from download_manager import DownloadManager
import asyncio

async def main():
    dm = DownloadManager()
    await dm.add_download(
        url='https://youtube.com/watch?v=YOUR_VIDEO_ID',
        download_type='video',
        is_playlist=False,
        quality='1080p',
        format_type='mp4',
        title='My Video'
    )
    await dm.process_queue()

asyncio.run(main())
"
```

## 🎉 Success Checklist

- [ ] Python 3.10+ installed
- [ ] pip dependencies installed (`yt-dlp`, `fastapi`, `uvicorn`, `rich`)
- [ ] FFmpeg installed and working
- [ ] Python CLI starts without errors
- [ ] Chrome extension loaded successfully
- [ ] Extension shows "Server Online" (green dot)
- [ ] Successfully downloaded a test video
- [ ] File appears in Downloads/PyFlow folder

## 📚 Next Steps

1. Read the main [README.md](README.md) for detailed usage
2. Customize settings in `download_manager.py`
3. Try downloading playlists
4. Experiment with different quality/format options

## 🆘 Still Having Issues?

1. Check all steps again carefully
2. Verify system meets requirements
3. Look at error messages in:
   - Python CLI terminal
   - Chrome Developer Console (F12 in Chrome)
4. Try restarting:
   - Python CLI
   - Chrome browser
   - Your computer (if all else fails)

## 💡 Pro Tips

1. **Always start Python CLI before using extension**
2. **Keep terminal window visible** to monitor downloads
3. **Test with a short video first** before downloading long content
4. **Check available disk space** before downloading large files
5. **Use 720p for faster downloads** if 1080p is too slow

---

Congratulations! You're now ready to use PyFlow! 🎊
