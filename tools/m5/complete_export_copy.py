"""Complete conv-43 only in a new local copy, then strictly export five Builds.

No generation, embeddings, query, evaluation, credentials, or remote publication.
The original paid relation stage remains related and unpublished.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.exports import ExportService, read_bundle
from locomo_memory.versions import VersionsService
from tools.m5.holdout_relations import NoProvider
from tools.m5.offline import sha
from tools.m5.relation_audit import audit, connect, table_digest

ROOT = Path(__file__).resolve().parents[2]
RELATION = ROOT.parent / 'm5-final-development-20261104/var/m5-development/conv43-relation-proposal-v1'
DEVELOPMENT = ROOT.parent / 'm5-final-input-v2-20261104/var/m5-development/level-c-input-v2-preparation-v1'
OUTPUT = ROOT / 'var/m5-development/five-build-export-v1'
REPORT = ROOT / 'experiments/m5-development/five-build-export-v1.json'
DEV = ('conv-26', 'conv-30', 'conv-41', 'conv-42')
EMPTY = ('candidate_queries', 'candidate_expansions', 'query_traces',
         'evaluation_inputs', 'evaluation_runs', 'evaluation_run_items')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def write_new(path, value):
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def no_annotations(path):
    """Inspect only SQL counts, never return annotation values to Python."""
    with connect(path) as db:
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'import_artifacts' not in names:
            return 0
        count = db.execute("""SELECT COUNT(*) FROM import_artifacts a,
            json_tree(a.annotations_json) j WHERE j.key IN
            ('qa','answer','answers','evidence','event_summary','observation','session_summary')
            AND j.type!='null'""").fetchone()[0]
        require(count == 0, 'source_annotations_must_be_null')
        return count


def logical(path):
    # Snapshot only after SQL establishes that no annotation payload exists.
    # Whole-table hashes are private digests; no source/provider text is emitted.
    no_annotations(path)
    with connect(path) as db:
        schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables = {name: table_digest(db, (name,)) for name in names}
        return dict(schema_sha256=hashlib.sha256(json.dumps([tuple(r) for r in schema]).encode()).hexdigest(),
                    tables=tables)


def zero_queries(db):
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name in EMPTY:
        if name in names:
            require(db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] == 0, 'copy_query_or_evaluation_exists')


def call_profile(calls):
    effort = Counter()
    for call in calls:
        thinking = call.get('thinking')
        if thinking == {'type': 'disabled'}:
            effort['disabled'] += 1
        elif thinking == {'type': 'enabled'}:
            effort[str(call.get('reasoning_effort', 'unknown'))] += 1
        else:
            effort['unknown'] += 1
    return dict(records=len(calls), thinking_efforts=dict(effort),
                requested_models=dict(Counter(c.get('requested_model', 'unknown') for c in calls)),
                returned_models=dict(Counter(c.get('returned_model') or 'not_reported' for c in calls)))


def lineage(db, build_id, settings, build_metadata):
    fragments = [json.loads(r[0]) for r in db.execute(
        'SELECT model_metadata_json FROM build_fragments WHERE build_id=?', (build_id,))]
    extraction = [call for metadata in fragments for call in metadata.get('calls', [])]
    relations = [json.loads(r[0]) for r in db.execute('''SELECT c.metadata_json
        FROM relation_provider_calls c JOIN relation_tasks t USING(task_id)
        WHERE t.build_id=?''', (build_id,))]
    # Older complete Builds predate normalized provider-attempt storage. Their
    # task metadata contains the physical records; do not claim zero calls.
    relation_source = 'relation_provider_calls.metadata_json'
    if not relations:
        metadata = [json.loads(r[0]) for r in db.execute(
            'SELECT metadata_json FROM relation_tasks WHERE build_id=?', (build_id,))]
        relations = [call for task in metadata for call in task.get('calls', [])]
        relation_source = 'legacy_relation_tasks.metadata_json.calls'
    return dict(build_model_metadata={k: build_metadata[k] for k in
                    ('requested_model', 'known_service_version', 'run_date', 'returned_models', 'artifact_versions')
                    if k in build_metadata},
                frozen_settings_thinking={k: v for k, v in settings.items() if k.endswith('_thinking_effort')},
                extraction_attempts=call_profile(extraction), relation_attempts=call_profile(relations),
                relation_attempt_records_source=relation_source,
                limitation='historical metadata retained; mutable model aliases are not immutable pins; no claim of all-chain thinking disabled')


def export_checked(bundle, db, source_database, original_status):
    require(bundle.schema_version == 'memory-export-v2', 'strict_v2_required')
    raw = bundle.model_dump(mode='json')
    path = OUTPUT / 'exports' / (bundle.build.sample_id + '.json')
    write_new(path, raw)
    roundtrip = MemoryExport.model_validate_json(path.read_text())
    require(roundtrip == bundle and roundtrip.model_dump(mode='json') == raw, 'strict_export_roundtrip_changed')
    bid = bundle.build.build_id
    row = db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?', (bid,)).fetchone()
    return dict(sample_id=bundle.build.sample_id, build_id=bid, status='complete',
        original_source_status=original_status, schema_version=bundle.schema_version,
        relation_contract_version=bundle.relation_contract_version,
        dataset_id=bundle.build.dataset_id, dataset_source_sha256=bundle.build.source_sha256,
        build_fingerprint=bundle.build.fingerprint,
        source_database=str(source_database), source_database_main_file_sha256=sha(source_database),
        export=str(path.relative_to(ROOT)), export_sha256=sha(path), export_bytes=path.stat().st_size,
        memories=len(bundle.memories), evidence_union_source_turns=len(bundle.sources),
        conversation_source_turns=db.execute('SELECT COUNT(*) FROM source_turns WHERE dataset_id=? AND sample_id=?',
                                          (bundle.build.dataset_id, bundle.build.sample_id)).fetchone()[0],
        relations=len(bundle.relations), relation_labels=dict(Counter(r.label for r in bundle.relations)),
        fragments=dict(db.execute('SELECT status,COUNT(*) FROM build_fragments WHERE build_id=? GROUP BY status', (bid,))),
        index=bundle.index.model_dump(mode='json'),
        projection=dict(fingerprint=bundle.projection.fingerprint, version=bundle.projection.projection_version,
                        cutoff=bundle.projection.cutoff,
                        counts={k: len(getattr(bundle.projection, k)) for k in
                            ('current_states', 'historical_states', 'events', 'nonfactual', 'conflicts', 'conditional_relations')}),
        lineage=lineage(db, bid, raw['build']['config'], json.loads(row[0])), strict_roundtrip=True)


def run():
    require(not OUTPUT.exists() and not REPORT.exists(), 'preserve_existing_output')
    plan = json.loads((RELATION / 'plan.json').read_text())
    dev_plan = json.loads((DEVELOPMENT / 'plan.json').read_text())
    source, ledger = RELATION / 'memory.sqlite3', RELATION / 'physical-requests.sqlite3'
    dev_source = DEVELOPMENT / 'memory.sqlite3'
    # relation_audit also checks the original indexed snapshot; guard its annotations first.
    no_annotations(Path(plan['source_index_stage']) / 'memory.sqlite3')
    source_before, dev_before = logical(source), logical(dev_source)
    ledger_before = logical(ledger)
    audited = audit(RELATION)
    saved_audit = json.loads((RELATION / 'terminal-audit-v1.json').read_text())
    require(audited == saved_audit and audited['status'] == 'related' and not audited['published'],
            'original_relation_terminal_audit_mismatch')
    settings_bytes = (RELATION / 'settings.json').read_bytes()
    require(sha(RELATION / 'settings.json') == plan['settings_sha256'], 'source_settings_changed')
    settings = Settings.model_validate_json(settings_bytes)
    require(settings.relation_thinking_effort == 'high', 'historical_relation_effort_changed')
    OUTPUT.mkdir(parents=True, mode=0o700, exist_ok=False)
    (OUTPUT / 'exports').mkdir(mode=0o700)
    write_new(OUTPUT / 'source-relation-audit.json', audited)
    write_new(OUTPUT / 'settings.json', settings.snapshot())
    require((OUTPUT / 'settings.json').read_bytes() == settings_bytes, 'settings_copy_not_byte_identical')
    target = OUTPUT / 'memory.sqlite3'
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with connect(source) as origin, sqlite3.connect(target) as destination:
        origin.backup(destination)
    require(logical(target) == source_before, 'backup_not_logically_identical')
    bid = plan['build_id']
    with connect(target) as db:
        zero_queries(db)
        before_builds = {r['build_id']: dict(r) for r in db.execute('SELECT * FROM build_versions')}
        require(len(before_builds) == 2 and before_builds[bid]['sample_id'] == 'conv-43'
                and before_builds[bid]['status'] == 'related', 'copy_build_scope_changed')
        require({r['sample_id']: r['status'] for r in before_builds.values()} ==
                {'conv-43': 'related', 'conv-44': 'failed'}, 'copy_other_build_changed')
        require(db.execute('SELECT COUNT(*) FROM active_versions').fetchone()[0] == 0, 'source_already_published')
    # Keep settings.db_path and fingerprint exactly as frozen; explicitly route storage to copy.
    builds = BuildService(Database(target), settings, NoProvider())
    builds.require_current_contract(builds.get(bid))
    versions = VersionsService(builds)
    completed = versions.publish(bid)
    require(versions.pin(completed['dataset_id'], 'conv-43', bid) == bid, 'copy_pin_failed')
    bundle = ExportService(versions).export(bid)
    with connect(target) as db:
        zero_queries(db)
        after_builds = {r['build_id']: dict(r) for r in db.execute('SELECT * FROM build_versions')}
        require(set(after_builds) == set(before_builds), 'copy_build_identity_changed')
        allowed = {'status', 'phase', 'updated_at'}
        for identity, before in before_builds.items():
            after = after_builds[identity]
            if identity == bid:
                require(after['status'] == after['phase'] == 'complete', 'copy_completion_failed')
                require({k: v for k, v in before.items() if k not in allowed} ==
                        {k: v for k, v in after.items() if k not in allowed}, 'copy_build_contract_changed')
            else:
                require(before == after, 'conv44_row_changed')
        require([tuple(r) for r in db.execute('SELECT * FROM active_versions')] ==
                [(completed['dataset_id'], 'conv-43', bid)], 'copy_active_version_scope_changed')
        results = [export_checked(bundle, db, source, 'related')]
    copy_after = logical(target)
    require(copy_after['schema_sha256'] == source_before['schema_sha256'], 'copy_schema_changed')
    require(set(copy_after['tables']) == set(source_before['tables']), 'copy_tables_changed')
    changed = sorted(name for name in source_before['tables']
                     if source_before['tables'][name] != copy_after['tables'][name])
    require(changed == ['active_versions', 'build_versions'], 'unexpected_copy_mutation')
    require(set(dev_plan['pins']) == set(DEV), 'development_pin_scope_changed')
    with connect(dev_source) as db:
        for conv in DEV:
            identity = dev_plan['pins'][conv]
            row = dict(db.execute('SELECT * FROM build_versions WHERE build_id=?', (identity,)).fetchone())
            require(row['sample_id'] == conv and row['status'] == 'complete', 'development_pin_incomplete')
            row['config'] = json.loads(row.pop('config_json'))
            results.append(export_checked(read_bundle(db, row), db, dev_source, 'complete'))
    require(logical(source) == source_before and logical(dev_source) == dev_before, 'source_database_changed')
    require(logical(ledger) == ledger_before, 'source_ledger_changed')
    require(audit(RELATION) == saved_audit, 'original_relation_final_audit_changed')
    require(len(results) == 5 and {r['sample_id'] for r in results} == {*DEV, 'conv-43'}, 'five_exports_required')
    result = dict(status='five_strict_exports_complete_local_copy_only', builds=sorted(results, key=lambda r: r['sample_id']),
        authorization_basis='user continue-total-task authorization; reversible local scratch completion within six-Build acceptance; no extension of original paid relation stage',
        source_relation_stage=str(RELATION), source_relation_plan_sha256=sha(RELATION / 'plan.json'),
        source_relation_terminal_audit_sha256=sha(RELATION / 'terminal-audit-v1.json'),
        source_relation_audit_full_object_equal=True, source_relation_status='related', source_relation_published=False,
        original_sources_and_ledger_unchanged=True, sqlite_backup_includes_committed_wal=True,
        source_relation_logical_before_after=source_before, development_logical_before_after=dev_before,
        source_ledger_logical_before_after=ledger_before, copy_logical_after=copy_after,
        copy_changed_tables=changed, copy_build_changed_columns=['status', 'phase', 'updated_at'],
        conv44_full_build_row_unchanged=True, all_other_tables_and_provider_metadata_unchanged=True,
        copied_database=str(target.relative_to(ROOT)), copied_database_main_file_sha256=sha(target),
        source_settings_sha256=sha(RELATION / 'settings.json'), copied_settings_sha256=sha(OUTPUT / 'settings.json'),
        script_sha256=sha(Path(__file__)), private_directory_mode=oct(OUTPUT.stat().st_mode & 0o777),
        private_file_modes={str(p.relative_to(OUTPUT)): oct(p.stat().st_mode & 0o777)
                            for p in [target, OUTPUT / 'settings.json', *sorted((OUTPUT / 'exports').glob('*.json'))]},
        provider_requests=0, credentials_accessed=False, query_or_evaluation_run=False,
        holdout_annotations_nonnull_sql_count=0, holdout_qa_evidence_answers_read=False,
        remote_write=False, production_database_written=False, level_e_executed=False,
        sixth_build='conv-44 remains failed; six complete Builds not achieved',
        limitation='strict source/schema/index/projection validity and local copy publication do not prove semantic relation accuracy, QA quality or release readiness')
    require(result['private_directory_mode'] == '0o700' and all(v == '0o600' for v in result['private_file_modes'].values()),
            'private_permissions_incorrect')
    write_new(OUTPUT / 'summary.json', result)
    write_new(REPORT, result)
    print(json.dumps(dict(status=result['status'], exports=len(results), provider_requests=0,
                          original_relation_status='related', report=str(REPORT.relative_to(ROOT)), report_sha256=sha(REPORT))))
    return result


if __name__ == '__main__':
    run()
