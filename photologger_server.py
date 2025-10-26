# photologger_server.py
import os
import json
import threading
import time
import subprocess
from pathlib import Path
from typing import Dict

from flask import Flask, jsonify, request, Response, make_response
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ---------------------- CONFIG ----------------------
INCOMING_DIR = r"C:\Users\jason\Pictures\incoming"
OUTPUT_DIR   = r"C:\Users\jason\desktop\PhotoLogger\output"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".arw", ".cr2", ".nef", ".mxf", ".mp4", ".dng", ".tif", ".tiff", ".heic", ".cr3"}
RENAME_DELAY = 1.0
STATE_FILE = Path(__file__).with_name("photologger_state.json")
# ----------------------------------------------------

app = Flask(__name__, static_folder=None)

# --- CORS for file:// origin (you open the HTML directly) ---
@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp

@app.route('/api/<path:_any>', methods=['OPTIONS'])
def api_cors_preflight(_any):
    r = make_response('', 204)
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r

state_lock = threading.Lock()
current_count = 1  # in-memory display/ID prefix
seq_per_id: Dict[int, int] = {}  # tracks per-ID sequence numbers

def safe_mkdirs():
    Path(INCOMING_DIR).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def load_state() -> int:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
            v = int(data.get("current_count", 1))
            return max(1, v)
        except Exception:
            return 1
    return 1

def save_state(value: int) -> None:
    try:
        STATE_FILE.write_text(json.dumps({"current_count": int(value)}), encoding='utf-8')
    except Exception:
        # Non-fatal; keep running even if we can't write the file
        pass

safe_mkdirs()
# Load persisted value at startup
with state_lock:
    current_count = load_state()

def get_and_bump_seq_for_id(id_val: int) -> int:
    with state_lock:
        seq = seq_per_id.get(id_val, 0) + 1
        seq_per_id[id_val] = seq
        return seq

def is_media(path: Path) -> bool:
    return path.suffix.lower() in PHOTO_EXTS

def open_html_in_chrome():
    html_path = Path(__file__).with_name('photologger.html')
    file_url = html_path.as_uri()  # e.g., file:///C:/Users/jason/PhotoLogger/photologger.html

    # Prefer Chrome explicitly
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for exe in candidates:
        if Path(exe).exists():
            try:
                subprocess.Popen([exe, file_url], close_fds=True)
                return True
            except Exception:
                pass

    # Fallback: let Windows open it (uses default browser if Chrome isn’t found)
    try:
        os.startfile(html_path)  # type: ignore[attr-defined]
        return True
    except Exception:
        print("[PhotoLogger] Could not auto-open HTML. Open this file manually:")
        print(" ", html_path)
        return False
        
        # Treat these as temp/partial files we should ignore
TEMP_SUFFIXES = (".tmp", ".part", ".crdownload", ".tmp.jpg", ".tmp.jpeg", ".tmp.cr3", ".tmp.png")
TEMP_SNIPPETS = ("~", ".~", "_tmp", ".partial")

def is_temporary_name(name: str) -> bool:
    n = name.lower()
    if n.endswith(TEMP_SUFFIXES):
        return True
    return any(snip in n for snip in TEMP_SNIPPETS)

def wait_until_stable(p: Path, min_age: float = 0.75, checks: int = 3, interval: float = 0.25, timeout: float = 10.0) -> bool:
    """
    Wait until file is likely done writing:
      - has existed at least `min_age` seconds
      - size unchanged for `checks` consecutive intervals
      - can be opened for reading (not locked)
    """
    start = time.time()
    last_size = -1
    stable_count = 0

    # Ensure minimum age first
    while time.time() - start < min_age:
        if not p.exists():
            return False
        time.sleep(0.05)

    while time.time() - start < timeout:
        if not p.exists():
            return False
        try:
            size = p.stat().st_size
        except Exception:
            size = -1
        if size > 0 and size == last_size:
            stable_count += 1
        else:
            stable_count = 0
        last_size = size

        # Try opening to ensure not locked
        try:
            with p.open("rb"):
                pass
            if stable_count >= checks:
                return True
        except Exception:
            pass

        time.sleep(interval)
    return False

class PhotoHandler(FileSystemEventHandler):
    def _process_path(self, path_str: str):
        src = Path(path_str)
        if not src.exists():
            return
        if is_temporary_name(src.name):
            return
        if not is_media(src):
            return

        # Wait until the tether app has finished writing/renaming
        if not wait_until_stable(src, min_age=RENAME_DELAY, checks=3, interval=0.25, timeout=15.0):
            print(f"[PhotoLogger] Skipped (not stable): {src}")
            return

        with state_lock:
            id_prefix = current_count

        ext = src.suffix.lower()
        seq = get_and_bump_seq_for_id(id_prefix)
        new_name = f"{id_prefix}_{seq}{ext}"
        dst = Path(OUTPUT_DIR) / new_name

        try:
            # Try to move; if locked, retry briefly, then copy+delete
            for _ in range(15):
                try:
                    src.rename(dst)
                    break
                except PermissionError:
                    time.sleep(0.2)
            else:
                data = src.read_bytes()
                dst.write_bytes(data)
                try:
                    src.unlink()
                except Exception:
                    pass
            print(f"[PhotoLogger] Renamed: {src.name} -> {dst.name}")
        except Exception as e:
            print(f"[PhotoLogger] ERROR renaming {src}: {e}")

    def on_created(self, event):
        if event.is_directory:
            return
        self._process_path(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Many tether apps do temp-name → final-name via a move/rename
        self._process_path(event.dest_path)

observer = Observer()
observer.schedule(PhotoHandler(), INCOMING_DIR, recursive=True)
observer_thread = threading.Thread(target=observer.start, daemon=True)
observer_thread.start()

# --- Server info page (cosmetic only) ---
SERVER_PAGE = r'''<!doctype html>
<meta charset="utf-8"/>
<title>Photo Logger Server</title>
<style>
  body{font-family:system-ui;margin:2rem}
  code{background:#eee;padding:.2rem .4rem;border-radius:.3rem}
</style>
<h1>Photo Logger Server</h1>
<p>Server running. Open your display UI (<code>photologger.html</code>) on the second monitor, or keep using this process.</p>
<p>API:</p>
<ul>
  <li>GET <code>/api/state</code></li>
  <li>POST <code>/api/increment</code></li>
  <li>POST <code>/api/decrement</code></li>
  <li>POST <code>/api/set-count</code> <code>{"count": 42}</code></li>
</ul>
<p><b>Incoming:</b> {{INCOMING_DIR}}<br><b>Output:</b> {{OUTPUT_DIR}}</p>
'''.replace('{{INCOMING_DIR}}', INCOMING_DIR).replace('{{OUTPUT_DIR}}', OUTPUT_DIR)

@app.route('/')
def root():
    return Response(SERVER_PAGE, mimetype='text/html; charset=utf-8')

# --- API ---
@app.route('/api/state')
def api_state():
    with state_lock:
        return jsonify({
            "current_count": current_count,
            "incoming_dir": INCOMING_DIR,
            "output_dir": OUTPUT_DIR,
        })

@app.route('/api/increment', methods=['POST'])
def api_increment():
    global current_count
    with state_lock:
        current_count += 1
        save_state(current_count)
    return jsonify({"ok": True, "current_count": current_count})

@app.route('/api/decrement', methods=['POST'])
def api_decrement():
    global current_count
    with state_lock:
        current_count = max(1, current_count - 1)
        save_state(current_count)
    return jsonify({"ok": True, "current_count": current_count})

@app.route('/api/set-count', methods=['POST'])
def api_set_count():
    global current_count
    data = request.get_json(silent=True) or {}
    try:
        val = int(data.get("count", 1))
        if val < 1:
            val = 1
    except Exception:
        val = 1
    with state_lock:
        current_count = val
        save_state(current_count)
    return jsonify({"ok": True, "current_count": current_count})

# --- Launch: start server, then open the local HTML in Chrome ---
def main():
    print("[PhotoLogger] Watching:", INCOMING_DIR, "->", OUTPUT_DIR)
    threading.Timer(1.5, open_html_in_chrome).start()
    app.run(host="127.0.0.1", port=8000, debug=False)

if __name__ == "__main__":
    try:
        main()
    finally:
        observer.stop()
        observer.join()