"""Prevent raw database exposure and incomplete dataset pages during publication."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.check_site import ROOT, validate_site


class PublicationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for folder in ("data", "osalr", "images", "docs", "scripts"):
            (self.root / folder).symlink_to(ROOT / folder, target_is_directory=True)
        shutil.copytree(ROOT / "site", self.root / "site")

    def test_raw_database_is_rejected_even_without_a_download_link(self):
        shutil.copy2(ROOT / "osalr" / "osalr.db", self.root / "site" / "osalr" / "osalr.db")
        with self.assertRaisesRegex(ValueError, "Raw data artifact is publicly exposed"):
            validate_site(self.root)

    def test_raw_csv_is_rejected_even_without_a_download_link(self):
        shutil.copy2(ROOT / "data" / "failures.csv", self.root / "site" / "failures.csv")
        with self.assertRaisesRegex(ValueError, "Raw data artifact is publicly exposed"):
            validate_site(self.root)

    def test_missing_dataset_page_is_rejected(self):
        (self.root / "site" / "datasets" / "failures" / "index.html").unlink()
        with self.assertRaisesRegex(ValueError, "Missing dataset page"):
            validate_site(self.root)


if __name__ == "__main__":
    unittest.main()
