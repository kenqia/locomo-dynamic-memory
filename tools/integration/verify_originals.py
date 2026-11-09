"""Verify only paths captured before integration; never write original worktrees."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(directory):
    mismatches = []
    checked = 0
    for group in json.loads((directory / 'originals-manifest.json').read_text()):
        root = Path(group['root'])
        for item in group['files']:
            path = root / item['path']
            if not path.is_file() or sha256(path) != item['sha256']:
                mismatches.append(str(path))
            checked += 1
    git_changes = []
    for item in json.loads((directory / 'worktrees.json').read_text()):
        if not item['registered_worktree']:
            continue
        def git(*args):
            return subprocess.check_output(['git', '-C', item['path'], *args], text=True).strip()
        if git('rev-parse', 'HEAD') != item['head'] or git('status', '--porcelain') != item['status']:
            git_changes.append(item['path'])
    return {'checked_files': checked, 'changed_or_missing_files': mismatches,
            'changed_original_git_states': git_changes,
            'passed': not mismatches and not git_changes,
            'scope': 'Original tracked files, selected research artifacts, user nonignored files except .scratch and credential-related names; 57 original databases. Does not read credential files.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[2] / 'docs/integration/20261031')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.directory)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'checked_files': result['checked_files']}))
    raise SystemExit(0 if result['passed'] else 1)
