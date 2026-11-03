"""Preserve failure evidence from the isolated, synthetic-only browser session."""

from contextlib import contextmanager
import json


@contextmanager
def browser_diagnostics(browser, output):
    context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    page_errors, console_errors = [], []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    result = {"status": "passed", "pageerrors": page_errors, "console_errors": console_errors}
    try:
        yield page, page_errors, console_errors
    except BaseException as error:
        result.update(status="failed", exception_type=type(error).__name__)
        # Keep the original failure even if a crashed page cannot provide evidence.
        for name, capture in [
            ("screenshot", lambda: page.screenshot(path=str(output / "failure.png"), full_page=True, timeout=5000)),
            ("page_state", lambda: (output / "page-state.txt").write_text(page.locator("body").inner_text(timeout=5000))),
        ]:
            try:
                capture()
            except Exception as capture_error:
                result[name + "_error"] = type(capture_error).__name__
        raise
    finally:
        try:
            context.tracing.stop(path=str(output / "trace.zip") if result["status"] == "failed" else None)
        except Exception as trace_error:
            result["trace_error"] = type(trace_error).__name__
        try:
            context.close()
        except Exception as close_error:
            result["context_close_error"] = type(close_error).__name__
        (output / "diagnostics.json").write_text(json.dumps(result, indent=2))
