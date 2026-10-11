"""Regression coverage for missing launch logs and empty failure ledgers."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from scripts import refresh_launch_logs as refresh


SUCCESS = """== Orbital launches ==
{{TLS-RL
|date = 1 January
|rocket = {{#invoke:flag|icon|USA}} Falcon 9
|flight = Example
|outcome = Successful
}}
"""


class RefreshTests(unittest.TestCase):
    def run_refresh(self, pages):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "refresh"
        log = io.StringIO()
        with patch.object(refresh, "OUT", str(output)), \
             patch.object(refresh, "wikitext", return_value="|total = 330"), \
             patch.object(refresh, "list_pages", side_effect=lambda year, offline: pages.get(year, [])), \
             patch("sys.argv", ["refresh", "--offline", "--first", "2025", "--current", "2026"]), \
             contextlib.redirect_stdout(log):
            refresh.main()
        return output, log.getvalue()

    def test_missing_cache_writes_no_misleading_zero_counts(self):
        output, log = self.run_refresh({})
        self.assertFalse(output.exists())
        self.assertIn("counts are unknown, not zero", log)
        self.assertIn("No refresh files written", log)

    def test_no_failures_still_writes_a_readable_ledger(self):
        output, log = self.run_refresh({2025: [SUCCESS], 2026: [SUCCESS]})
        ledger = pd.read_csv(output / "launch_failures_refresh.csv")
        self.assertTrue(ledger.empty)
        self.assertEqual(list(ledger.columns), ["date", "vehicle", "flight", "country", "outcome", "remarks"])
        cadence = pd.read_csv(output / "launch_cadence_refresh.csv")
        current = cadence[cadence.year == 2026].iloc[0]
        self.assertEqual(current.global_orbital_attempts, 1)
        self.assertEqual(current.spacex_all_vehicles, 1)
        self.assertIn("failures 0", log)

    def test_missing_current_year_remains_unknown(self):
        output, log = self.run_refresh({2025: [SUCCESS]})
        cadence = pd.read_csv(output / "launch_cadence_refresh.csv")
        current = cadence[cadence.year == 2026].iloc[0]
        self.assertTrue(pd.isna(current.global_orbital_attempts))
        self.assertTrue(pd.isna(current.spacex_all_vehicles))
        self.assertIn("unknown launches", log)


if __name__ == "__main__":
    unittest.main()
