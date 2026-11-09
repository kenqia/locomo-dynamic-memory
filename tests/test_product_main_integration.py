"""Exercise the imported Console entry and main's preserved workflow."""
from pathlib import Path
import sys

import httpx
from streamlit.testing.v1 import AppTest


def test_console_entry_switches_to_main_workflow_and_back(client, monkeypatch):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, httpx.URL(url).path))
        kwargs.pop('timeout', None)
        return client.request(method, url, **kwargs)

    monkeypatch.setattr(httpx, 'request', request)
    entry = Path(__file__).parents[1] / 'src/locomo_memory/console_ui.py'
    app = AppTest.from_file(str(entry), default_timeout=30).run()
    assert not app.exception
    assert app.radio(key='console_page').value == 'Overview'
    app.radio(key='console_page').set_value('Demo').run()
    app.toggle(key='console_legacy_workflow').set_value(True).run()
    assert not app.exception
    assert any('上传一份对话数据' in item.value for item in app.markdown)
    app.toggle(key='console_legacy_workflow').set_value(False).run()
    assert not app.exception
    app.radio(key='console_page').set_value('Overview').run()
    assert not app.exception
    assert app.button(key='overview_experiments')
    assert all(method == 'GET' for method, _ in calls)
