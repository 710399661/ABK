import base64
import os
import sys
import unittest
import urllib.error
from datetime import datetime
from unittest import mock

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import gki_fetch  # noqa: E402


class GetEndDateTests(unittest.TestCase):
    def test_returns_explicit_end_unchanged(self):
        self.assertEqual(gki_fetch.get_end_date("2025-12"), "2025-12")

    def test_empty_string_is_returned_as_is(self):
        # Only ``None`` triggers the "current month" fallback.
        self.assertEqual(gki_fetch.get_end_date(""), "")

    def test_none_uses_current_month(self):
        expected = datetime.now().strftime("%Y-%m")
        self.assertEqual(gki_fetch.get_end_date(None), expected)


class MakeDateRangeTests(unittest.TestCase):
    def test_same_month(self):
        self.assertEqual(gki_fetch.make_date_range("2024-03", "2024-03"), ["2024-03"])

    def test_within_a_year(self):
        self.assertEqual(
            gki_fetch.make_date_range("2024-01", "2024-04"),
            ["2024-01", "2024-02", "2024-03", "2024-04"],
        )

    def test_crosses_year_boundary(self):
        self.assertEqual(
            gki_fetch.make_date_range("2023-11", "2024-02"),
            ["2023-11", "2023-12", "2024-01", "2024-02"],
        )

    def test_months_are_zero_padded(self):
        result = gki_fetch.make_date_range("2024-09", "2024-10")
        self.assertEqual(result, ["2024-09", "2024-10"])
        self.assertTrue(all(len(month) == len("YYYY-MM") for month in result))

    def test_start_after_end_yields_empty(self):
        self.assertEqual(gki_fetch.make_date_range("2025-05", "2025-01"), [])


class ParseVersionTests(unittest.TestCase):
    def test_extracts_all_three_fields(self):
        makefile = "VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 75\nEXTRAVERSION =\n"
        self.assertEqual(gki_fetch.parse_version(makefile), ("6", "1", "75"))

    def test_tolerates_extra_whitespace(self):
        makefile = "VERSION   =    5\nPATCHLEVEL\t= 10\nSUBLEVEL =   200 extra\n"
        self.assertEqual(gki_fetch.parse_version(makefile), ("5", "10", "200"))

    def test_ignores_non_anchored_matches(self):
        # A key that only appears mid-line must not satisfy the ^KEY anchor.
        makefile = "# VERSION = 9\nVERSION = 6\nPATCHLEVEL = 6\nSUBLEVEL = 0\n"
        self.assertEqual(gki_fetch.parse_version(makefile), ("6", "6", "0"))

    def test_missing_field_returns_none(self):
        self.assertIsNone(gki_fetch.parse_version("VERSION = 6\nPATCHLEVEL = 1\n"))

    def test_empty_text_returns_none(self):
        self.assertIsNone(gki_fetch.parse_version(""))


class JsonPathTests(unittest.TestCase):
    def test_builds_path_under_data_dir(self):
        path = gki_fetch.json_path("android14", "6.1")
        self.assertEqual(
            path, os.path.join(gki_fetch.DATA_DIR, "android14", "6.1.json")
        )

    def test_data_dir_is_sibling_of_scripts(self):
        self.assertEqual(
            gki_fetch.DATA_DIR,
            os.path.join(gki_fetch.PROJECT_ROOT, "data"),
        )


class TryFetchTests(unittest.TestCase):
    def _make_response(self, raw_bytes):
        resp = mock.MagicMock()
        resp.read.return_value = raw_bytes
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    def test_decodes_base64_payload(self):
        payload = "VERSION = 6\n"
        encoded = base64.b64encode(payload.encode("utf-8"))
        resp = self._make_response(encoded)
        with mock.patch.object(gki_fetch.urllib.request, "urlopen", return_value=resp):
            self.assertEqual(gki_fetch.try_fetch("http://example/Makefile"), payload)

    def test_http_error_returns_none(self):
        err = urllib.error.HTTPError("http://x", 404, "Not Found", None, None)
        with mock.patch.object(gki_fetch.urllib.request, "urlopen", side_effect=err):
            self.assertIsNone(gki_fetch.try_fetch("http://example/missing"))

    def test_url_error_returns_none(self):
        err = urllib.error.URLError("no route to host")
        with mock.patch.object(gki_fetch.urllib.request, "urlopen", side_effect=err):
            self.assertIsNone(gki_fetch.try_fetch("http://example/down"))

    def test_invalid_base64_returns_none(self):
        resp = self._make_response(b"!!!not base64!!!")
        with mock.patch.object(gki_fetch.urllib.request, "urlopen", return_value=resp):
            self.assertIsNone(gki_fetch.try_fetch("http://example/bad"))


class FetchMakefileTests(unittest.TestCase):
    def setUp(self):
        # ``fetch_makefile`` sleeps between fallback attempts; skip the wait.
        sleep_patcher = mock.patch.object(gki_fetch.time, "sleep")
        self.addCleanup(sleep_patcher.stop)
        sleep_patcher.start()

    def test_deprecated_path_tried_first_when_before_cutoff(self):
        captured = []

        def fake(url):
            captured.append(url)
            return "VERSION = 5\n"

        with mock.patch.object(gki_fetch, "try_fetch", side_effect=fake):
            result = gki_fetch.fetch_makefile("android12", "5.10", "2023-01", "2024-08")

        self.assertEqual(result, "VERSION = 5\n")
        self.assertIn("deprecated/android12-5.10-2023-01", captured[0])

    def test_active_path_tried_first_when_after_cutoff(self):
        captured = []

        def fake(url):
            captured.append(url)
            return "VERSION = 6\n"

        with mock.patch.object(gki_fetch, "try_fetch", side_effect=fake):
            gki_fetch.fetch_makefile("android14", "6.1", "2025-01", "2024-09")

        self.assertNotIn("deprecated/", captured[0])
        self.assertIn("android14-6.1-2025-01", captured[0])

    def test_falls_back_to_second_path(self):
        results = iter([None, "VERSION = 6\n"])

        with mock.patch.object(gki_fetch, "try_fetch", side_effect=lambda url: next(results)):
            result = gki_fetch.fetch_makefile("android14", "6.1", "2025-01", "")

        self.assertEqual(result, "VERSION = 6\n")

    def test_returns_none_when_all_paths_fail(self):
        with mock.patch.object(gki_fetch, "try_fetch", return_value=None):
            self.assertIsNone(
                gki_fetch.fetch_makefile("android14", "6.1", "2025-01", "")
            )

    def test_empty_cutoff_never_prefers_deprecated(self):
        captured = []

        def fake(url):
            captured.append(url)
            return "VERSION = 6\n"

        with mock.patch.object(gki_fetch, "try_fetch", side_effect=fake):
            gki_fetch.fetch_makefile("android16", "6.12", "2020-01", "")

        self.assertNotIn("deprecated/", captured[0])


class FetchLtsTests(unittest.TestCase):
    def test_requests_lts_branch(self):
        captured = {}

        def fake(url):
            captured["url"] = url
            return "VERSION = 6\n"

        with mock.patch.object(gki_fetch, "try_fetch", side_effect=fake):
            result = gki_fetch.fetch_lts("android13", "5.15")

        self.assertEqual(result, "VERSION = 6\n")
        self.assertIn("android13-5.15-lts/Makefile", captured["url"])

    def test_propagates_none(self):
        with mock.patch.object(gki_fetch, "try_fetch", return_value=None):
            self.assertIsNone(gki_fetch.fetch_lts("android13", "5.15"))


if __name__ == "__main__":
    unittest.main()
