"""One isolated producer job; source code selected before importing the application."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    path.chmod(0o600)


def replay_query(packet, settings, model, scratch):
    """Use the real QueryService with fixed, previously observed retrieval adapters."""
    from locomo_memory.queries import QueryService, QueryFailure
    from locomo_memory.query_schemas import QueryRequest

    class ReplayDatabase:
        @contextmanager
        def connect(self):
            db = sqlite3.connect(scratch)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()

    if scratch.exists():
        raise ValueError('replay_database_already_exists')
    database = ReplayDatabase()
    with database.connect() as db:
        db.executescript('''CREATE TABLE build_versions(build_id TEXT PRIMARY KEY);
            CREATE TABLE current_state_projections(build_id TEXT,fingerprint TEXT);
            CREATE TABLE source_turns(source_id TEXT,dataset_id TEXT,sample_id TEXT,
                session_id TEXT,dia_id TEXT,speaker TEXT,session_time TEXT,text TEXT,position INTEGER);
            CREATE TABLE memory_relations(relation_id TEXT,build_id TEXT,relation_json TEXT);''')
        db.execute('INSERT INTO build_versions VALUES(?)', (packet['build_id'],))
        db.execute('INSERT INTO current_state_projections VALUES(?,?)',
                   (packet['build_id'], packet.get('projection_fingerprint', 'fixed-replay')))
        columns = ('source_id','dataset_id','sample_id','session_id','dia_id','speaker','session_time','text','position')
        db.executemany('INSERT INTO source_turns VALUES(?,?,?,?,?,?,?,?,?)',
                       [[s[k] for k in columns] for s in packet['sources']])
        db.executemany('INSERT INTO memory_relations VALUES(?,?,?)',
                       [(r['relation_id'], packet['build_id'], json.dumps(r)) for r in packet['relations']])
    versions = SimpleNamespace(pin=lambda *args: packet['build_id'])
    retrieval = SimpleNamespace(database=database, settings=settings,
        query=lambda *args: deepcopy(packet['initial']))
    expansion = SimpleNamespace(expand=lambda *args, **kwargs: deepcopy(packet['expanded']))
    service = QueryService(versions, retrieval, expansion, model)
    request = QueryRequest(**{k:packet[k] for k in ('dataset_id','sample_id','build_id','question')})
    try:
        return service.query(request)
    except QueryFailure as error:
        return service.get(error.trace_id)


def review_schema():
    from pydantic import BaseModel, ConfigDict, Field, model_validator, ValidationInfo
    from typing import Literal

    class Quote(BaseModel):
        model_config = ConfigDict(extra='forbid')
        source_id: str
        quote: str = Field(min_length=1)

    class Judgment(BaseModel):
        model_config = ConfigDict(extra='forbid')
        packet_id: str
        variant: Literal['X','Y']
        semantic_support: Literal['supported','unsupported','uncertain','not_executed']
        person_attribution: Literal['supported','unsupported','uncertain','not_executed']
        temporal_precision: Literal['supported','unsupported','uncertain','not_applicable','not_executed']
        missing_supported_fact: Literal['yes','no','uncertain','not_executed']
        reason: str = Field(min_length=1)
        quotes: list[Quote]

    class Review(BaseModel):
        model_config = ConfigDict(extra='forbid')
        judgments: list[Judgment]

        @model_validator(mode='after')
        def supplied_scope(self, info: ValidationInfo):
            context = info.context or {}
            expected = {(p['packet_id'], v) for p in context['packets'] for v in ('X','Y')}
            actual = [(j.packet_id,j.variant) for j in self.judgments]
            if len(actual)!=len(expected) or set(actual)!=expected:
                raise ValueError('review_scope_incomplete')
            sources = {p['packet_id']:{s['source_id']:s['text'] for s in p['sources']} for p in context['packets']}
            for j in self.judgments:
                if j.semantic_support!='not_executed' and not j.quotes:
                    raise ValueError('review_quote_required')
                if any(q.source_id not in sources[j.packet_id] or q.quote not in sources[j.packet_id][q.source_id] for q in j.quotes):
                    raise ValueError('review_quote_not_verbatim')
            return self
    return Review


def run_job(job, settings, model, scratch):
    if job['kind']=='query':
        return replay_query(job['packet'], settings, model, scratch)
    if job['kind']=='extract':
        from locomo_memory.memory_schemas import ExtractionBatch
        payload = dict(sample_id=job['sample_id'], sources=job['sources'])
        context = dict(sources={s['source_id']:s for s in job['sources']})
        if job['window']:
            from locomo_memory.extraction_window import WINDOW_VERSION
            payload.update(target_source_ids=job['target_ids'], extraction_window_version=WINDOW_VERSION)
            context['target_source_ids'] = job['target_ids']
        generation = model.generate('extract', payload, ExtractionBatch, context=context)
        return dict(outcome='succeeded', extraction=generation.value.model_dump(mode='json'),
                    operations={'extract':generation.metadata})
    schema = review_schema()
    generation = model.generate('boundary_review', dict(instructions=job['instructions'],
        packets=job['packets']), schema, context={'packets':job['packets']})
    return dict(outcome='succeeded', review=generation.value.model_dump(mode='json'),
                operations={'review':generation.metadata})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.producer/'src'))
    import httpx
    from locomo_memory.config import Settings
    from locomo_memory.m5_budget import BudgetTransport
    from locomo_memory.model import DeepSeekModel, ModelFailure, request_messages

    if args.output.exists():
        raise ValueError('job_already_recorded')
    job = json.loads(args.job.read_text())
    settings = Settings.model_validate(job['settings'])
    policy = dict(max_requests=64,max_usd='15',model='deepseek-flash',
        input_usd_per_million='0.30',output_usd_per_million='1.20',
        max_input_bytes=640000,max_output_tokens=32768)
    observed = []
    started = time.monotonic()
    delegate = httpx.HTTPTransport(retries=0)
    transport = BudgetTransport(args.ledger, delegate, **policy)

    class ObservedModel(DeepSeekModel):
        def generate(self, operation, payload, schema, **kwargs):
            messages = request_messages(operation,payload,schema)
            entry = dict(operation=operation, messages_sha256=hashlib.sha256(
                json.dumps(messages,ensure_ascii=False).encode()).hexdigest())
            observed.append(entry)
            def checkpoint(call):
                entry['latest_call'] = deepcopy(call)
                dump(args.output.with_suffix('.progress.json'), observed)
            kwargs['on_call'] = checkpoint
            try:
                value = super().generate(operation,payload,schema,**kwargs)
                entry['metadata'] = value.metadata
                return value
            except ModelFailure as error:
                entry['metadata'] = error.metadata
                raise

    try:
        result = run_job(job,settings,ObservedModel(settings,transport=transport),args.output.with_suffix('.sqlite3'))
    except ModelFailure as error:
        result = dict(outcome='failed',error={'code':error.code},operations={'failed':error.metadata})
    finally:
        delegate.close()
    result.update(job_id=job['job_id'],kind=job['kind'], observations=observed,
                  job_sha256=hashlib.sha256(args.job.read_bytes()).hexdigest(),
                  producer=job['producer'],elapsed_seconds=time.monotonic()-started)
    dump(args.output,result)
    print(json.dumps({'job':job['job_id'],'outcome':result['outcome']},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
