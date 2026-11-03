"""Verify main, Production v1 and preserved directory names against P0 records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(archive):
    root = Path('/home/kenqia/my_folder/locomo-dynamic-memory')
    production = root.parent / 'locomo-worktrees/production-integration-20261101'
    changed = []
    manifest = json.loads((archive / 'main-file-manifest.json').read_text())
    for row in manifest:
        p = root / row['path']
        if row.get('missing'):
            okay = not p.exists()
        elif 'symlink' in row:
            okay = p.is_symlink() and os.readlink(p) == row['symlink']
        else:
            okay = p.is_file() and sha(p) == row['sha256'] and p.stat().st_mode & 0o777 == row['mode']
        if not okay:
            changed.append(row['path'])
    def git(directory, *args):
        return subprocess.check_output(['git', '-C', str(directory), *args])
    checks = {}
    for name, args in [('main-status.z', ('status', '--porcelain=v1', '-z', '--untracked-files=all')),
                       ('main-staged.patch', ('diff', '--cached', '--binary', '--full-index')),
                       ('main-unstaged.patch', ('diff', '--binary', '--full-index'))]:
        checks[name] = git(root, *args) == (archive / name).read_bytes()
    production_manifest = json.loads((archive / 'worktree-snapshots/production-integration-20261101.manifest.json').read_text())
    changed_production = [r['path'] for r in production_manifest if not (production / r['path']).is_file() or sha(production / r['path']) != r['sha256']]
    missing_directories = [p for p in json.loads((archive / 'unregistered-directories.json').read_text()) if not Path(p).is_dir()]
    production_head = git(production, 'rev-parse', 'HEAD').decode().strip()
    main_head = git(root, 'rev-parse', 'HEAD').decode().strip()
    checks['production_head'] = production_head == '915fac02f6b9296e331f913a1e78717cfa7e2df1'
    checks['main_head'] = main_head == 'f5a5dfdec5235d1c411cb5d4b525467e40fef415'
    checks['production_clean'] = not git(production, 'status', '--porcelain=v1')
    return {'passed': not changed and not changed_production and not missing_directories and all(checks.values()),
            'main_files_checked': len(manifest), 'main_changed_files': changed,
            'production_files_checked': len(production_manifest), 'production_changed_files': changed_production,
            'missing_preserved_directories': missing_directories, 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
