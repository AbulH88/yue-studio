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
from setup_service import SetupService
from update_service import UpdateService
from caption_service import CaptionService


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
SETUP = SetupService(TRAINING, load_config, save_config)
CAPTIONS = CaptionService(ROOT)
UPDATES = UpdateService(
    ROOT,
    load_config,
    save_config,
    lambda: TRAINING.status().get("status") in {"queued", "validating", "staging", "preparing", "training", "stopping"}
    or bool(SETUP.status().get("active")),
)


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
    return scan_sources([{"type": "folder", "path": path_text}])


def normalize_sources(raw_sources: object) -> list[dict]:
    if not isinstance(raw_sources, list):
        raise ValueError("Dataset sources must be a list.")
    normalized = []
    seen = set()
    for source in raw_sources:
        if not isinstance(source, dict):
            raise ValueError("Each dataset source must include a type and path.")
        source_type = str(source.get("type", "")).lower()
        path_text = str(source.get("path", "")).strip()
        if source_type not in {"file", "folder"} or not path_text:
            raise ValueError("Each source must be a file or folder with a path.")
        path = Path(path_text).expanduser()
        if source_type == "file" and not path.is_file():
            raise ValueError(f"Selected file no longer exists: {path}")
        if source_type == "folder" and not path.is_dir():
            raise ValueError(f"Selected folder no longer exists: {path}")
        resolved = str(path.resolve())
        key = (source_type, resolved.casefold())
        if key not in seen:
            normalized.append({"type": source_type, "path": resolved})
            seen.add(key)
    return normalized


def scan_sources(raw_sources: object) -> list[dict]:
    sources = normalize_sources(raw_sources)
    tracks = []
    seen_files = set()
    for source in sources:
        root = Path(source["path"])
        candidates = [root] if source["type"] == "file" else sorted(root.rglob("*"))
        for audio in candidates:
            if not audio.is_file() or audio.suffix.lower() not in SUPPORTED:
                continue
            resolved = str(audio.resolve())
            if resolved.casefold() in seen_files:
                continue
            seen_files.add(resolved.casefold())
            caption_path = audio.with_suffix(".txt")
            tracks.append({
                "name": audio.name,
                "path": resolved,
                "caption_path": str(caption_path),
                "caption": caption_path.read_text(encoding="utf-8", errors="replace").strip() if caption_path.exists() else "",
                "duration": ffprobe_duration(audio),
                "has_caption": caption_path.exists(),
            })
    tracks.sort(key=lambda item: (item["name"].casefold(), item["path"].casefold()))
    return tracks


def dataset_sources(dataset: dict) -> list[dict]:
    sources = dataset.get("sources")
    if isinstance(sources, list):
        return sources
    path = str(dataset.get("path", "")).strip()
    return [{"type": "folder", "path": path}] if path else []


def choose_sources(kind: str) -> list[dict]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("Windows file picker is unavailable in this Python installation.") from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if kind == "folder":
            selected = filedialog.askdirectory(title="Choose a music folder", mustexist=True)
            return [{"type": "folder", "path": str(Path(selected).resolve())}] if selected else []
        if kind == "files":
            filetypes = [("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a"), ("All files", "*.*")]
            selected = filedialog.askopenfilenames(title="Choose audio tracks", filetypes=filetypes)
            return [{"type": "file", "path": str(Path(path).resolve())} for path in selected]
        raise ValueError("Unknown picker type.")
    finally:
        root.destroy()


def caption_fallback(track: dict, config: dict) -> str:
    trigger = config.get("trigger_word", "").strip()
    prefix = f"{trigger}, " if trigger else ""
    stem = Path(track["name"]).stem.replace("_", " ").replace("-", " ").strip()
    kind = "instrumental music" if config.get("instrumental", True) else "music"
    return f"{prefix}{kind}, inspired by {stem}, expressive instrumentation, balanced arrangement, clear production"


def authorized_track(path_text: str) -> dict:
    target = Path(path_text).resolve()
    for dataset in load_config().get("datasets", []):
        try:
            for track in scan_sources(dataset_sources(dataset)):
                if Path(track["path"]).resolve() == target:
                    return track
        except ValueError:
            continue
    raise ValueError("That track is not part of a linked dataset.")


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
            UPDATES.check_async()
            self.send_json(load_config())
            return
        if parsed.path == "/api/dataset":
            cfg = load_config()
            datasets = cfg.get("datasets", [])
            if not datasets and cfg.get("dataset_path"):
                datasets = [{"name": Path(cfg["dataset_path"]).name or "Dataset", "path": cfg["dataset_path"]}]
            result = []
            for dataset in datasets:
                sources = dataset_sources(dataset)
                try:
                    tracks = scan_sources(sources) if sources else []
                except ValueError:
                    tracks = []
                result.append({**dataset, "sources": sources, "tracks": tracks, "track_count": len(tracks)})
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
        if parsed.path == "/api/setup/status":
            self.send_json(SETUP.status())
            return
        if parsed.path == "/api/update/status":
            self.send_json(UPDATES.status())
            return
        if parsed.path == "/api/caption/status":
            self.send_json(CAPTIONS.status())
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
                if not name:
                    raise ValueError("Dataset name is required.")
                raw_sources = data.get("sources")
                if raw_sources is None:
                    path_text = str(data.get("path", "")).strip()
                    raw_sources = [{"type": "folder", "path": path_text}] if path_text else []
                sources = normalize_sources(raw_sources)
                tracks = scan_sources(sources)
                if not tracks:
                    raise ValueError("No supported audio files were found in the selected sources.")
                config = load_config()
                datasets = config.setdefault("datasets", [])
                existing = next((item for item in datasets if item.get("name") == name), None)
                entry = {"name": name, "sources": sources}
                if existing:
                    existing.update(entry)
                else:
                    datasets.append(entry)
                config["dataset_path"] = sources[0]["path"] if sources and sources[0]["type"] == "folder" else ""
                save_config(config)
                self.send_json({"ok": True, "dataset": {**entry, "tracks": tracks, "track_count": len(tracks)}})
                return
            if parsed.path == "/api/dataset/preview":
                sources = normalize_sources(data.get("sources", []))
                tracks = scan_sources(sources)
                self.send_json({"sources": sources, "tracks": tracks, "track_count": len(tracks)})
                return
            if parsed.path == "/api/picker/files":
                self.send_json({"sources": choose_sources("files")})
                return
            if parsed.path == "/api/picker/folder":
                self.send_json({"sources": choose_sources("folder")})
                return
            if parsed.path == "/api/caption":
                config = load_config()
                track = authorized_track(str(data.get("track_path", "")))
                self.send_json(CAPTIONS.generate(Path(track["path"]), bool(config.get("instrumental", True))))
                return
            if parsed.path == "/api/caption/install":
                self.send_json(CAPTIONS.install_engine())
                return
            if parsed.path == "/api/caption/save":
                track = authorized_track(str(data.get("track_path", "")))
                caption = str(data.get("caption", "")).strip()
                if not caption:
                    raise ValueError("Caption cannot be empty.")
                path = Path(track["caption_path"])
                if path.exists() and not bool(data.get("overwrite", False)):
                    raise ValueError("A caption already exists. Confirm replacement before overwriting it.")
                path.write_text(caption + "\n", encoding="utf-8")
                self.send_json({"ok": True, "caption_path": str(path)})
                return
            if parsed.path == "/api/training/settings":
                self.send_json(TRAINING.save_settings(data))
                return
            if parsed.path == "/api/setup/start":
                self.send_json(SETUP.start(), HTTPStatus.ACCEPTED)
                return
            if parsed.path == "/api/training/autodetect":
                detected = TRAINING.autodetect(str(data.get("wsl_distribution", "Ubuntu")))
                self.send_json(TRAINING.save_settings(detected))
                return
            if parsed.path == "/api/training/preflight":
                self.send_json(TRAINING.preflight(data or None))
                return
            if parsed.path == "/api/training/start":
                raw_sources = data.get("sources")
                if raw_sources is None:
                    dataset_path = str(data.get("dataset_path", ""))
                    raw_sources = [{"type": "folder", "path": dataset_path}] if dataset_path else []
                sources = normalize_sources(raw_sources)
                if not sources:
                    raise ValueError("Choose a dataset before starting training.")
                tracks = scan_sources(sources)
                request = {
                    **data,
                    "dataset_name": str(data.get("dataset_name") or "Dataset"),
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
