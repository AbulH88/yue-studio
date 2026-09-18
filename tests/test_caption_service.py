import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yue_studio"))

from caption_service import CaptionService, format_yue2_caption, instrumental_warning


class CaptionServiceTests(unittest.TestCase):
    def test_formats_local_caption_for_instrumental_yue2_training(self):
        caption = format_yue2_caption("Slow medieval folk with lute, frame drum and room reverb.")
        self.assertEqual(caption, "instrumental, no vocals, slow medieval folk with lute, frame drum and room reverb")

    def test_instrumental_warning_flags_singing_terms(self):
        self.assertIn("singing", instrumental_warning("instrumental, soft singing, lute") or "")

    def test_empty_caption_is_rejected(self):
        with self.assertRaises(ValueError):
            format_yue2_caption("   ")

    def test_batch_releases_vram_after_each_track_and_stops_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CaptionService(root)
            service.status = lambda: {"ready": True}
            good = root / "good.wav"
            bad = root / "bad.wav"
            existing = root / "existing.wav"
            for path in (good, bad, existing):
                path.write_bytes(b"audio")
            existing.with_suffix(".txt").write_text("already captioned", encoding="utf-8")
            attempted = []
            def generated(path, instrumental=True):
                attempted.append(path)
                if path == bad:
                    raise RuntimeError("bad audio")
                return {"caption": "instrumental, no vocals, lute"}
            service.generate = generated
            released = []
            service.release_vram = lambda: released.append(True)
            tracks = [{"name": path.name, "path": str(path), "caption_path": str(path.with_suffix('.txt')), "has_caption": path.with_suffix('.txt').exists()} for path in (good, bad, existing)]
            service.start_batch(tracks)
            while service.batch_status()["status"] == "running":
                pass
            result = service.batch_status()
            self.assertEqual(result["saved"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(len(result["failed"]), 1)
            self.assertEqual(result["status"], "stopped")
            self.assertEqual(result["completed"], 2)
            self.assertEqual(len(released), 2)
            self.assertEqual(attempted, [good, bad])
            self.assertEqual(existing.with_suffix(".txt").read_text(encoding="utf-8"), "already captioned")

    def test_server_uses_context_large_enough_for_full_songs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CaptionService(root)
            engine = root / "llama-server.exe"
            service.status = lambda: {"models": [{"ready": True}, {"ready": True}]}
            service._engine_path = lambda: engine
            with patch("caption_service.subprocess.Popen") as started, patch("caption_service.urllib.request.urlopen"):
                service._ensure_server()
            arguments = started.call_args.args[0]
            self.assertEqual(arguments[arguments.index("-c") + 1], "8192")

    def test_caption_request_uses_audio_url_data_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            track = root / "song.wav"
            track.write_bytes(b"wav")
            service = CaptionService(root)
            service._ensure_server = lambda: None
            response = type("Response", (), {"read": lambda self: b'{"choices":[{"message":{"content":"lute"}}]}', "__enter__": lambda self: self, "__exit__": lambda self, *args: None})()
            with patch("caption_service.urllib.request.urlopen", return_value=response) as opened:
                service.generate(track)
            body = json.loads(opened.call_args.args[0].data.decode("utf-8"))
            audio = body["messages"][0]["content"][0]
            self.assertEqual(audio["type"], "audio_url")
            self.assertTrue(audio["audio_url"]["url"].startswith("data:audio/wav;base64,"))
