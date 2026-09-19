from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable


DEFAULT_TRAINING_SETTINGS = {
    "wsl_distribution": "Ubuntu",
    "wsl_python": "",
    "trainer_path": "",
    "yue2_model_path": "",
    "mert_path": "",
    "vae_path": "",
    "tokenizer_head_path": "",
    "runs_root": "/workspace/yue-studio-runs",
    "minimum_free_gb": 20,
}

RUN_NAME_RE = re.compile(r"[^a-z0-9_-]+")
STEP_RE = re.compile(r"step\s+(\d+)\s+loss\s+([0-9.]+).*?([0-9.]+)s\s+mem\s+([0-9.]+)G", re.I)
EVAL_RE = re.compile(r"EVAL\s+step\s+(\d+)\s+minted_val\s+([0-9.]+)\s+artist\s+([0-9.]+)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_run_name(value: str) -> str:
    cleaned = RUN_NAME_RE.sub("-", value.strip().lower()).strip("-_")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned[:48] or "instrumental-lora"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_training_line(line: str) -> dict:
    step = STEP_RE.search(line)
    if step:
        return {
            "step": int(step.group(1)),
            "loss": float(step.group(2)),
            "elapsed_seconds": float(step.group(3)),
            "vram_gb": float(step.group(4)),
        }
    evaluation = EVAL_RE.search(line)
    if evaluation:
        return {
            "step": int(evaluation.group(1)),
            "validation_loss": float(evaluation.group(2)),
            "artist_loss": float(evaluation.group(3)),
        }
    return {}


def training_values(request: dict) -> dict:
    """Validate the controls exposed in the Training Configuration panel."""
    try:
        steps = int(request.get("steps", 1000))
        rank = int(request.get("rank", 64))
        learning_rate = float(request.get("learning_rate", 6e-5))
        checkpoint_every = int(request.get("checkpoint_every", min(200, steps)))
        seed = int(request.get("seed", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Training controls must contain valid numeric values.") from exc
    if not 1 <= steps <= 100000:
        raise ValueError("Training steps must be between 1 and 100,000.")
    if not 8 <= rank <= 256 or rank % 8:
        raise ValueError("LoRA rank must be a multiple of 8 between 8 and 256.")
    if not 1e-7 <= learning_rate <= 1e-3:
        raise ValueError("Learning rate must be between 1e-7 and 1e-3.")
    if not 1 <= checkpoint_every <= steps:
        raise ValueError("Checkpoint interval must be between 1 and the training step count.")
    if not 0 <= seed <= 2_147_483_647:
        raise ValueError("Seed must be between 0 and 2,147,483,647.")
    return {
        "steps": steps,
        "rank": rank,
        "learning_rate": learning_rate,
        "checkpoint_every": checkpoint_every,
        "seed": seed,
    }


class TrainingBridge:
    def __init__(self, app_root: Path, config_loader: Callable[[], dict], config_saver: Callable[[dict], None]):
        self.app_root = app_root
        self.config_loader = config_loader
        self.config_saver = config_saver
        self._lock = threading.Lock()
        self._active: dict | None = None
        self._process: subprocess.Popen | None = None
        self._stop_requested = False

    def settings(self) -> dict:
        config = self.config_loader()
        return {**DEFAULT_TRAINING_SETTINGS, **config.get("training", {})}

    def save_settings(self, values: dict) -> dict:
        allowed = set(DEFAULT_TRAINING_SETTINGS)
        settings = self.settings()
        for key in allowed:
            if key in values:
                settings[key] = values[key]
        settings["minimum_free_gb"] = max(1, int(settings.get("minimum_free_gb", 20)))
        config = self.config_loader()
        config["training"] = settings
        self.config_saver(config)
        return settings

    @staticmethod
    def _wsl_prefix(settings: dict) -> list[str]:
        distro = str(settings.get("wsl_distribution", "")).strip()
        if not distro:
            raise ValueError("Choose a WSL distribution first.")
        return ["wsl.exe", "--distribution", distro, "--"]

    def _run_wsl(self, settings: dict, args: list[str], timeout: int = 20, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            self._wsl_prefix(settings) + args,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def windows_to_wsl(self, settings: dict, path: Path) -> str:
        resolved = path.resolve()
        # Passing a Windows path through WSL's argument parser can consume its
        # backslashes. Translate mounted drive paths directly instead.
        if resolved.drive:
            relative = resolved.as_posix().split(":/", 1)[-1]
            candidate = f"/mnt/{resolved.drive[0].lower()}/{relative}"
            accessible = self._run_wsl(settings, ["test", "-e", candidate])
            if accessible.returncode == 0:
                return candidate
        result = self._run_wsl(settings, ["wslpath", "-a", str(resolved)])
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError(f"WSL could not access this Windows path: {path}")
        return result.stdout.strip()

    def autodetect(self, distro: str = "Ubuntu") -> dict:
        settings = {**DEFAULT_TRAINING_SETTINGS, "wsl_distribution": distro or "Ubuntu"}
        try:
            who = self._run_wsl(settings, ["whoami"])
            if who.returncode != 0:
                return settings
            user = who.stdout.strip()
            home = f"/home/{user}"
            candidates = {
                "wsl_python": [f"{home}/yue2-venv/bin/python", "/usr/bin/python3"],
                "yue2_model_path": [f"{home}/yue2-raw"],
                "mert_path": [f"{home}/mert-fullsong"],
                "vae_path": [f"{home}/yue2-base-vae"],
                "tokenizer_head_path": [
                    f"{home}/yue2-work/tok/full/tokenizer_head_joint_v4.pt",
                    f"{home}/yue2-work/tok/full/tokenizer_head_joint_v5.safetensors",
                ],
            }
            for key, paths in candidates.items():
                for candidate in paths:
                    check = self._run_wsl(settings, ["test", "-e", candidate])
                    if check.returncode == 0:
                        settings[key] = candidate
                        break
            settings["runs_root"] = "/workspace/yue-studio-runs"
        except (OSError, subprocess.TimeoutExpired):
            pass
        return settings

    def preflight(self, override: dict | None = None) -> dict:
        settings = {**self.settings(), **(override or {})}
        checks: list[dict] = []

        def add(name: str, ok: bool, message: str):
            checks.append({"name": name, "ok": ok, "message": message})

        try:
            listed = subprocess.run(["wsl.exe", "--list", "--quiet"], capture_output=True, text=True, timeout=10, check=False)
            normalized = listed.stdout.replace("\x00", "")
            distro = str(settings.get("wsl_distribution", "")).strip()
            add("WSL distribution", listed.returncode == 0 and distro.lower() in normalized.lower(), distro or "No distribution selected")
            if not checks[-1]["ok"]:
                return {"ok": False, "checks": checks}
        except (OSError, subprocess.TimeoutExpired) as exc:
            add("WSL", False, f"WSL is unavailable: {exc}")
            return {"ok": False, "checks": checks}

        python = str(settings.get("wsl_python", "")).strip()
        py = self._run_wsl(settings, [python, "--version"]) if python else None
        add("Python", bool(py and py.returncode == 0), (py.stdout or py.stderr).strip() if py else "Choose the YuE2 Python executable.")

        if py and py.returncode == 0:
            cuda = self._run_wsl(settings, [python, "-c", "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no GPU')"], timeout=30)
            lines = [line.strip() for line in cuda.stdout.splitlines() if line.strip()]
            ok = cuda.returncode == 0 and "True" in lines
            add("CUDA", ok, " · ".join(lines) if lines else (cuda.stderr.strip() or "PyTorch/CUDA check failed."))
            packages = self._run_wsl(settings, [python, "-c", "import numpy,scipy,soundfile,transformers,safetensors,yue2; print('YuE2 training packages available')"], timeout=30)
            add("Python packages", packages.returncode == 0, packages.stdout.strip() or packages.stderr.strip() or "Required packages are missing.")

        ffmpeg = self._run_wsl(settings, ["ffmpeg", "-version"])
        add("FFmpeg", ffmpeg.returncode == 0, ffmpeg.stdout.splitlines()[0] if ffmpeg.stdout else (ffmpeg.stderr.strip() or "Install FFmpeg inside WSL."))

        path_checks = [
            ("YuE2 model", "yue2_model_path", "-d"),
            ("MERT model", "mert_path", "-d"),
            ("YuE2 VAE", "vae_path", "-d"),
            ("Tokenizer head", "tokenizer_head_path", "-f"),
        ]
        for label, key, flag in path_checks:
            value = str(settings.get(key, "")).strip()
            result = self._run_wsl(settings, ["test", flag, value]) if value else None
            add(label, bool(result and result.returncode == 0), value or f"Choose the {label.lower()} path.")
        model_path = str(settings.get("yue2_model_path", "")).strip()
        tokenizer_file = f"{model_path.rstrip('/')}/qwen.tiktoken" if model_path else ""
        tokenizer = self._run_wsl(settings, ["test", "-f", tokenizer_file]) if tokenizer_file else None
        add("YuE2 tokenizer", bool(tokenizer and tokenizer.returncode == 0), tokenizer_file or "The YuE2 model path is not set.")

        runs_root = str(settings.get("runs_root", "")).strip()
        if runs_root and PurePosixPath(runs_root).is_absolute():
            mkdir = self._run_wsl(settings, ["mkdir", "-p", runs_root])
            writable = self._run_wsl(settings, ["test", "-w", runs_root]) if mkdir.returncode == 0 else mkdir
            add("Run workspace", writable.returncode == 0, runs_root if writable.returncode == 0 else (writable.stderr.strip() or "Workspace is not writable."))
            disk = self._run_wsl(settings, ["df", "-Pk", runs_root])
            try:
                free_kb = int(disk.stdout.splitlines()[-1].split()[3])
                free_gb = free_kb / 1024 / 1024
                minimum = float(settings.get("minimum_free_gb", 20))
                add("Free disk space", free_gb >= minimum, f"{free_gb:.1f} GB free; {minimum:.0f} GB required")
            except (IndexError, ValueError):
                add("Free disk space", False, disk.stderr.strip() or "Could not read free disk space.")
        else:
            add("Run workspace", False, "Enter an absolute Linux path such as /workspace/yue-studio-runs.")

        runner = self.app_root / "wsl" / "run_instrumental.py"
        add("YuE Studio runner", runner.is_file(), str(runner))
        return {"ok": all(item["ok"] for item in checks), "checks": checks, "settings": settings}

    def _write_linux_json(self, settings: dict, linux_path: str, value: dict) -> None:
        code = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding='utf-8')"
        result = self._run_wsl(settings, [str(settings["wsl_python"]), "-c", code, linux_path], input_text=json.dumps(value, indent=2))
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Could not write the run manifest in WSL.")

    def start(self, request: dict, tracks: list[dict]) -> dict:
        settings = self.settings()
        with self._lock:
            if self._active and self._active.get("status") in {"validating", "staging", "preparing", "training", "stopping"}:
                raise ValueError("Another training run is already active.")

        controls = training_values(request)
        steps = controls["steps"]
        rank = controls["rank"]
        if not tracks:
            raise ValueError("The selected dataset has no supported audio tracks.")
        missing = [track["name"] for track in tracks if not track.get("has_caption") or not str(track.get("caption", "")).strip()]
        if missing:
            raise ValueError("Every track needs a non-empty caption. Missing: " + ", ".join(missing[:8]))

        preflight = self.preflight()
        if not preflight["ok"]:
            failed = next(item for item in preflight["checks"] if not item["ok"])
            raise ValueError(f"Setup check failed: {failed['name']} — {failed['message']}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = safe_run_name(str(request.get("name") or request.get("dataset_name") or "instrumental-lora"))
        run_id = f"{base_name}-{timestamp}"
        runs_root = str(settings["runs_root"]).rstrip("/")
        run_dir = f"{runs_root}/{run_id}"
        exists = self._run_wsl(settings, ["test", "-e", run_dir])
        if exists.returncode == 0:
            raise ValueError(f"Run directory already exists: {run_dir}")
        made = self._run_wsl(settings, ["mkdir", "-p", f"{run_dir}/source", f"{run_dir}/prep", f"{run_dir}/ar", f"{run_dir}/checkpoints", f"{run_dir}/logs"])
        if made.returncode != 0:
            raise RuntimeError(made.stderr.strip() or "Could not create the run workspace.")

        runner_path = self.windows_to_wsl(settings, self.app_root / "wsl" / "run_instrumental.py")
        source_files = []
        seen = set()
        for index, track in enumerate(tracks, 1):
            audio = Path(track["path"])
            if not audio.is_file():
                raise ValueError(f"Audio file is missing: {audio}")
            slug = safe_run_name(audio.stem) or f"track-{index:03d}"
            slug = f"{index:03d}-{slug}"
            if slug in seen:
                raise ValueError(f"Duplicate normalized track name: {audio.name}")
            seen.add(slug)
            source_files.append({
                "name": slug,
                "original_name": audio.name,
                "windows_path": str(audio.resolve()),
                "wsl_path": self.windows_to_wsl(settings, audio),
                "size": audio.stat().st_size,
                "caption": str(track["caption"]).strip(),
            })

        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "status": "queued",
            "stage": "queued",
            "instrumental": True,
            "dataset": {"name": request.get("dataset_name", "Dataset"), "files": source_files},
            "training": {
                "steps": steps,
                "rank": rank,
                "learning_rate": controls["learning_rate"],
                "artist_fraction": 1.0,
                "cursor_loss_weight": 0.08,
                "gradient_accumulation": 2,
                "checkpoint_every": controls["checkpoint_every"],
                "seed": controls["seed"],
            },
            "paths": {
                "run_dir": run_dir,
                "python": settings["wsl_python"],
                "yue2_model": settings["yue2_model_path"],
                "mert": settings["mert_path"],
                "vae": settings["vae_path"],
                "tokenizer_head": settings["tokenizer_head_path"],
                "runner": runner_path,
            },
            "commands": {
                "runner": [settings["wsl_python"], runner_path, "--manifest", f"{run_dir}/manifest.json"]
            },
            "script_sha256": file_sha256(self.app_root / "wsl" / "run_instrumental.py"),
        }
        self._write_linux_json(settings, f"{run_dir}/manifest.json", manifest)

        state = {
            "run_id": run_id,
            "run_dir": run_dir,
            "status": "queued",
            "stage": "queued",
            "steps": steps,
            "step": 0,
            "logs": [],
            "checkpoints": [],
            "started_at": utc_now(),
            "error": None,
        }
        with self._lock:
            self._active = state
            self._stop_requested = False
        thread = threading.Thread(target=self._run_worker, args=(settings, manifest), daemon=True)
        thread.start()
        return self.status()

    def _record_line(self, line: str) -> None:
        line = line.rstrip()
        if not line:
            return
        with self._lock:
            if not self._active:
                return
            self._active["logs"].append(line)
            self._active["logs"] = self._active["logs"][-1000:]
            if line.startswith("STAGE "):
                self._active["stage"] = line.split(" ", 1)[1].strip().lower()
                self._active["status"] = self._active["stage"]
            if line.startswith("CHECKPOINT "):
                name = line.split(" ", 1)[1].strip()
                if name and not any(item.get("name") == name for item in self._active["checkpoints"]):
                    self._active["checkpoints"].append({"name": name})
            self._active.update(parse_training_line(line))

    def _run_worker(self, settings: dict, manifest: dict) -> None:
        run_dir = manifest["paths"]["run_dir"]
        command = manifest["commands"]["runner"]
        log_path = f"{run_dir}/logs/runner.log"
        try:
            self._record_line("STAGE staging")
            process = subprocess.Popen(
                self._wsl_prefix(settings) + command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with self._lock:
                self._process = process
            assert process.stdout is not None
            captured = []
            for line in process.stdout:
                captured.append(line)
                self._record_line(line)
            code = process.wait()
            self._write_linux_text(settings, log_path, "".join(captured))
            with self._lock:
                if not self._active:
                    return
                if self._stop_requested:
                    self._active["status"] = "stopped"
                    self._active["stage"] = "stopped"
                elif code == 0:
                    self._active["status"] = "completed"
                    self._active["stage"] = "completed"
                else:
                    self._active["status"] = "failed"
                    self._active["stage"] = "failed"
                    self._active["error"] = f"Runner exited with code {code}."
        except Exception as exc:  # background boundary: retain the error for the UI
            with self._lock:
                if self._active:
                    self._active["status"] = "failed"
                    self._active["stage"] = "failed"
                    self._active["error"] = str(exc)
                    self._active["logs"].append(f"ERROR {exc}")
        finally:
            checkpoints = self._list_checkpoints(settings, f"{run_dir}/checkpoints")
            with self._lock:
                if self._active:
                    self._active["checkpoints"] = checkpoints
                    self._active["finished_at"] = utc_now()
                self._process = None

    def _write_linux_text(self, settings: dict, path: str, value: str) -> None:
        code = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding='utf-8')"
        self._run_wsl(settings, [str(settings["wsl_python"]), "-c", code, path], input_text=value, timeout=60)

    def _update_linux_manifest(self, settings: dict, path: str, changes: dict) -> None:
        code = (
            "import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            "v=json.loads(p.read_text(encoding='utf-8')); v.update(json.loads(sys.stdin.read())); "
            "p.write_text(json.dumps(v,indent=2),encoding='utf-8')"
        )
        self._run_wsl(settings, [str(settings["wsl_python"]), "-c", code, path], input_text=json.dumps(changes), timeout=30)

    def _list_checkpoints(self, settings: dict, directory: str) -> list[dict]:
        code = "import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(json.dumps([{'name':x.name,'size':x.stat().st_size} for x in sorted(p.glob('*.pt'))]))"
        result = self._run_wsl(settings, [str(settings["wsl_python"]), "-c", code, directory])
        try:
            return json.loads(result.stdout) if result.returncode == 0 else []
        except json.JSONDecodeError:
            return []

    def status(self) -> dict:
        with self._lock:
            if not self._active:
                return {"status": "idle", "stage": "idle", "logs": [], "checkpoints": []}
            return json.loads(json.dumps(self._active))

    def checkpoint_files(self) -> dict:
        """Read current checkpoints, surviving a Studio restart."""
        with self._lock:
            active = json.loads(json.dumps(self._active)) if self._active else None
        if not active:
            runs = self.list_runs()
            if not runs:
                return {"run_id": "", "checkpoints": []}
            active = runs[0]
        files = self._list_checkpoints(self.settings(), f"{active['run_dir']}/checkpoints")
        return {"run_id": active["run_id"], "checkpoints": files}

    def export_checkpoints(self, run_id: str, checkpoint_names: list[str], destination: str) -> dict:
        """Create portable adapter folders for the bundled ComfyUI loader."""
        if not re.fullmatch(r"[a-z0-9_-]+", run_id) or not checkpoint_names:
            raise ValueError("Choose at least one valid checkpoint.")
        target = Path(destination).expanduser().resolve()
        if not target.is_dir():
            raise ValueError("Choose an existing export folder.")
        settings = self.settings()
        run_dir = f"{str(settings['runs_root']).rstrip('/')}/{run_id}"
        exporter = self.windows_to_wsl(settings, self.app_root / "wsl" / "export_comfy_lora.py")
        target_wsl = self.windows_to_wsl(settings, target)
        exported = []
        for name in checkpoint_names:
            if not re.fullmatch(r"(?:best|last|step-\d+)\.pt", str(name)):
                raise ValueError("Invalid checkpoint name.")
            if self._run_wsl(settings, ["test", "-f", f"{run_dir}/checkpoints/{name}"]).returncode:
                raise ValueError(f"Checkpoint not found: {name}")
            folder = f"{safe_run_name(run_id)}-{Path(name).stem}"
            result = self._run_wsl(settings, [str(settings["wsl_python"]), exporter, "--checkpoint", f"{run_dir}/checkpoints/{name}", "--destination", f"{target_wsl}/{folder}"], timeout=300)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or f"Could not export {name}.")
            exported.append(str(target / folder))
        return {"ok": True, "exported": exported}

    def resume(self, run_id: str, checkpoint_name: str) -> dict:
        """Resume a persisted run from one of its checkpoint files."""
        if not re.fullmatch(r"[a-z0-9_-]+", run_id):
            raise ValueError("Invalid run identifier.")
        if not re.fullmatch(r"(?:best|last|step-\d+)\.pt", checkpoint_name):
            raise ValueError("Invalid checkpoint name.")
        settings = self.settings()
        run_dir = f"{str(settings['runs_root']).rstrip('/')}/{run_id}"
        manifest_path = f"{run_dir}/manifest.json"
        code = "import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))"
        result = self._run_wsl(settings, [str(settings["wsl_python"]), "-c", code, manifest_path])
        if result.returncode:
            raise ValueError("Saved run was not found.")
        try:
            manifest = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("Saved run manifest is unreadable.") from exc
        if self._run_wsl(settings, ["test", "-f", f"{run_dir}/checkpoints/{checkpoint_name}"]).returncode:
            raise ValueError("That checkpoint file was not found.")
        with self._lock:
            if self._active and self._active.get("status") in {"queued", "staging", "preparing", "training", "stopping"}:
                raise ValueError("Another training run is already active.")
        manifest.setdefault("training", {})["resume_checkpoint"] = checkpoint_name
        self._update_linux_manifest(settings, manifest_path, {"status": "queued", "stage": "queued", "error": None, "training": manifest["training"]})
        state = {"run_id": run_id, "run_dir": run_dir, "status": "queued", "stage": "queued", "steps": int(manifest["training"]["steps"]), "step": 0, "logs": [f"Resuming from {checkpoint_name}"], "checkpoints": self._list_checkpoints(settings, f"{run_dir}/checkpoints"), "started_at": utc_now(), "error": None}
        with self._lock:
            self._active = state
            self._stop_requested = False
        threading.Thread(target=self._run_worker, args=(settings, manifest), daemon=True).start()
        return self.status()

    def list_runs(self) -> list[dict]:
        settings = self.settings()
        root = str(settings.get("runs_root", "")).strip()
        python = str(settings.get("wsl_python", "")).strip()
        if not root or not python:
            return []
        code = (
            "import json,pathlib,sys; out=[]; root=pathlib.Path(sys.argv[1]); "
            "files=sorted(root.glob('*/manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True); "
            "[(lambda v,p: out.append({'run_id':v.get('run_id',p.parent.name),'status':v.get('status','unknown'),"
            "'stage':v.get('stage','unknown'),'created_at':v.get('created_at'),'run_dir':str(p.parent)}))(json.loads(p.read_text(encoding='utf-8')),p) for p in files[:50]]; "
            "print(json.dumps(out))"
        )
        result = self._run_wsl(settings, [python, "-c", code, root])
        try:
            return json.loads(result.stdout) if result.returncode == 0 else []
        except json.JSONDecodeError:
            return []

    def stop(self) -> dict:
        with self._lock:
            process = self._process
            if not self._active or not process or process.poll() is not None:
                raise ValueError("There is no active training process to stop.")
            self._stop_requested = True
            self._active["status"] = "stopping"
            self._active["stage"] = "stopping"
            manifest_path = f"{self._active['run_dir']}/manifest.json"
            process.terminate()
        self._update_linux_manifest(self.settings(), manifest_path, {"status": "stopped", "stage": "stopped", "updated_at": utc_now()})
        return self.status()
