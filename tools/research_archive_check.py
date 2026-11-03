"""Validate the public research-process archive without models or runtime access."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/research-process'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest = json.loads((DOCS / 'upload-allowlist.json').read_text())
    errors = []
    payload_paths = [r['path'] for r in manifest['files']]
    expected = set(payload_paths + manifest['control_files'])
    assert len(payload_paths) == len(set(payload_paths))
    for rel in expected:
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
    tracked = set(subprocess.check_output(
        ['git', '-C', str(ROOT), 'ls-files', '-z']).decode().strip(chr(0)).split(chr(0)))
    # During preparation, allow new files only when explicitly listed in the manifest.
    extra = tracked - expected
    if extra:
        errors.extend('unallowlisted_tracked:' + p for p in sorted(extra))
    checks = {}
    for line in (DOCS / 'SHA256SUMS').read_text().splitlines():
        sha, rel = line.split('  ', 1)
        assert rel not in checks
        checks[rel] = sha
        if not (ROOT / rel).is_file() or digest(ROOT / rel) != sha:
            errors.append('checksum:' + rel)
    assert set(checks) == expected - {'docs/research-process/SHA256SUMS'}
    for row in manifest['files']:
        path = ROOT / row['path']
        if not path.is_file() or path.is_symlink() or digest(path) != row['sha256']:
            errors.append('file_integrity:' + row['path'])
    for path in DOCS.rglob('*.json'):
        json.loads(path.read_text())
    links = 0
    for path in [ROOT / 'README.md', *DOCS.rglob('*.md')]:
        # Archive local links use no title or whitespace in the destination.
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            target = target.split('#')[0]
            links += 1
            if not (path.parent / target).resolve().is_file():
                errors.append('link:' + str(path.relative_to(ROOT)) + ':' + target)
    entries = json.loads((DOCS / 'experiments.json').read_text())['entries']
    assert len({e['id'] for e in entries}) == len(entries) == 42
    sources = {r['id']: r for r in json.loads((DOCS / 'source-index.json').read_text())}
    for e in entries:
        for ref in e['evidence']:
            assert ref['id'] in sources
            assert ref['sha256'] == sources[ref['id']]['source_sha256']
            assert (DOCS / ref['public']).is_file()
    m = json.loads((DOCS / 'metrics.json').read_text())
    b = m['baseline']
    assert b['planned_combinations'] == b['succeeded'] + b['failed'] + b['unknown'] == 3028
    p = m['paired']
    assert sum(p['pair_states'].values()) == 757
    assert p['dynamic_wins'] + p['hybrid_wins'] + p['ties'] == p['comparable'] == 705
    assert abs(p['paired_dynamic_mean'] - p['paired_hybrid_mean'] - p['mean_paired_delta']) < 1e-12
    assert p['hybrid']['full_denominator_score'] is None
    assert p['dynamic']['full_denominator_score'] < p['hybrid']['full_denominator_bounds'][0]
    extra = m['additional_reported_aggregates']
    for name in ('supplemental', 'answer_repair'):
        r = extra[name]
        assert r['planned'] == r['succeeded'] + r['failed'] + r['unknown']
    r = extra['e6a_offline']
    assert round(100 * (1-r['e6a_local_input_estimate']/r['control_local_input_estimate']), 2) == 34.31
    assert r['new_provider_calls'] == 0 and r['semantic_quality'] is None
    summary = {'allowlisted_files': len(manifest['files']), 'local_links_checked': links,
               'explorations': len(entries), 'source_versions': len(sources), 'errors': errors,
               'new_provider_calls': 0, 'review': 'automated integrity and arithmetic; not semantic or human review'}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
