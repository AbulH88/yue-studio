import tempfile
import unittest
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

    def test_batch_skips_existing_caption_and_continues_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CaptionService(root)
            good = root / "good.wav"
            bad = root / "bad.wav"
            existing = root / "existing.wav"
            for path in (good, bad, existing):
                path.write_bytes(b"audio")
            existing.with_suffix(".txt").write_text("already captioned", encoding="utf-8")
            def generated(path, instrumental=True):
                if path == bad:
                    raise RuntimeError("bad audio")
                return {"caption": "instrumental, no vocals, lute"}
            service.generate = generated
            tracks = [{"name": path.name, "path": str(path), "caption_path": str(path.with_suffix('.txt')), "has_caption": path.with_suffix('.txt').exists()} for path in (good, bad, existing)]
            service.start_batch(tracks)
            while service.batch_status()["status"] == "running":
                pass
            result = service.batch_status()
            self.assertEqual(result["saved"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(len(result["failed"]), 1)
