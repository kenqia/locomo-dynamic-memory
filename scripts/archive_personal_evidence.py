#!/usr/bin/env python3
"""Local archival snapshot. Excludes credentials/logs/caches; never deletes sources."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[1]
BASE = Path('/home/kenqia/my_folder')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def forbidden(path):
    lower = path.name.lower()
    return (lower.startswith('.env') or any(s in lower for s in ('auth.json', 'cookie', 'credential', 'session-token', 'stdout', 'stderr'))
            or path.suffix.lower() in {'.env', '.log', '.pem', '.key', '.p12'}
            or lower in {'auth.toml', 'token.json', 'tokens.json', 'headers.json', 'secrets.json'} or lower.endswith(('-wal', '-shm')))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-only', action='store_true')
    args = p.parse_args()
    destination = args.output.resolve()
    destination.mkdir(parents=True, mode=0o700, exist_ok=True)
    destination.chmod(0o700)
    archive_path = destination / 'research-evidence.tar.gz'
    if archive_path.exists():
        raise SystemExit('Refusing to overwrite an archive; choose a new output directory')
    roots = [BASE / 'locomo-dynamic-memory'] + sorted((BASE / 'locomo-worktrees').iterdir())
    inventory, omitted, worktrees = [], [], []
    with tempfile.TemporaryDirectory(prefix='locomo-archive-snapshots-') as scratch:
        with tarfile.open(archive_path, 'x:gz', compresslevel=1) as archive:
            for root in roots:
                if not root.is_dir():
                    continue
                try:
                    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
                    state = subprocess.check_output(['git', 'status', '--porcelain=v1', '-z'], cwd=root)
                except subprocess.CalledProcessError:
                    head, state = 'unavailable', b''
                worktrees.append({'path': str(root), 'head': head, 'status_sha256_basis': 'git status --porcelain=v1 -z raw bytes',
                                  'status_sha256': hashlib.sha256(state).hexdigest(), 'dirty_entries': len([x for x in state.split(b'\0') if x]),
                                  'category': 'A' if root == REPO else ('C' if root.name == 'locomo-dynamic-memory' else 'B')})
                # Evidence/workspace documents only; no virtualenvs, model weights, logs or credentials.
                targets = [root / name for name in ('src', 'tools', 'tests', 'scripts')] if args.source_only else [root / 'var', root / 'docs', root / 'experiments', root / 'process']
                if root == REPO or (args.source_only and root.name == 'locomo-dynamic-memory'):
                    targets = []  # Release evidence is packaged/versioned separately.
                for target in targets:
                    if not target.exists():
                        continue
                    for folder, dirs, files in os.walk(target, followlinks=False):
                        dirs[:] = [d for d in dirs if d not in {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.cache', 'ollama-models'} and not Path(folder, d).is_symlink()]
                        for name in sorted(files):
                            path = Path(folder, name)
                            relative = path.relative_to(BASE).as_posix()
                            if path.suffix.lower() == '.pyc':
                                continue
                            if path.is_symlink() or forbidden(path):
                                omitted.append({'path': relative, 'reason': 'protected log/credential, live WAL/SHM or symlink; original preserved', 'bytes': path.lstat().st_size})
                                continue
                            # Package dependency checkouts are rebuildable C/E, not experimental outputs.
                            if any(part.startswith(('hindsight-', 'propmem-')) for part in path.relative_to(target).parts):
                                omitted.append({'path': relative, 'reason': 'external checkout/cache; original preserved', 'bytes': path.stat().st_size})
                                continue
                            before = path.stat()
                            archived = path
                            kind = path.suffix.lower()
                            if kind in {'.sqlite3', '.sqlite', '.db'}:
                                archived = Path(scratch) / (hashlib.sha256(relative.encode()).hexdigest() + '.sqlite3')
                                try:
                                    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as source:
                                        with sqlite3.connect(archived) as snapshot:
                                            source.backup(snapshot)
                                            if snapshot.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                                                raise ValueError('SQLite quick_check failed')
                                except (sqlite3.Error, ValueError):
                                    omitted.append({'path': relative, 'reason': 'SQLite snapshot unavailable; original preserved', 'bytes': before.st_size})
                                    continue
                            digest = sha(archived)
                            info = archive.gettarinfo(str(archived), arcname=relative)
                            info.mode, info.uid, info.gid, info.uname, info.gname = 0o600, 0, 0, '', ''
                            with archived.open('rb') as stream:
                                archive.addfile(info, stream)
                            after = path.stat()
                            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                                raise RuntimeError('Source changed during archive; preserve partial archive and investigate')
                            inventory.append({'path': relative, 'sha256': digest, 'bytes': archived.stat().st_size,
                                              'kind': kind, 'source_preserved': True,
                                              'copy_basis': 'SQLite consistent backup' if archived != path else 'byte-for-byte'})
        archive_path.chmod(0o600)
        # Full stream restore-equivalence check without writing controlled bodies to disk.
        actual = []
        with tarfile.open(archive_path, 'r:gz') as archive:
            for member in archive:
                with archive.extractfile(member) as stream:
                    actual.append((member.name, hashlib.file_digest(stream, 'sha256').hexdigest(), member.size))
        expected = [(r['path'], r['sha256'], r['bytes']) for r in inventory]
        if actual != expected:
            raise RuntimeError('Archive restore hash verification failed')
    manifest = {'version': 'private-research-archive-v1', 'status': 'PASS', 'deletions': 0,
                'scope': 'all existing docs/experiments/process and experimental var in discovered sibling directories; protected logs/credentials/caches omitted and preserved in place',
                'files': [{'path': archive_path.name, 'sha256': sha(archive_path), 'bytes': archive_path.stat().st_size, 'members': inventory}],
                'worktrees': worktrees, 'omitted': omitted,
                'restore_verification': 'all member bytes streamed and SHA/size/order compared to source snapshot inventory',
                'provider_requests': 0}
    out = destination / 'private-archive-manifest.json'
    out.write_text(json.dumps(manifest, indent=2) + '\n');out.chmod(0o600)
    summary = {'status': 'PASS', 'archive_path': str(archive_path), 'archive_sha256': manifest['files'][0]['sha256'],
               'archive_bytes': archive_path.stat().st_size, 'members': len(inventory), 'member_bytes': sum(r['bytes'] for r in inventory),
               'omitted_files': len(omitted), 'deletions': 0, 'restore_verification': manifest['restore_verification'],
               'worktrees': worktrees}
    (REPO / 'experiments/personal-release/local-archive-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='worktrees'},indent=2))


if __name__ == '__main__':
    main()
