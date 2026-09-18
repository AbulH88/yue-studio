import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yue_studio"))

from update_service import UpdateService, validate_manifest, version_key


class UpdateServiceTests(unittest.TestCase):
    def test_version_key_orders_versions(self):
        self.assertGreater(version_key("0.10.0"), version_key("0.2.0"))

    def test_manifest_requires_https_and_checksum(self):
        manifest = validate_manifest({"version": "1.2.3", "url": "https://example.com/app.zip", "sha256": "a" * 64})
        self.assertEqual(manifest["version"], "1.2.3")
        with self.assertRaises(ValueError):
            validate_manifest({"version": "1.2.3", "url": "http://example.com/app.zip", "sha256": "a" * 64})

    def test_unpublished_update_is_not_an_error(self):
        config = {}
        with tempfile.TemporaryDirectory() as directory:
            service = UpdateService(Path(directory), lambda: config, lambda value: config.update(value), lambda: False)
            service._check()
        self.assertEqual(config["update"]["status"], "not_published")

