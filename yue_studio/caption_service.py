from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


MODEL_FILES = {
    "model": ("acestep-captioner-Q4_K_M.gguf", "1c6fb97c2599dc259af70bbfc89a65da24360ba55d7b982366ca32f7e2ae8786"),
    "projector": ("acestep-captioner-mmproj-Q8_0.gguf", "77f15ee6e123a85deb2e853ef08d791613e2350c3cd24e033e99e6bad027a8b8"),
}
PROMPT = "*Task* Describe this audio in detail"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def format_yue2_caption(raw: str, instrumental: bool = True) -> str:
    text = " ".join(raw.strip().replace("\n", " ").split()).strip(" ,.;")
    if not text:
        raise ValueError("The captioner did not return a description.")
    parts = [part.strip(" .") for part in text.split(",") if part.strip(" .")]
    normalized = ", ".join(parts).lower()
    if instrumental and "instrumental" not in normalized:
        normalized = "instrumental, no vocals, " + normalized
    return normalized[:1500].strip(" ,")


def instrumental_warning(caption: str) -> str | None:
    terms = ("vocal", "singing", "singer", "lyrics", "spoken word", "rap")
    checked = caption.lower().replace("no vocals", "")
    found = [term for term in terms if term in checked]
    return "This instrumental caption mentions: " + ", ".join(found) if found else None


class CaptionService:
    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.model_root = app_root / "models" / "captioner"
        self.engine_root = self.model_root / "engine"
        self._server: subprocess.Popen | None = None
        self._hash_cache: dict[str, tuple[int, int, bool]] = {}
        self.port = 9766

    def _model_path(self, key: str) -> Path:
        return self.model_root / MODEL_FILES[key][0]

    def status(self) -> dict:
        files = []
        for key, (name, expected) in MODEL_FILES.items():
            path = self._model_path(key)
            valid = self._valid_model(key, path, expected)
            files.append({"name": name, "ready": valid, "path": str(path)})
        engine = self._engine_path()
        return {"ready": all(item["ready"] for item in files) and engine is not None, "models": files, "engine": str(engine) if engine else "", "message": "ACE-Step captioner is ready." if all(item["ready"] for item in files) and engine else "ACE-Step needs its local audio engine. Open Setup and choose Install Captioner."}

    def _valid_model(self, key: str, path: Path, expected: str) -> bool:
        if not path.is_file():
            return False
        stat = path.stat()
        cached = self._hash_cache.get(key)
        if cached and cached[:2] == (stat.st_size, stat.st_mtime_ns):
            return cached[2]
        valid = sha256_file(path) == expected
        self._hash_cache[key] = (stat.st_size, stat.st_mtime_ns, valid)
        return valid

    def _engine_path(self) -> Path | None:
        for candidate in (self.engine_root / "llama-server.exe", self.engine_root / "llama-mtmd-cli.exe"):
            if candidate.is_file():
                return candidate
        found = shutil.which("llama-server") or shutil.which("llama-server.exe")
        return Path(found) if found else None

    def _ensure_server(self) -> None:
        if self._server and self._server.poll() is None:
            return
        status = self.status()
        if not all(item["ready"] for item in status["models"]):
            raise ValueError("ACE-Step captioner files are missing. Run Setup first.")
        engine = self._engine_path()
        if not engine or engine.name.lower() != "llama-server.exe":
            raise ValueError("ACE-Step audio engine is not installed yet. Run Setup to install the compatible engine.")
        self._server = subprocess.Popen([str(engine), "-m", str(self._model_path("model")), "--mmproj", str(self._model_path("projector")), "-ngl", "99", "-c", "4096", "--port", str(self.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=1):
                    return
            except OSError:
                time.sleep(0.5)
        raise RuntimeError("ACE-Step audio engine did not start. Open Setup for details.")

    @staticmethod
    def _wav_bytes(track: Path) -> bytes:
        if track.suffix.lower() == ".wav":
            return track.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "caption-input.wav"
            result = subprocess.run(["ffmpeg", "-y", "-i", str(track), "-ar", "16000", "-ac", "1", str(wav)], capture_output=True, text=True, timeout=180, check=False)
            if result.returncode or not wav.is_file():
                raise RuntimeError("FFmpeg could not prepare this audio for captioning.")
            return wav.read_bytes()

    def generate(self, track_path: Path, instrumental: bool = True) -> dict:
        self._ensure_server()
        audio = base64.b64encode(self._wav_bytes(track_path)).decode("ascii")
        body = {"messages": [{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": audio, "format": "wav"}}, {"type": "text", "text": PROMPT}]}], "max_tokens": 400, "temperature": 0, "top_k": 1, "seed": 4242, "stream": False, "cache_prompt": False}
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            value = json.loads(response.read().decode("utf-8"))
        raw = str(value["choices"][0]["message"]["content"])
        caption = format_yue2_caption(raw, instrumental)
        return {"raw_caption": raw, "caption": caption, "warning": instrumental_warning(caption), "engine": "ACE-Step local"}
