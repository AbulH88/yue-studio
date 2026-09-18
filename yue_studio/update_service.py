from __future__ import annotations

import hashlib
import json
import threading
import urllib.request
from pathlib import Path
from typing import Callable

from version import VERSION


def version_key(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.strip().lstrip("v").split("."))
    except ValueError as exc:
        raise ValueError("Release version must use numbers such as 0.1.0.") from exc


def validate_manifest(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Release manifest must be an object.")
    version = str(value.get("version", ""))
    url = str(value.get("url", ""))
    sha256 = str(value.get("sha256", "")).lower()
    version_key(version)
    if not url.startswith("https://"):
        raise ValueError("Release downloads must use HTTPS.")
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise ValueError("Release manifest needs a SHA-256 checksum.")
    return {"version": version, "url": url, "sha256": sha256}


class UpdateService:
    """Checks a published HTTPS manifest. Downloads are staged for the next launcher start."""

    def __init__(self, app_root: Path, config_loader: Callable[[], dict], config_saver: Callable[[dict], None], is_busy: Callable[[], bool]):
        self.app_root = app_root
        self.config_loader = config_loader
        self.config_saver = config_saver
        self.is_busy = is_busy
        self._thread: threading.Thread | None = None

    def status(self) -> dict:
        config = self.config_loader()
        update = config.get("update", {})
        return {"current_version": VERSION, "active": bool(self._thread and self._thread.is_alive()), **update}

    def check_async(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._check, daemon=True, name="yue-studio-update-check")
        self._thread.start()

    def _save(self, **changes) -> None:
        config = self.config_loader()
        config["update"] = {**config.get("update", {}), **changes}
        self.config_saver(config)

    def _check(self) -> None:
        try:
            manifest_url = str(self.config_loader().get("release_manifest_url", "")).strip()
            if not manifest_url:
                self._save(status="not_published", message="Automatic updates will start with the first published release.")
                return
            if not manifest_url.startswith("https://"):
                raise ValueError("Update source must use HTTPS.")
            with urllib.request.urlopen(manifest_url, timeout=15) as response:
                manifest = validate_manifest(json.loads(response.read().decode("utf-8")))
            if version_key(manifest["version"]) <= version_key(VERSION):
                self._save(status="current", message="YuE Studio is up to date.", available=None)
                return
            self._save(status="available", message=f"Version {manifest['version']} is downloading safely in the background.", available=manifest)
            self._download(manifest)
        except Exception as exc:
            self._save(status="check_failed", message=f"Update check skipped: {exc}")

    def _download(self, manifest: dict) -> None:
        if self.is_busy():
            self._save(status="deferred", message="Update postponed until training and setup finish.")
            return
        updates = self.app_root / ".updates"
        updates.mkdir(exist_ok=True)
        archive = updates / f"YuE-Studio-{manifest['version']}.zip.part"
        final = archive.with_suffix("")
        with urllib.request.urlopen(manifest["url"], timeout=60) as response, archive.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != manifest["sha256"]:
            archive.unlink(missing_ok=True)
            raise ValueError("Downloaded update did not pass its security check.")
        archive.replace(final)
        (updates / "pending-update.json").write_text(json.dumps({**manifest, "archive": str(final)}, indent=2), encoding="utf-8")
        self._save(status="ready_to_apply", message="Update downloaded. It will install automatically the next time YuE Studio opens.")
