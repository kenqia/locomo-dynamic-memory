"""E5 process-local, bounded exact-query cache. Opt-in; no provider requests."""
from collections import OrderedDict
import hashlib
import json
from threading import Lock
import time

import numpy as np

from locomo_memory.embeddings import normalize_vectors

VERSION='exact-query-embedding-v1'
ENCODING_CONFIG=dict(input='single_exact_utf8_question',batch_size=1,output_dtype='float32',
                     normalization='locomo_normalize_vectors',precision='float32',truncate='reject')


def cache_key(*,build_id,index_fingerprint,embedding_identity,question,text_schema_version,encoding_config):
    if not build_id or not index_fingerprint or not text_schema_version or not embedding_identity.get('model') or not embedding_identity.get('revision'):
        raise ValueError('Complete cache identity required')
    # JSON encodes the raw bytes as hex; no case folding, whitespace stripping,
    # Unicode normalization, truncation or cross-Build reuse is allowed.
    identity=dict(cache_version=VERSION,build_id=build_id,index_fingerprint=index_fingerprint,
        embedding_identity=embedding_identity,encoding_config=encoding_config,
        question_utf8_hex=question.encode('utf-8').hex(),text_schema_version=text_schema_version)
    return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class ExactQueryEmbeddingCache:
    def __init__(self,max_entries=4096):
        if type(max_entries) is not int or max_entries<1:raise ValueError('Positive capacity required')
        self.max_entries=max_entries;self.entries=OrderedDict();self.lock=Lock()
        self.hits=0;self.misses=0;self.embedding_calls=0;self.evictions=0

    def vector(self,encoder,question,*,build_id,index_fingerprint,text_schema_version,encoding_config=None):
        started=time.perf_counter();cpu=time.process_time()
        identity=encoder.identity();config=ENCODING_CONFIG if encoding_config is None else encoding_config
        key=cache_key(build_id=build_id,index_fingerprint=index_fingerprint,embedding_identity=identity,
            question=question,text_schema_version=text_schema_version,encoding_config=config)
        with self.lock:
            hit=key in self.entries
            if hit:
                raw=self.entries.pop(key);self.entries[key]=raw;self.hits+=1
            else:
                self.misses+=1;self.embedding_calls+=1
                # Identical normalization boundary to RetrievalService.query.
                vector=normalize_vectors(encoder.encode([question]),1,identity['dimensions'])[0]
                raw=vector.tobytes();self.entries[key]=raw
                if len(self.entries)>self.max_entries:
                    self.entries.popitem(last=False);self.evictions+=1
            # Own a copy so the caller cannot mutate the cached value.
            vector=np.frombuffer(raw,dtype=np.float32).copy()
        return vector,dict(cache_version=VERSION,cache_key=key,cache_hit=hit,
            cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-started,
            embedding_calls=0 if hit else 1,stored_vector_bytes=len(raw))

    def snapshot(self):
        with self.lock:
            return dict(version=VERSION,hits=self.hits,misses=self.misses,embedding_calls=self.embedding_calls,
                entries=len(self.entries),vector_bytes=sum(map(len,self.entries.values())),evictions=self.evictions,
                persistence='none; process exit loses cache',max_entries=self.max_entries)

    def clear(self):
        with self.lock:self.entries.clear()


class CachedRetrieval:
    """Explicit research adapter, usable by all three existing RAG strategies.

    Wrap an already constructed isolated research RetrievalService. To roll back,
    restore ``wrapped.service``; never attach this adapter to the default app.
    """
    def __init__(self,service,cache):self.service=service;self.cache=cache
    def __getattr__(self,name):return getattr(self.service,name)
    def query(self,build_id,question):
        return self.service.query(build_id,question,query_embedding_cache=self.cache)
