"""Decode a local synthetic demo clip in a fresh, offline browser context."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    video = args.video.resolve(strict=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
        page = browser.new_page()
        page.route('http://**/*', lambda route: route.abort())
        page.route('https://**/*', lambda route: route.abort())
        page.goto(video.as_uri())
        page.locator('video').wait_for()
        page.locator('video').evaluate('(video) => { video.muted = true; return video.play(); }')
        page.wait_for_function('document.querySelector("video").currentTime > 0.1 && document.querySelector("video").readyState >= 2')
        result = page.locator('video').evaluate('(video) => ({duration_seconds: video.duration, width: video.videoWidth, height: video.videoHeight, current_time: video.currentTime, error: video.error})')
        assert result['duration_seconds'] > 0 and result['width'] == 1280 and result['height'] == 900 and result['error'] is None
        result['status'] = 'passed'
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))
        browser.close()
