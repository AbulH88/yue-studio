import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yue_studio"))

from caption_service import format_yue2_caption, instrumental_warning


class CaptionServiceTests(unittest.TestCase):
    def test_formats_local_caption_for_instrumental_yue2_training(self):
        caption = format_yue2_caption("Slow medieval folk with lute, frame drum and room reverb.")
        self.assertEqual(caption, "instrumental, no vocals, slow medieval folk with lute, frame drum and room reverb")

    def test_instrumental_warning_flags_singing_terms(self):
        self.assertIn("singing", instrumental_warning("instrumental, soft singing, lute") or "")

    def test_empty_caption_is_rejected(self):
        with self.assertRaises(ValueError):
            format_yue2_caption("   ")

