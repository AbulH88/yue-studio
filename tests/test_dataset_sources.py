import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yue_studio"))

from app import dataset_sources, normalize_sources, scan_sources


class DatasetSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.album = self.root / "album"
        self.album.mkdir()
        (self.album / "lute.flac").write_bytes(b"audio")
        (self.album / "lute.txt").write_text("instrumental lute", encoding="utf-8")
        nested = self.album / "nested"
        nested.mkdir()
        (nested / "harp.wav").write_bytes(b"audio")
        (self.root / "outside.mp3").write_bytes(b"audio")
        (self.root / "notes.pdf").write_bytes(b"not audio")

    def tearDown(self):
        self.temp.cleanup()

    def test_folder_sources_scan_recursively(self):
        tracks = scan_sources([{"type": "folder", "path": str(self.album)}])
        self.assertEqual([track["name"] for track in tracks], ["harp.wav", "lute.flac"])
        self.assertTrue(next(track for track in tracks if track["name"] == "lute.flac")["has_caption"])

    def test_mixed_sources_deduplicate_tracks(self):
        tracks = scan_sources([
            {"type": "folder", "path": str(self.album)},
            {"type": "file", "path": str(self.album / "lute.flac")},
            {"type": "file", "path": str(self.root / "outside.mp3")},
        ])
        self.assertEqual([track["name"] for track in tracks], ["harp.wav", "lute.flac", "outside.mp3"])

    def test_legacy_path_is_a_folder_source(self):
        self.assertEqual(dataset_sources({"path": str(self.album)}), [{"type": "folder", "path": str(self.album)}])

    def test_missing_source_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sources([{"type": "file", "path": str(self.root / "gone.wav")}])


if __name__ == "__main__":
    unittest.main()
