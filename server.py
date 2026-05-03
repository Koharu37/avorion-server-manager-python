"""
Avorion Server Manager — Python Version
Flask + Flask-SocketIO backend
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO

# ─── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
PUBLIC_DIR = BASE_DIR / "public"

# ─── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "steamcmdPath": "C:\\steamcmd",
    "serverPath": "C:\\avorion-server",
    "galaxyName": "avorion_galaxy",
    "serverName": "My Avorion Server",
    "port": 27000,
    "maxPlayers": 10,
    "saveInterval": 300,
    "adminSteamId": "",
    "seed": "",
    "webPort": 3000,
}


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


config = load_config()

# ─── Server State ──────────────────────────────────────────────────────────────
server_process: subprocess.Popen | None = None
server_start_time: float | None = None
install_process: subprocess.Popen | None = None
console_buffer: deque = deque(maxlen=500)
state_lock = threading.Lock()

# ─── Flask + SocketIO ──────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")
app.config["SECRET_KEY"] = "avorion-server-manager"
socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins="*")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def push_log(text: str):
    entry = {"time": now_iso(), "text": text}
    console_buffer.append(entry)
    socketio.emit("log", entry)


def stream_output(proc: subprocess.Popen, prefix: str = ""):
    """Read stdout/stderr from a subprocess in background threads."""

    def _read(stream, tag):
        try:
            for raw_line in iter(stream.readline, b""):
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    push_log(f"{prefix}{tag}{line}")
        except Exception:
            pass

    threading.Thread(target=_read, args=(proc.stdout, ""), daemon=True).start()
    threading.Thread(target=_read, args=(proc.stderr, "[ERR] "), daemon=True).start()


# ─── INI Parser ────────────────────────────────────────────────────────────────
def parse_ini(text: str) -> dict:
    result: dict = {}
    current_section = "__global__"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        sec_match = re.match(r"^\[(.+)\]$", line)
        if sec_match:
            current_section = sec_match.group(1)
            result.setdefault(current_section, {})
            continue
        kv_match = re.match(r"^([^=]+)=(.*)$", line)
        if kv_match:
            result.setdefault(current_section, {})
            result[current_section][kv_match.group(1).strip()] = kv_match.group(2).strip()
    return result


def stringify_ini(obj: dict) -> str:
    lines = []
    for section, kvs in obj.items():
        if section == "__global__":
            for k, v in kvs.items():
                lines.append(f"{k}={v}")
        else:
            lines.append(f"\n[{section}]")
            for k, v in kvs.items():
                lines.append(f"{k}={v}")
    return "\n".join(lines) + "\n"


def get_server_ini_path() -> Path:
    galaxy_dir = (
        Path(os.environ.get("APPDATA", ""))
        / "Avorion"
        / "galaxies"
        / config.get("galaxyName", "avorion_galaxy")
    )
    return galaxy_dir / "server.ini"


# ─── Routes: Static ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(PUBLIC_DIR), "index.html")


# ─── Routes: Status ───────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    global server_process
    running = server_process is not None and server_process.poll() is None
    uptime = int(time.time() - server_start_time) if running and server_start_time else 0
    installing = install_process is not None and install_process.poll() is None
    return jsonify(
        {
            "running": running,
            "uptime": uptime,
            "pid": server_process.pid if running else None,
            "installing": installing,
        }
    )


@app.route("/api/console")
def api_console():
    return jsonify(list(console_buffer))


# ─── Routes: Settings (config.json) ───────────────────────────────────────────
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    global config
    config = load_config()
    return jsonify(config)


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    global config
    data = request.get_json(force=True)
    config.update(data)
    save_config(config)
    return jsonify({"ok": True})


# ─── Routes: Game Config (server.ini) ──────────────────────────────────────────
@app.route("/api/gameconfig", methods=["GET"])
def api_get_gameconfig():
    ini_path = get_server_ini_path()
    if not ini_path.exists():
        return jsonify({"exists": False, "data": {}})
    text = ini_path.read_text(encoding="utf-8")
    return jsonify({"exists": True, "data": parse_ini(text)})


@app.route("/api/gameconfig", methods=["POST"])
def api_save_gameconfig():
    ini_path = get_server_ini_path()
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    data = request.get_json(force=True)
    ini_path.write_text(stringify_ini(data), encoding="utf-8")
    return jsonify({"ok": True})


# ─── Routes: SteamCMD Install ─────────────────────────────────────────────────
@app.route("/api/install", methods=["POST"])
def api_install():
    global install_process
    if install_process is not None and install_process.poll() is None:
        return jsonify({"error": "Install already running"}), 409

    steamcmd_exe = Path(config["steamcmdPath"]) / "steamcmd.exe"
    if not steamcmd_exe.exists():
        return (
            jsonify(
                {
                    "error": f"steamcmd.exe not found at {steamcmd_exe}. "
                    "Please install SteamCMD first or update the path in Settings."
                }
            ),
            400,
        )

    push_log("=== SteamCMD: Starting server install/update ===")

    args = [
        str(steamcmd_exe),
        "+force_install_dir", config["serverPath"],
        "+login", "anonymous",
        "+app_update", "565060", "validate",
        "+quit",
    ]

    install_process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=config["steamcmdPath"],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    def _watch():
        global install_process
        stream_output(install_process, "[SteamCMD] ")
        install_process.wait()
        code = install_process.returncode
        push_log(f"=== SteamCMD: Finished (exit code {code}) ===")
        socketio.emit("installDone", {"code": code})
        install_process = None

    threading.Thread(target=_watch, daemon=True).start()
    return jsonify({"ok": True})


# ─── Routes: Start Server ─────────────────────────────────────────────────────
@app.route("/api/start", methods=["POST"])
def api_start():
    global server_process, server_start_time

    if server_process is not None and server_process.poll() is None:
        return jsonify({"error": "Server is already running"}), 409

    server_path = Path(config["serverPath"])
    exe_candidates = [
        server_path / "bin" / "AvorionServer.exe",
        server_path / "AvorionServer.exe",
    ]
    exe = None
    for c in exe_candidates:
        if c.exists():
            exe = c
            break

    if exe is None:
        return (
            jsonify(
                {"error": "AvorionServer.exe not found. Please install the server first via SteamCMD."}
            ),
            400,
        )

    args = [
        str(exe),
        "--galaxy-name", config["galaxyName"],
        "--server-name", config["serverName"],
        "--port", str(config["port"]),
        "--max-players", str(config["maxPlayers"]),
        "--save-interval", str(config["saveInterval"]),
    ]
    if config.get("adminSteamId"):
        args += ["--admin", config["adminSteamId"]]
    if config.get("seed"):
        args += ["--seed", config["seed"]]

    push_log("=== Starting Avorion Server ===")
    push_log(f"Executable: {exe}")
    push_log(f"Args: {' '.join(args[1:])}")

    try:
        server_process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(server_path),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        server_start_time = time.time()
    except Exception as e:
        push_log(f"[ERROR] Failed to start server: {e}")
        server_process = None
        server_start_time = None
        return jsonify({"error": str(e)}), 500

    def _watch():
        global server_process, server_start_time
        stream_output(server_process, "")
        server_process.wait()
        code = server_process.returncode
        push_log(f"=== Server stopped (exit code {code}) ===")
        socketio.emit("serverStopped", {"code": code})
        server_process = None
        server_start_time = None

    threading.Thread(target=_watch, daemon=True).start()
    socketio.emit("serverStarted", {})
    return jsonify({"ok": True})


# ─── Routes: Stop Server ──────────────────────────────────────────────────────
@app.route("/api/stop", methods=["POST"])
def api_stop():
    global server_process
    if server_process is None or server_process.poll() is not None:
        return jsonify({"error": "Server is not running"}), 409

    push_log("=== Stopping Avorion Server ===")

    def _graceful_stop():
        global server_process
        try:
            if server_process and server_process.stdin:
                server_process.stdin.write(b"/save\n")
                server_process.stdin.flush()
                time.sleep(3)
                server_process.stdin.write(b"/stop\n")
                server_process.stdin.flush()
        except Exception:
            pass
        # Wait up to 10s then force kill
        for _ in range(20):
            time.sleep(0.5)
            if server_process is None or server_process.poll() is not None:
                return
        if server_process and server_process.poll() is None:
            push_log("Force killing server process...")
            server_process.kill()

    threading.Thread(target=_graceful_stop, daemon=True).start()
    return jsonify({"ok": True})


# ─── Routes: Send Command ─────────────────────────────────────────────────────
@app.route("/api/command", methods=["POST"])
def api_command():
    if server_process is None or server_process.poll() is not None:
        return jsonify({"error": "Server is not running"}), 409

    data = request.get_json(force=True)
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "No command provided"}), 400

    push_log(f"> {command}")
    try:
        server_process.stdin.write((command + "\n").encode("utf-8"))
        server_process.stdin.flush()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── SocketIO Events ──────────────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    # Send existing buffer to new client
    for entry in console_buffer:
        socketio.emit("log", entry)


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = config.get("webPort", 3000)
    print()
    print("  +----------------------------------------------+")
    print("  |   Avorion Server Manager  (Python)            |")
    print(f"  |   http://localhost:{port}                      |")
    print("  +----------------------------------------------+")
    print()
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
