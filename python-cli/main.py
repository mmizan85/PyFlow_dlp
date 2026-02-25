#!/usr/bin/env python3
"""
PyFlow –- YouTube Downloader Server
════════════════════════════════════════════════════════════════════

Usage
─────
  pyflow                      Start server (show UI)
  pyflow --hidden             Start server in background (daemon)
  pyflow --show               Start server and show full live UI
  pyflow --path <DIR>         Override download directory
  pyflow --port <PORT>        Override server port (default: 8000)
  pyflow --host <HOST>        Override bind address (default: 127.0.0.1)
  pyflow --stop               Shut down a running background server
  pyflow --status             Show server status
  pyflow --version            Print version and exit
  pyflow --help / -h          Show this help message

Platform: Windows, Linux, macOS  (Python 3.9+)
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import signal
import sys
from pathlib import Path
from threading import Thread

# ── Bootstrap: ensure project root is on sys.path ────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

from download_manager import DownloadManager
from server import create_app
from ui import UIManager
from utils import (
    get_download_directory,
    load_config,
    save_config,
    print_dependency_status,
    set_download_directory,
)

# ── Constants ─────────────────────────────────────────────────────────────────
VERSION     = "2.0.0"
DEFAULT_PORT = 8000
DEFAULT_HOST = "127.0.0.1"
PID_FILE     = Path(__file__).parent / ".pyflow.pid"   # tracks background PID


# ── Logging ───────────────────────────────────────────────────────────────────

def _configure_logging(show_ui: bool):
    """
    When show_ui=True  → log only to file (console is used by Rich Live)
    When show_ui=False → log to file and console (no Live widget)
    """
    handlers = [logging.FileHandler("pyflow.log", encoding="utf-8")]
    if not show_ui:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=handlers,
        force=True,
    )


# ── Argument Parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyflow",
        description="PyFlow – YouTube Downloader Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=True,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--hidden",
        action="store_true",
        help="Run server in background. Terminal can be closed safely.",
    )
    mode.add_argument(
        "--show",
        action="store_true",
        help="Run server with full live UI dashboard (default when no mode given).",
    )
    mode.add_argument(
        "--stop",
        action="store_true",
        help="Stop a running background server and exit.",
    )
    mode.add_argument(
        "--status",
        action="store_true",
        help="Check whether a PyFlow server is currently running.",
    )
    parser.add_argument(
        "--_daemon",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--path", "-p",
        metavar="DIR",
        help="Set download directory. Saved for future runs.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        metavar="PORT",
        help=f"HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        metavar="HOST",
        help=f"Bind address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Skip background yt-dlp auto-update on startup.",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"PyFlow {VERSION}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check dependencies and exit.",
    )

    return parser


# ── Background (daemon) helpers ────────────────────────────────────────────────

def _save_pid(pid: int):
    PID_FILE.write_text(str(pid))


def _read_pid() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            pass
    return None


def _stop_server():
    """Send SIGTERM to a running background server."""
    pid = _read_pid()
    if pid is None:
        print("ℹ️  No PyFlow PID file found – server may not be running.")
        return

    system = platform.system()
    try:
        if system == "Windows":
            import subprocess
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            os.kill(pid, signal.SIGTERM)

        PID_FILE.unlink(missing_ok=True)
        print(f"✅ PyFlow server (PID {pid}) stopped.")
    except ProcessLookupError:
        print(f"⚠️  Process {pid} not found – maybe already stopped.")
        PID_FILE.unlink(missing_ok=True)
    except Exception as exc:
        print(f"❌ Failed to stop server: {exc}")


def _show_status():
    """Report whether a background server is running."""
    import urllib.request, urllib.error
    pid = _read_pid()
    if pid:
        print(f"📌 PID file exists: {pid}")
    else:
        print("ℹ️  No PID file – server was not started with --hidden")

    # Try pinging the health endpoint
    try:
        with urllib.request.urlopen(
            f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/health", timeout=2
        ) as resp:
            data = json.loads(resp.read())
            print(f"✅ Server is online  yt-dlp={data.get('ytdlp_version', '?')}  "
                  f"active={data.get('active_downloads', 0)}")
    except Exception:
        print("❌ Server is not responding on "
              f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")


def _daemonize():
    """
    Detach the process from the terminal on POSIX systems.
    On Windows we use subprocess to spawn a detached process instead.
    """
    system = platform.system()
    if system == "Windows":
        # Re-launch via subprocess with CREATE_NO_WINDOW
        import subprocess
        CREATE_NO_WINDOW = 0x08000000
        args = [sys.executable] + [a for a in sys.argv if a != "--hidden"] + ["--_daemon"]
        proc = subprocess.Popen(
            args,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
        print(f"🚀 PyFlow server started in background (PID {proc.pid})")
        print("   Use  pyflow --stop  to shut it down.")
        _save_pid(proc.pid)
        sys.exit(0)
    else:
        # Unix double-fork daemon
        pid = os.fork()
        if pid > 0:
            # Parent: save child PID and exit
            _save_pid(pid)
            print(f"🚀 PyFlow server started in background (PID {pid})")
            print("   Use  pyflow --stop  to shut it down.")
            sys.exit(0)

        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            sys.exit(0)

        # Redirect std streams
        sys.stdin  = open(os.devnull)
        sys.stdout = open("pyflow.log", "a", buffering=1)
        sys.stderr = sys.stdout


# ── Server Runner ─────────────────────────────────────────────────────────────

def _run_uvicorn(app, host: str, port: int):
    """Run uvicorn in its own thread."""
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="critical",
        access_log=False,
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


async def _run(args, show_ui: bool):
    """Main async logic – starts download manager, server, and optional UI."""
    print("🚀 PyFlow YouTube Downloader  v" + VERSION)
    print("=" * 55)

    # Apply path override
    download_dir = None
    if args.path:
        download_dir = set_download_directory(args.path)
        print(f"📁 Download directory set to: {download_dir}")
    else:
        download_dir = get_download_directory()

    # Boot components
    download_manager = DownloadManager(download_dir=download_dir)

    # Optionally disable auto-update
    if args.no_update:
        # Monkey-patch updater to do nothing
        async def _noop(): pass
        download_manager._background_update_ytdlp = _noop

    app = create_app(download_manager)
    ui_manager = UIManager(download_manager) if show_ui else None

    # Start HTTP server in background thread
    server_thread = Thread(
        target=_run_uvicorn, args=(app, args.host, args.port), daemon=True
    )
    server_thread.start()

    print(f"✅ Server started  →  http://{args.host}:{args.port}")
    print(f"📁 Downloads dir   →  {download_manager.download_dir}")
    if not show_ui:
        print("\n💡 Use the PyFlow Chrome Extension to queue downloads.")
        print("   Logs are written to pyflow.log")
        print("   Press Ctrl+C to stop.")
    print("=" * 55)
    print()

    # Launch coroutines
    tasks = [asyncio.create_task(download_manager.process_queue())]
    if ui_manager:
        tasks.append(asyncio.create_task(ui_manager.run()))

    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\n🛑 Shutting down PyFlow…")
        download_manager.shutdown()
        if ui_manager:
            ui_manager.shutdown()
        PID_FILE.unlink(missing_ok=True)


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = _build_parser()
    args = parser.parse_args()

    # ── Sub-commands that don't start a server ────────────────────────────────
    if args.show:
        pid = _read_pid()
        if pid:
            print(f"🔄 A background server (PID {pid}) is running. Stopping it to show UI...")
            _stop_server()
            import time
            time.sleep(2)  # Give it a moment to shut down before restarting with UI                            
            
    if args.check:
        print_dependency_status()
        sys.exit(0)

    if args.stop:
        _stop_server()
        sys.exit(0)

    if args.status:
        _show_status()
        sys.exit(0)

    # ── Apply path early (before daemon fork) ─────────────────────────────────
    if args.path:
        set_download_directory(args.path)

    # ── Hidden / background mode ──────────────────────────────────────────────
    if args.hidden and not args._daemon:
        _configure_logging(show_ui=False)
        _daemonize()
        # _daemonize() exits the parent; child continues below
        return

    # ── Decide whether to show the Rich UI ───────────────────────────────────
    #   show_ui = True  unless --hidden daemon child  (no tty available)
    
    show_ui = not (args.hidden or args._daemon)   # daemon child won't have a tty
    
    # show_ui = show_ui or args.show  # but --show forces it on even if --hidden
    _configure_logging(show_ui=show_ui)

    try:
        asyncio.run(_run(args, show_ui=show_ui))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
