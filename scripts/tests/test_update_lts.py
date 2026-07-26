import json
import os
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import update_lts  # noqa: E402


class UpdateLtsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "6.1.json")

        # Restrict iteration to a single deterministic target.
        targets_patcher = mock.patch.object(
            update_lts, "TARGETS", {("android14", "6.1"): ("2023-06", None, "")}
        )
        self.addCleanup(targets_patcher.stop)
        targets_patcher.start()

        path_patcher = mock.patch.object(
            update_lts, "json_path", return_value=self.path
        )
        self.addCleanup(path_patcher.stop)
        path_patcher.start()

    def _write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_skips_when_json_missing(self):
        with mock.patch.object(update_lts, "fetch_lts") as fetch_lts:
            update_lts.update_lts()
        fetch_lts.assert_not_called()
        self.assertFalse(os.path.exists(self.path))

    def test_writes_new_lts_value(self):
        self._write({"lts": "6.1.5", "entries": []})
        with mock.patch.object(update_lts, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_lts, "parse_version", return_value=("6", "1", "20")):
            update_lts.update_lts()
        self.assertEqual(self._read()["lts"], "6.1.20")

    def test_unchanged_lts_leaves_file_untouched(self):
        self._write({"lts": "6.1.20", "entries": []})
        before = os.path.getmtime(self.path)
        with mock.patch.object(update_lts, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_lts, "parse_version", return_value=("6", "1", "20")):
            update_lts.update_lts()
        self.assertEqual(os.path.getmtime(self.path), before)

    def test_fetch_none_leaves_lts_unchanged(self):
        self._write({"lts": "6.1.5", "entries": []})
        with mock.patch.object(update_lts, "fetch_lts", return_value=None), \
             mock.patch.object(update_lts, "parse_version") as parse:
            update_lts.update_lts()
        parse.assert_not_called()
        self.assertEqual(self._read()["lts"], "6.1.5")

    def test_parse_failure_leaves_lts_unchanged(self):
        self._write({"lts": "6.1.5", "entries": []})
        with mock.patch.object(update_lts, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_lts, "parse_version", return_value=None):
            update_lts.update_lts()
        self.assertEqual(self._read()["lts"], "6.1.5")


if __name__ == "__main__":
    unittest.main()
