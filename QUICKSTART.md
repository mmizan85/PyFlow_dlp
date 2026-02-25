# PyFlow Quick Start Guide

## ⚡ Super Fast Setup (5 Minutes)

### Step 1: Install Python Dependencies (1 min)
```bash
cd pyflow-downloader/python-cli
pip install -r requirements.txt
```

### Step 2: Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:** Download from https://www.gyan.dev/ffmpeg/builds/

### Step 3: Start Python Server (30 seconds)
```bash
# On macOS/Linux:
./start.sh

# On Windows:
start.bat

# Or manually:
python main.py
```

### Step 4: Install Chrome Extension (1 min)
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. Done!

### Step 5: Test It! (1 min)
1. Go to any YouTube video
2. Click the PyFlow extension icon
3. Click "Download"
4. Check `~/Downloads/PyFlow` for your file!

---

## 📁 Project Structure Overview

```
pyflow-downloader/
├── chrome-extension/     → Install this in Chrome
│   ├── manifest.json
│   ├── popup.html/css/js
│   └── content.js/css
│
└── python-cli/          → Run this first!
    ├── main.py          → Entry point
    ├── requirements.txt → Dependencies
    └── start.sh/.bat    → Quick start scripts
```

---

## 🎯 Basic Usage

### Download a Single Video
1. Navigate to YouTube video
2. Click PyFlow icon
3. Select quality (1080p recommended)
4. Click "Download"

### Download a Playlist
1. Navigate to video in a playlist
2. Click PyFlow icon
3. Toggle "Whole Playlist"
4. Click "Download"

### Audio Only
1. Select "Audio Only" from Type dropdown
2. Choose format (MP3 most compatible)
3. Click "Download"

---

## 🔧 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "Server Offline" | Run `python main.py` in python-cli folder |
| FFmpeg not found | Install FFmpeg and add to PATH |
| pip install fails | Try `pip3 install -r requirements.txt` |
| Port 8000 in use | Kill process or change port in code |
| Downloads slow | Reduce quality or concurrent downloads |

---

## 📊 Feature Cheat Sheet

### Quality Options
- **4K (2160p)** - Highest quality, large files
- **1080p** ⭐ - Best balance (recommended)
- **720p** - Faster, smaller files
- **480p/360p** - Mobile-friendly

### Format Options

**Video:**
- **MP4** ⭐ - Most compatible
- **MKV** - Better quality retention
- **WebM** - Smaller file size

**Audio:**
- **MP3** ⭐ - Universal compatibility
- **M4A** - Better quality
- **FLAC** - Lossless audio

### Download Types
- **Video** - Full video with audio
- **Audio Only** - Extract audio track

---

## 💡 Pro Tips

1. **Always start Python CLI first** before using the extension
2. **Use 720p for speed** if 1080p is too slow
3. **Check disk space** before downloading playlists
4. **Monitor the terminal** to see download progress
5. **Test with short videos** before downloading long content

---

## 📱 Where Are My Downloads?

- **Windows:** `C:\Users\YourName\Downloads\PyFlow`
- **macOS:** `/Users/YourName/Downloads/PyFlow`
- **Linux:** `/home/yourname/Downloads/PyFlow`

---

## 🚨 Emergency Troubleshooting

If something breaks:

1. **Restart everything:**
   ```bash
   # Kill Python CLI (Ctrl+C)
   # Restart it
   python main.py
   
   # Reload extension in Chrome
   chrome://extensions/ → Click reload
   ```

2. **Check dependencies:**
   ```bash
   python -c "from utils import print_dependency_status; print_dependency_status()"
   ```

3. **Clear and reinstall:**
   ```bash
   pip uninstall yt-dlp fastapi uvicorn rich
   pip install -r requirements.txt
   ```

---

## 📚 Full Documentation

- **README.md** - Complete feature overview
- **INSTALL.md** - Detailed installation guide
- **STRUCTURE.md** - Technical architecture
- **python-cli/README.md** - CLI documentation
- **chrome-extension/README.md** - Extension docs

---

## ⚠️ Legal Reminder

- For personal use only
- Respect YouTube's Terms of Service
- Don't redistribute copyrighted content
- Support content creators!

---

## 🎉 You're Ready!

That's it! You now have a powerful YouTube downloader with:
- ✅ Modern UI
- ✅ Playlist support
- ✅ Multiple quality options
- ✅ Real-time progress tracking
- ✅ Cross-platform compatibility

Enjoy! 🚀
