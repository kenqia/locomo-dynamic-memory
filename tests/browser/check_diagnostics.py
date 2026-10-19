"""Run with the isolated Playwright Python: check real failure artifacts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from playwright.sync_api import sync_playwright

from diagnostics import browser_diagnostics


class DiagnosticArtifacts(unittest.TestCase):
    def test_closed_page_does_not_replace_original_failure(self):
        with TemporaryDirectory(prefix="locomo-diagnostics-check-") as directory, sync_playwright() as playwright:
            output = Path(directory)
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                with self.assertRaisesRegex(RuntimeError, "original closed-page failure"):
                    with browser_diagnostics(browser, output) as (page, _, _):
                        page.close()
                        raise RuntimeError("original closed-page failure")
                summary = json.loads((output / "diagnostics.json").read_text())
                self.assertEqual(summary["status"], "failed")
                self.assertEqual(summary["exception_type"], "RuntimeError")
                self.assertIn("screenshot_error", summary)
                self.assertIn("page_state_error", summary)
            finally:
                browser.close()

    def test_failure_keeps_evidence_and_original_exception(self):
        with TemporaryDirectory(prefix="locomo-diagnostics-check-") as directory, sync_playwright() as playwright:
            output = Path(directory)
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    with browser_diagnostics(browser, output) as (page, _, _):
                        page.goto("data:text/html,<h1>Synthetic diagnostic page</h1>")
                        raise RuntimeError("synthetic failure")
                summary = json.loads((output / "diagnostics.json").read_text())
                self.assertEqual(summary["status"], "failed")
                self.assertEqual(summary["exception_type"], "RuntimeError")
                self.assertNotIn("trace_error", summary)
                self.assertNotIn("screenshot_error", summary)
                self.assertNotIn("page_state_error", summary)
                self.assertTrue((output / "failure.png").read_bytes().startswith(b"\x89PNG"))
                self.assertIn("Synthetic diagnostic page", (output / "page-state.txt").read_text())
                with zipfile.ZipFile(output / "trace.zip") as archive:
                    self.assertTrue(any(name.endswith(".trace") for name in archive.namelist()))
            finally:
                browser.close()

    def test_success_records_summary_without_failure_artifacts(self):
        with TemporaryDirectory(prefix="locomo-diagnostics-check-") as directory, sync_playwright() as playwright:
            output = Path(directory)
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                with browser_diagnostics(browser, output) as (page, _, _):
                    page.goto("data:text/html,<h1>Synthetic success</h1>")
                self.assertEqual(json.loads((output / "diagnostics.json").read_text())["status"], "passed")
                self.assertFalse((output / "trace.zip").exists())
                self.assertFalse((output / "failure.png").exists())
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
