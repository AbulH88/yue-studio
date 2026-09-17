import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yue_studio"))

from training_bridge import TrainingBridge, parse_training_line, safe_run_name


class TrainingBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "wsl").mkdir()
        (self.root / "wsl" / "run_instrumental.py").write_text("print('ok')\n", encoding="utf-8")
        self.config = {}

        def load():
            return json.loads(json.dumps(self.config))

        def save(value):
            self.config = json.loads(json.dumps(value))

        self.bridge = TrainingBridge(self.root, load, save)

    def tearDown(self):
        self.temp.cleanup()

    def test_safe_run_name_removes_shell_characters(self):
        self.assertEqual(safe_run_name(" My Project; rm -rf / "), "my-project-rm-rf")

    def test_parse_training_progress(self):
        parsed = parse_training_line("step 200 loss 2.237 cursor nan len 8821 341s mem 13.5G")
        self.assertEqual(parsed["step"], 200)
        self.assertEqual(parsed["loss"], 2.237)
        self.assertEqual(parsed["elapsed_seconds"], 341)
        self.assertEqual(parsed["vram_gb"], 13.5)

    def test_parse_evaluation(self):
        parsed = parse_training_line("EVAL step 400 minted_val 4.329 artist 0.612 900s")
        self.assertEqual(parsed, {"step": 400, "validation_loss": 4.329, "artist_loss": 0.612})

    def test_save_settings_only_accepts_known_fields(self):
        saved = self.bridge.save_settings({"wsl_distribution": "Ubuntu-24.04", "minimum_free_gb": 30, "unexpected": "ignored"})
        self.assertEqual(saved["wsl_distribution"], "Ubuntu-24.04")
        self.assertEqual(saved["minimum_free_gb"], 30)
        self.assertNotIn("unexpected", saved)

    def test_start_writes_manifest_before_worker_starts(self):
        audio = self.root / "song.wav"
        audio.write_bytes(b"RIFF-test")
        self.bridge.save_settings({
            "wsl_python": "/venv/bin/python",
            "yue2_model_path": "/models/yue2",
            "mert_path": "/models/mert",
            "vae_path": "/models/vae",
            "tokenizer_head_path": "/models/head.pt",
            "runs_root": "/runs",
        })
        written = {}

        def capture(_settings, path, value):
            written["path"] = path
            written["value"] = value

        completed = type("Completed", (), {"returncode": 1, "stdout": "", "stderr": ""})()
        made = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(self.bridge, "preflight", return_value={"ok": True, "checks": []}), \
             patch.object(self.bridge, "_run_wsl", side_effect=[completed, made]), \
             patch.object(self.bridge, "windows_to_wsl", side_effect=["/mnt/g/app/wsl/run_instrumental.py", "/mnt/g/data/song.wav"]), \
             patch.object(self.bridge, "_write_linux_json", side_effect=capture), \
             patch("training_bridge.threading.Thread") as thread:
            result = self.bridge.start(
                {"name": "My Run", "dataset_name": "Dataset", "steps": 200, "rank": 64},
                [{"name": "song.wav", "path": str(audio), "caption": "medieval instrumental", "has_caption": True}],
            )

        self.assertEqual(result["status"], "queued")
        self.assertTrue(written["path"].endswith("/manifest.json"))
        self.assertEqual(written["value"]["training"]["artist_fraction"], 1.0)
        self.assertEqual(written["value"]["dataset"]["files"][0]["caption"], "medieval instrumental")
        thread.return_value.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
