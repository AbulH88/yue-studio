from __future__ import annotations

import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MODEL_ROOT_TEMPLATE = "/home/{user}/.local/share/yue-studio/models"
REQUIRED_DISK_GB = 18


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SetupService:
    """Guided, resumable WSL preparation without storing credentials in the app."""

    def __init__(self, bridge, config_loader: Callable[[], dict], config_saver: Callable[[dict], None]):
        self.bridge = bridge
        self.config_loader = config_loader
        self.config_saver = config_saver
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def _state(self) -> dict:
        config = self.config_loader()
        return {
            "stage": "idle",
            "message": "YuE Studio has not been set up yet.",
            "logs": [],
            "updated_at": now(),
            **config.get("setup", {}),
        }

    def _save_state(self, **changes) -> dict:
        config = self.config_loader()
        state = {**self._state(), **changes, "updated_at": now()}
        state["logs"] = state.get("logs", [])[-120:]
        config["setup"] = state
        self.config_saver(config)
        return state

    def _log(self, message: str) -> None:
        state = self._state()
        self._save_state(logs=[*state.get("logs", []), message])

    @staticmethod
    def _list_distros() -> list[str]:
        try:
            result = subprocess.run(["wsl.exe", "--list", "--quiet"], capture_output=True, text=True, timeout=12, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return []
        return [line.replace("\x00", "").strip() for line in result.stdout.splitlines() if line.replace("\x00", "").strip()]

    def status(self) -> dict:
        state = self._state()
        active = self._thread is not None and self._thread.is_alive()
        if active:
            return {**state, "active": True}
        settings = self.bridge.settings()
        preflight = self.bridge.preflight(settings)
        if preflight.get("ok"):
            if state.get("stage") != "ready":
                state = self._save_state(stage="ready", message="YuE Studio is ready for training.")
            return {**state, "active": False, "preflight": preflight}
        distros = self._list_distros()
        selected = settings.get("wsl_distribution", "Ubuntu")
        if not any(name.casefold() == selected.casefold() for name in distros):
            state = self._save_state(
                stage="needs_wsl",
                message="Ubuntu needs to be installed once before YuE Studio can finish setup.",
                action="Run the Windows setup step, then restart if Windows asks.",
                install_command="wsl --install -d Ubuntu",
            )
        return {**state, "active": False, "preflight": preflight}

    def start(self) -> dict:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._state()
            distros = self._list_distros()
            selected = self.bridge.settings().get("wsl_distribution", "Ubuntu")
            if not any(name.casefold() == selected.casefold() for name in distros):
                return self._save_state(
                    stage="needs_wsl",
                    message="Install Ubuntu first, then return here and press Continue setup.",
                    action="Run the Windows setup step, then restart if Windows asks.",
                    install_command="wsl --install -d Ubuntu",
                )
            self._save_state(stage="starting", message="Preparing your private Ubuntu workspace…", logs=[])
            self._thread = threading.Thread(target=self._install, name="yue-studio-setup", daemon=True)
            self._thread.start()
            return self._state()

    def _run(self, args: list[str], timeout: int = 3600) -> str:
        settings = self.bridge.settings()
        result = self.bridge._run_wsl(settings, args, timeout=timeout)
        output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()
        if result.returncode:
            raise RuntimeError(output or f"Ubuntu setup command failed ({result.returncode}).")
        return output

    def _install(self) -> None:
        try:
            settings = self.bridge.settings()
            distro = settings["wsl_distribution"]
            self._save_state(stage="installing", message="Installing Ubuntu tools…")
            self._log("Installing FFmpeg and Python support in Ubuntu.")
            root = ["wsl.exe", "--distribution", distro, "--user", "root", "--"]
            for command in ([*root, "apt-get", "update"], [*root, "apt-get", "install", "-y", "ffmpeg", "python3-venv", "python3-pip", "git"]):
                result = subprocess.run(command, capture_output=True, text=True, timeout=900, check=False)
                if result.returncode:
                    raise RuntimeError(result.stderr.strip() or "Ubuntu package installation failed.")

            user = self._run(["whoami"], timeout=30).strip()
            if not user or user == "root":
                raise RuntimeError("Ubuntu needs a normal user account before YuE Studio can finish setup.")
            model_root = MODEL_ROOT_TEMPLATE.format(user=user)
            venv = f"/home/{user}/.local/share/yue-studio/venv"
            self._save_state(stage="installing", message="Creating YuE Studio’s Python environment…")
            self._run(["mkdir", "-p", model_root], timeout=30)
            self._run(["python3", "-m", "venv", venv], timeout=180)
            python = f"{venv}/bin/python"
            self._run([python, "-m", "pip", "install", "--upgrade", "pip", "huggingface_hub", "numpy", "scipy", "soundfile", "transformers", "safetensors"], timeout=1800)
            self._run([python, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cu128"], timeout=1800)

            self._save_state(stage="downloading", message="Downloading the local ACE-Step captioner (about 6 GB)…")
            self._log("Checking the local ACE-Step audio captioner files.")
            caption_root = self.bridge.windows_to_wsl(settings, self.bridge.app_root.parent / "models" / "captioner")
            caption_download = (
                "from huggingface_hub import hf_hub_download; import sys; root=sys.argv[1]; repo='dernet/acestep-captioner-GGUF'; rev='732354f20c9dd5fa1c037d0e301e8bf837c1cf8e'; "
                "hf_hub_download(repo,'acestep-captioner-Q4_K_M.gguf',revision=rev,local_dir=root); "
                "hf_hub_download(repo,'acestep-captioner-mmproj-Q8_0.gguf',revision=rev,local_dir=root)"
            )
            self._run([python, "-c", caption_download, caption_root], timeout=14400)
            self._save_state(stage="installing", message="Installing ACE-Step’s local audio engine…")
            engine_script = self.bridge.app_root.parent / "install_captioner_engine.ps1"
            engine_root = self.bridge.app_root.parent / "models" / "captioner" / "engine"
            installed_engine = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(engine_script), "-EngineRoot", str(engine_root)], capture_output=True, text=True, timeout=3600, check=False)
            if installed_engine.returncode:
                raise RuntimeError(installed_engine.stderr.strip() or "ACE-Step audio engine installation failed.")

            self._save_state(stage="downloading", message="Downloading YuE2 training models (about 11 GB)…")
            self._log("Downloading YuE2, MERT, VAE, and the Mothersuperior tokenizer head.")
            download = (
                "from huggingface_hub import snapshot_download, hf_hub_download; import sys; root=sys.argv[1]; "
                "snapshot_download('m-a-p/YuE2-3B', local_dir=root+'/yue2', resume_download=True); "
                "snapshot_download('m-a-p/MERT-v2-FullSong', local_dir=root+'/mert', resume_download=True); "
                "snapshot_download('m-a-p/YuE2-Vae', local_dir=root+'/vae', resume_download=True); "
                "hf_hub_download('Mothersuperior/yue2-mothersuperior-realaudio-tokenizer-v4', 'tokenizer_head_joint_v4.pt', local_dir=root+'/training-assets')"
            )
            self._run([python, "-c", download, model_root], timeout=14400)
            self._run([python, "-m", "pip", "install", f"{model_root}/yue2/yue2_infer-0.1.5-py3-none-any.whl"], timeout=900)

            settings.update({
                "wsl_python": python,
                "yue2_model_path": f"{model_root}/yue2",
                "mert_path": f"{model_root}/mert",
                "vae_path": f"{model_root}/vae",
                "tokenizer_head_path": f"{model_root}/training-assets/tokenizer_head_joint_v4.pt",
                "runs_root": f"/home/{user}/.local/share/yue-studio/runs",
            })
            self.bridge.save_settings(settings)
            self._save_state(stage="verifying", message="Checking the finished installation…")
            result = self.bridge.preflight(settings)
            if not result.get("ok"):
                problems = "; ".join(item["name"] for item in result.get("checks", []) if not item["ok"])
                raise RuntimeError(f"Setup completed but verification still needs attention: {problems}")
            self._save_state(stage="ready", message="YuE Studio is ready for training.")
            self._log("Setup finished successfully.")
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._save_state(stage="failed", message=str(exc))
            self._log(f"Setup stopped: {exc}")
