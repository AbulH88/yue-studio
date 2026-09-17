from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from training_bridge import TrainingBridge


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
CONFIG_PATH = ROOT / "studio.config.json"
SUPPORTED = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "project_name": "Untitled Music Project",
        "project_type": "General Music",
        "trigger_word": "",
        "caption_engine": "local-ace-step",
        "dataset_path": "",
        "export_path": "./exports",
        "instrumental": True,
        "datasets": [],
    }


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


TRAINING = TrainingBridge(ROOT, load_config, save_config)


def ffprobe_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return round(float(result.stdout.strip()), 2) if result.stdout.strip() else None
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        return None


def scan_dataset(path_text: str) -> list[dict]:
    path = Path(path_text).expanduser()
    if not path.is_dir():
        return []
    tracks = []
    for audio in sorted(path.rglob("*")):
        if audio.is_file() and audio.suffix.lower() in SUPPORTED:
            caption_path = audio.with_suffix(".txt")
            tracks.append({
                "name": audio.name,
                "path": str(audio),
                "caption_path": str(caption_path),
                "caption": caption_path.read_text(encoding="utf-8", errors="replace").strip() if caption_path.exists() else "",
                "duration": ffprobe_duration(audio),
                "has_caption": caption_path.exists(),
            })
    return tracks


def caption_fallback(track: dict, config: dict) -> str:
    trigger = config.get("trigger_word", "").strip()
    prefix = f"{trigger}, " if trigger else ""
    stem = Path(track["name"]).stem.replace("_", " ").replace("-", " ").strip()
    kind = "instrumental music" if config.get("instrumental", True) else "music"
    return f"{prefix}{kind}, inspired by {stem}, expressive instrumentation, balanced arrangement, clear production"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, value: object, status: int = 200):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(load_config())
            return
        if parsed.path == "/api/dataset":
            cfg = load_config()
            datasets = cfg.get("datasets", [])
            if not datasets and cfg.get("dataset_path"):
                datasets = [{"name": Path(cfg["dataset_path"]).name or "Dataset", "path": cfg["dataset_path"]}]
            result = []
            for dataset in datasets:
                tracks = scan_dataset(dataset.get("path", ""))
                result.append({**dataset, "tracks": tracks, "track_count": len(tracks)})
            self.send_json({"datasets": result})
            return
        if parsed.path == "/api/training/settings":
            self.send_json(TRAINING.settings())
            return
        if parsed.path == "/api/training/status":
            self.send_json(TRAINING.status())
            return
        if parsed.path == "/api/training/runs":
            self.send_json({"runs": TRAINING.list_runs()})
            return
        if parsed.path.startswith("/static/"):
            file_path = STATIC / parsed.path.removeprefix("/static/")
        else:
            file_path = STATIC / "index.html"
        if not file_path.is_file() or STATIC not in file_path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            if parsed.path == "/api/config":
                config = load_config()
                config.update(data)
                save_config(config)
                self.send_json(config)
                return
            if parsed.path == "/api/dataset":
                name = str(data.get("name", "")).strip()
                path_text = str(data.get("path", "")).strip()
                path = Path(path_text).expanduser()
                if not name:
                    raise ValueError("Dataset name is required.")
                if not path.is_dir():
                    raise ValueError("The selected dataset folder does not exist.")
                tracks = scan_dataset(str(path))
                if not tracks:
                    raise ValueError("No supported audio files were found in that folder.")
                config = load_config()
                datasets = config.setdefault("datasets", [])
                existing = next((item for item in datasets if item.get("name") == name), None)
                entry = {"name": name, "path": str(path.resolve())}
                if existing:
                    existing.update(entry)
                else:
                    datasets.append(entry)
                config["dataset_path"] = str(path.resolve())
                save_config(config)
                self.send_json({"ok": True, "dataset": {**entry, "tracks": tracks, "track_count": len(tracks)}})
                return
            if parsed.path == "/api/caption":
                config = load_config()
                track = data["track"]
                caption = caption_fallback(track, config)
                self.send_json({"caption": caption, "engine": "template-fallback"})
                return
            if parsed.path == "/api/caption/save":
                path = Path(data["caption_path"])
                path.write_text(data.get("caption", "").strip() + "\n", encoding="utf-8")
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/training/settings":
                self.send_json(TRAINING.save_settings(data))
                return
            if parsed.path == "/api/training/autodetect":
                detected = TRAINING.autodetect(str(data.get("wsl_distribution", "Ubuntu")))
                self.send_json(TRAINING.save_settings(detected))
                return
            if parsed.path == "/api/training/preflight":
                self.send_json(TRAINING.preflight(data or None))
                return
            if parsed.path == "/api/training/start":
                dataset_path = str(data.get("dataset_path", ""))
                if not dataset_path:
                    raise ValueError("Choose a dataset before starting training.")
                tracks = scan_dataset(dataset_path)
                request = {
                    **data,
                    "dataset_name": str(data.get("dataset_name") or Path(dataset_path).name or "Dataset"),
                }
                self.send_json(TRAINING.start(request, tracks), HTTPStatus.ACCEPTED)
                return
            if parsed.path == "/api/training/stop":
                self.send_json(TRAINING.stop())
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main():
    port = int(os.environ.get("YUE_STUDIO_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"YuE Studio running at {url}")
    if os.environ.get("YUE_STUDIO_NO_BROWSER") != "1":
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
