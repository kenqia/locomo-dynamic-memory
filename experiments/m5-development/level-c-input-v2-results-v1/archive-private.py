"""Archive the completed input v2 evidence locally, without logs or credentials.

Run from this worktree with the existing offline guard. All original text stays
under ignored var/. SQLite backup includes committed WAL content. This program
does not regenerate answers, score Gold, or contact a provider.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / 'var/m5-development/level-c-input-v2-preparation-v1'
REVIEW = ROOT / 'var/m5-development/level-c-input-v2-source-review-v1'
DEST = ROOT / 'var/m5-development/level-c-input-v2-raw-terminal-v1.tar.gz'
REPORT = Path(__file__).with_name('private-archive-report.json')
STAGE_FILES = (
    'authorization.json', 'build-identities.json', 'embedding-preflight.json',
    'execution-started.json', 'generation-freeze.json', 'inputs.json', 'plan.json',
    'pre-execution-integrity-v1.json', 'preparation-verification.json',
    'pricing-before-execution-v1.json', 'pricing-before-execution-v1.md',
    'pricing-recheck.json', 'pricing-recheck.md', 'sample.json', 'scores.json',
    'settings.json', 'terminal-audit-v1.json', 'user-authorization-receipt-v1.json',
    'user-authorization-receipt.json',
)
REVIEW_FILES = (
    'manifest.json', 'packets.json', 'private-mapping.json', 'review-template.json',
    'reviews-conv26-30-v1.json', 'reviews-conv41-42-v1.json', 'independent-reviews.json',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_member(entry):
    assert entry.isfile()
    entry.mode = 0o600
    return entry


def logical_snapshot(path):
    digest = hashlib.sha256()
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        digest.update(json.dumps(schema, ensure_ascii=False).encode())
        for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            rows = sorted(json.dumps(row, ensure_ascii=False, default=str)
                          for row in db.execute('SELECT * FROM ' + quoted))
            digest.update(json.dumps([name, rows], ensure_ascii=False).encode())
    return digest.hexdigest()


def main():
    assert not DEST.exists() and not REPORT.exists(), 'preserve_existing_archive'
    semantic = json.loads(Path(__file__).with_name('semantic-review-summary.json').read_text())
    assert semantic['completed'] and semantic['summary']['overall']['reviewed'] == 200
    frozen = json.loads((STAGE / 'generation-freeze.json').read_text())
    assert semantic['generation_freeze_sha256'] == sha(STAGE / 'generation-freeze.json')
    assert len(frozen['item_hashes']) == 200
    selected = {'stage/' + name: STAGE / name for name in STAGE_FILES}
    selected.update({'review/' + name: REVIEW / name for name in REVIEW_FILES})
    for name, expected in frozen['item_hashes'].items():
        path = STAGE / name
        assert path.parent == STAGE / 'items' and sha(path) == expected
        selected['stage/' + name] = path
    assert all(p.is_file() and not p.is_symlink() for p in selected.values())
    original_hashes = {name: sha(path) for name, path in selected.items()}
    databases = ('memory.sqlite3', 'physical-requests.sqlite3')
    before = {name: logical_snapshot(STAGE / name) for name in databases}
    with tempfile.TemporaryDirectory(prefix='input-v2-archive-', dir=DEST.parent) as tmp:
        for name in databases:
            backup = Path(tmp) / name
            with sqlite3.connect((STAGE / name).as_uri() + '?mode=ro', uri=True) as source:
                with sqlite3.connect(backup) as target:
                    source.backup(target)
            assert logical_snapshot(backup) == before[name], 'backup_logical_mismatch'
            selected['stage/' + name] = backup
        members = {name: dict(sha256=sha(path), bytes=path.stat().st_size)
                   for name, path in sorted(selected.items())}
        internal = json.dumps(dict(members=members, database_logical_sha256=before), indent=2).encode()
        descriptor = os.open(DEST, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'wb') as stream, tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, path in sorted(selected.items()):
                archive.add(path, arcname=name, recursive=False, filter=private_member)
            entry = tarfile.TarInfo('archive-manifest.json')
            entry.mode = 0o600
            entry.size = len(internal)
            archive.addfile(entry, io.BytesIO(internal))
        with tarfile.open(DEST, 'r:gz') as archive:
            assert set(archive.getnames()) == set(members) | {'archive-manifest.json'}
            assert all(entry.isfile() and entry.mode == 0o600 for entry in archive.getmembers())
            for name, meta in members.items():
                data = archive.extractfile(name).read()
                assert len(data) == meta['bytes'] and hashlib.sha256(data).hexdigest() == meta['sha256']
            assert archive.extractfile('archive-manifest.json').read() == internal
    after = {name: logical_snapshot(STAGE / name) for name in databases}
    assert before == after, 'source_database_changed'
    assert all(sha(selected[name]) == value for name, value in original_hashes.items())
    result = dict(archive=str(DEST.relative_to(ROOT)), sha256=sha(DEST), bytes=DEST.stat().st_size,
                  verified_members=len(members) + 1, members=members,
                  archive_mode_octal=oct(DEST.stat().st_mode & 0o777),
                  database_logical_sha256=before, source_logical_snapshots_unchanged=True,
                  sqlite_backup_includes_committed_wal=True,
                  excluded=['WAL/SHM sidecars', 'runtime locks', 'raw process logs', 'credentials'],
                  private_original_text_committed=False)
    REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'members'}))


if __name__ == '__main__':
    main()
