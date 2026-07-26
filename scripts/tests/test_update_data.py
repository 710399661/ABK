import json
import os
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import update_data  # noqa: E402


class UpdateTargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "android14", "6.1.json")

        # Never sleep and always resolve to our temp path.
        sleep_patcher = mock.patch.object(update_data.time, "sleep")
        self.addCleanup(sleep_patcher.stop)
        sleep_patcher.start()

        path_patcher = mock.patch.object(
            update_data, "json_path", return_value=self.path
        )
        self.addCleanup(path_patcher.stop)
        path_patcher.start()

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_existing(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_creates_file_for_new_target(self):
        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01", "2024-02"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-02"), \
             mock.patch.object(update_data, "fetch_makefile", return_value="MK"), \
             mock.patch.object(update_data, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_data, "parse_version", side_effect=[
                 ("6", "1", "10"), ("6", "1", "11"), ("6", "1", "20")]):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-02", ""
            )

        self.assertTrue(changed)
        data = self._read()
        self.assertEqual(data["lts"], "6.1.20")
        self.assertEqual(
            data["entries"],
            [{"date": "2024-01", "kernel": "6.1.10"},
             {"date": "2024-02", "kernel": "6.1.11"}],
        )

    def test_only_fetches_missing_months(self):
        self._write_existing({
            "android_version": "android14",
            "kernel_version": "6.1",
            "lts": "6.1.5",
            "entries": [{"date": "2024-01", "kernel": "6.1.10"}],
        })

        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01", "2024-02"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-02"), \
             mock.patch.object(update_data, "fetch_makefile", return_value="MK") as fetch_mk, \
             mock.patch.object(update_data, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_data, "parse_version", side_effect=[
                 ("6", "1", "11"), ("6", "1", "5")]):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-02", ""
            )

        # Only the missing month (2024-02) should have been fetched.
        self.assertEqual(fetch_mk.call_count, 1)
        self.assertEqual(fetch_mk.call_args.args[2], "2024-02")
        self.assertTrue(changed)
        self.assertEqual(len(self._read()["entries"]), 2)

    def test_entries_are_sorted_by_date(self):
        self._write_existing({
            "android_version": "android14",
            "kernel_version": "6.1",
            "lts": None,
            "entries": [{"date": "2024-03", "kernel": "6.1.30"}],
        })

        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01", "2024-03"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-03"), \
             mock.patch.object(update_data, "fetch_makefile", return_value="MK"), \
             mock.patch.object(update_data, "fetch_lts", return_value=None), \
             mock.patch.object(update_data, "parse_version", side_effect=[("6", "1", "10")]):
            update_data.update_target("android14", "6.1", "2024-01", "2024-03", "")

        dates = [e["date"] for e in self._read()["entries"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(dates, ["2024-01", "2024-03"])

    def test_no_changes_does_not_write_file(self):
        self._write_existing({
            "android_version": "android14",
            "kernel_version": "6.1",
            "lts": "6.1.5",
            "entries": [{"date": "2024-01", "kernel": "6.1.10"}],
        })
        before = os.path.getmtime(self.path)

        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-01"), \
             mock.patch.object(update_data, "fetch_makefile") as fetch_mk, \
             mock.patch.object(update_data, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_data, "parse_version", return_value=("6", "1", "5")):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-01", ""
            )

        self.assertFalse(changed)
        fetch_mk.assert_not_called()  # no missing months
        self.assertEqual(os.path.getmtime(self.path), before)

    def test_fetch_returning_none_is_skipped(self):
        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01", "2024-02"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-02"), \
             mock.patch.object(update_data, "fetch_makefile", side_effect=[None, "MK"]), \
             mock.patch.object(update_data, "fetch_lts", return_value=None), \
             mock.patch.object(update_data, "parse_version", side_effect=[("6", "1", "11")]):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-02", ""
            )

        self.assertTrue(changed)
        entries = self._read()["entries"]
        self.assertEqual(entries, [{"date": "2024-02", "kernel": "6.1.11"}])

    def test_parse_failure_is_skipped(self):
        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-01"), \
             mock.patch.object(update_data, "fetch_makefile", return_value="MK"), \
             mock.patch.object(update_data, "fetch_lts", return_value=None), \
             mock.patch.object(update_data, "parse_version", return_value=None):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-01", ""
            )

        self.assertFalse(changed)
        self.assertFalse(os.path.exists(self.path))

    def test_lts_change_marks_changed(self):
        self._write_existing({
            "android_version": "android14",
            "kernel_version": "6.1",
            "lts": "6.1.5",
            "entries": [{"date": "2024-01", "kernel": "6.1.10"}],
        })

        with mock.patch.object(update_data, "make_date_range", return_value=["2024-01"]), \
             mock.patch.object(update_data, "get_end_date", return_value="2024-01"), \
             mock.patch.object(update_data, "fetch_makefile"), \
             mock.patch.object(update_data, "fetch_lts", return_value="LTS"), \
             mock.patch.object(update_data, "parse_version", return_value=("6", "1", "9")):
            changed = update_data.update_target(
                "android14", "6.1", "2024-01", "2024-01", ""
            )

        self.assertTrue(changed)
        self.assertEqual(self._read()["lts"], "6.1.9")


class MainTests(unittest.TestCase):
    def test_aggregates_changed_flag(self):
        with mock.patch.object(update_data, "update_target", side_effect=[False, True, False, False, False]):
            self.assertTrue(update_data.main())

    def test_no_changes_returns_false(self):
        with mock.patch.object(update_data, "update_target", return_value=False):
            self.assertFalse(update_data.main())

    def test_iterates_every_target(self):
        with mock.patch.object(update_data, "update_target", return_value=False) as ut:
            update_data.main()
        self.assertEqual(ut.call_count, len(update_data.TARGETS))


if __name__ == "__main__":
    unittest.main()
