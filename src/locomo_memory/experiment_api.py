"""Read-only, credential-safe prerequisites for the local experiment runner."""
import hashlib
import importlib.util
import os
import platform
from pathlib import Path

import numpy as np
from importlib.metadata import version

from .embeddings import EmbeddingFailure, MiniLMEmbedder
from .model import KNOWN_MODEL_VERSION, utc_now


def register_experiment_routes(app):
    @app.get('/experiment-preflight')
    def inspect_preflight(verify_embedding: bool = False):
        settings = app.state.settings
        record = {
            'checked_at': utc_now(),
            'implementation_sha256': hashlib.sha256(b''.join(p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest(),
            'database_path': str(settings.db_path.resolve()),
            'credential_present': bool(os.environ.get('DEEPSEEK_API_KEY')),
            'config': settings.snapshot(), 'python': platform.python_version(),
            'packages': {name: version(name) for name in ('locomo-dynamic-memory', 'fastapi', 'numpy', 'pydantic')},
            'generation': {'status': 'not_called', 'adapter': type(app.state.model).__name__,
                           'controlled_transport': getattr(app.state.model, '_transport', None) is not None,
                           'known_service_version': KNOWN_MODEL_VERSION},
            'embedding': {'status': 'not_verified', 'adapter': type(app.state.embedder).__name__, 'real_adapter': isinstance(app.state.embedder, MiniLMEmbedder), 'dependencies_present': all(importlib.util.find_spec(name) is not None for name in ('sentence_transformers', 'torch'))},
        }
        if verify_embedding:
            try:
                identity = app.state.embedder.identity()
                vectors = app.state.embedder.encode(['Alex lives in Paris.', 'Sam works in London.'])
                if vectors.shape != (2, 384) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), [1, 1]):
                    raise EmbeddingFailure('embedding_dimension_mismatch')
                try:
                    app.state.embedder.encode(['word ' * 300])
                except EmbeddingFailure as error:
                    if error.code != 'embedding_input_too_long':
                        raise
                else:
                    raise EmbeddingFailure('embedding_length_policy_not_enforced')
                record['embedding'].update(status='verified', identity=identity)
            except EmbeddingFailure as error:
                record['embedding'].update(status='failed', error={'code': error.code})
        return record
