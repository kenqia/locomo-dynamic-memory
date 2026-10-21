"""Read-only local API factory for displaying saved real experiment traces.

Use with the unchanged Streamlit app. All non-GET requests are blocked.
"""
import json
import os
from pathlib import Path

from fastapi.responses import JSONResponse
from locomo_memory.api import create_app
from locomo_memory.config import Settings


class NoProvider:
    def generate(self, *args, **kwargs):
        raise AssertionError('recorded_showcase_must_not_generate')


def app_factory():
    directory = Path(os.environ['LOCOMO_SHOWCASE_DIRECTORY']).resolve()
    plan = json.loads((directory / 'plan.json').read_text())
    app = create_app(Settings.model_validate(plan['settings']), model=NoProvider())

    @app.middleware('http')
    async def read_only(request, call_next):
        if request.method != 'GET':
            return JSONResponse(status_code=403, content={'error': {'code': 'recorded_showcase_read_only',
                'message': 'This isolated display reads saved real traces; generation and builds are disabled'}})
        return await call_next(request)

    return app
