import json
import os
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import fetch_all  # noqa: E402


class FetchAllTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "android14", "6.1.json")

        sleep_patcher = mock.patch.object(fetch_all.time, "sleep")
        self.addCleanup(sleep_patcher.stop)
        sleep_patcher.start()

        targets_patcher = mock.patch.object(
            fetch_all, "TARGETS", {("android14", "6.1"): ("2024-01", "2024-02", "")}
        )
        self.addCleanup(targets_patcher.stop)
        targets_patcher.start()

        path_patcher = mock.patch.object(fetch_all, "json_path", return_value=self.path)
        self.addCleanup(path_patcher.stop)
        path_patcher.start()

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_writes_entries_and_lts(self):
        with mock.patch.object(fetch_all, "get_end_date", return_value="2024-02"), \
             mock.patch.object(fetch_all, "make_date_range", return_value=["2024-01", "2024-02"]), \
             mock.patch.object(fetch_all, "fetch_makefile", return_value="MK"), \
             mock.patch.object(fetch_all, "fetch_lts", return_value="LTS"), \
             mock.patch.object(fetch_all, "parse_version", side_effect=[
                 ("6", "1", "10"), ("6", "1", "11"), ("6", "1", "20")]):
            fetch_all.fetch_all()

        data = self._read()
        self.assertEqual(data["android_version"], "android14")
        self.assertEqual(data["kernel_version"], "6.1")
        self.assertEqual(data["lts"], "6.1.20")
        self.assertEqual(
            data["entries"],
            [{"date": "2024-01", "kernel": "6.1.10"},
             {"date": "2024-02", "kernel": "6.1.11"}],
        )

    def test_skips_dates_with_no_makefile(self):
        with mock.patch.object(fetch_all, "get_end_date", return_value="2024-02"), \
             mock.patch.object(fetch_all, "make_date_range", return_value=["2024-01", "2024-02"]), \
             mock.patch.object(fetch_all, "fetch_makefile", side_effect=[None, "MK"]), \
             mock.patch.object(fetch_all, "fetch_lts", return_value=None), \
             mock.patch.object(fetch_all, "parse_version", side_effect=[("6", "1", "11")]):
            fetch_all.fetch_all()

        data = self._read()
        self.assertEqual(data["entries"], [{"date": "2024-02", "kernel": "6.1.11"}])
        self.assertIsNone(data["lts"])

    def test_no_data_writes_nothing(self):
        with mock.patch.object(fetch_all, "get_end_date", return_value="2024-02"), \
             mock.patch.object(fetch_all, "make_date_range", return_value=["2024-01"]), \
             mock.patch.object(fetch_all, "fetch_makefile", return_value=None), \
             mock.patch.object(fetch_all, "fetch_lts", return_value=None), \
             mock.patch.object(fetch_all, "parse_version"):
            fetch_all.fetch_all()

        self.assertFalse(os.path.exists(self.path))

    def test_lts_only_still_writes(self):
        with mock.patch.object(fetch_all, "get_end_date", return_value="2024-01"), \
             mock.patch.object(fetch_all, "make_date_range", return_value=["2024-01"]), \
             mock.patch.object(fetch_all, "fetch_makefile", return_value=None), \
             mock.patch.object(fetch_all, "fetch_lts", return_value="LTS"), \
             mock.patch.object(fetch_all, "parse_version", return_value=("6", "1", "20")):
            fetch_all.fetch_all()

        data = self._read()
        self.assertEqual(data["entries"], [])
        self.assertEqual(data["lts"], "6.1.20")


if __name__ == "__main__":
    unittest.main()
