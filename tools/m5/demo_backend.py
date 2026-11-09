"""Read-only real-development-data demo; no production startup or provider adapter."""
from contextlib import contextmanager
import sqlite3
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from locomo_memory.export_schemas import MemoryExport
from locomo_memory.m5_api import register_m5_routes
from tools.m5.offline import ROOT, ORIGIN, DEV


class ReadOnlyDatabase:
    @contextmanager
    def connect(self):
        db = sqlite3.connect(ORIGIN.resolve().as_uri() + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        try:
            yield db
        finally:
            db.close()


def resources():
    bundles = {conv: MemoryExport.model_validate_json(
        (ROOT/'var/m5-development/replay-v1/exports'/f'{conv}.json').read_text()) for conv in DEV}
    by_build = {b.build.build_id: b for b in bundles.values()}

    def get(build_id):
        if build_id not in by_build:
            raise HTTPException(404, 'Build not in frozen development set')
        return by_build[build_id].build.model_dump(mode='json')

    def pin(dataset_id, sample_id, build_id):
        build = get(build_id)
        if (build['dataset_id'], build['sample_id']) != (dataset_id, sample_id):
            raise HTTPException(422, 'Build scope mismatch')
        return build_id

    versions = SimpleNamespace(database=ReadOnlyDatabase(), builds=SimpleNamespace(get=get), pin=pin)
    app = FastAPI()
    register_m5_routes(app, versions)
    sources = {s.source_id: s.model_dump(mode='json') for b in bundles.values() for s in b.sources}

    @app.get('/datasets/{dataset}/conversations/{sample}/turns/{turn}')
    def source(dataset: str, sample: str, turn: str):
        item = sources.get(f'{dataset}/{sample}/{turn}')
        if item is None:
            raise HTTPException(404)
        return item

    return bundles, TestClient(app)
