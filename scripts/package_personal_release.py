#!/usr/bin/env python3
"""Build a public candidate from explicit files, scan it, hash every member."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def public_paths():
    root_files = ['README.md', 'CONTEXT.md', 'AGENTS.md', '.python-version', 'pyproject.toml', 'uv.lock', 'config.example.toml',
                  'deliverables/m5-personal-candidate/README.md',
                  'memory-export-schema.json', 'six-memory-exports-manifest.json', 'RELEASE_MANIFEST.md',
                  'RELEASE_CODE_LINEAGE.md', 'RELEASE_COMMIT_MAP.json', 'RELEASE_COMPONENT_MATRIX.md',
                  'PERSONAL_EXPERIMENT_SUMMARY.md', 'EXPERIMENT_ARCHIVE_INDEX.md', 'LOCAL_ARCHIVE_AND_CLEANUP_PLAN.md',
                  'TEAM_INTEGRATION_HANDOFF.md']
    roots = ['src', 'tools', 'tests', 'scripts', 'docs/app', 'docs/agents', 'docs/adr', 'docs/m5-development', 'docs/release', 'docs/supplement', 'experiments/m5-development', 'experiments/personal-release']
    paths = [ROOT / name for name in root_files if (ROOT / name).is_file()]
    for name in roots:
        for path in (ROOT / name).rglob('*'):
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:
                continue
            if path.suffix.lower() not in {'.py', '.sh', '.md', '.json', '.txt', '.xml', '.png', '.pdf', '.dot', '.tex'} and path.name != 'personal-release':
                continue
            if path.name in {'public-package-manifest.json', 'public-package-scan.json', 'answer-source-turns.json', 'test_answer_regressions.py', 'test_imports.py'}:
                continue
            # Old/raw stdout/stderr and protected payloads are never public artifacts.
            if any(token in path.name.lower() for token in ('stderr', 'stdout', 'wire-capture', 'gold.json')):
                continue
            paths.append(path)
    # Historical analysis code is needed during pytest collection; never bundle its raw outputs.
    paths += list((ROOT / 'experiments').rglob('*.py'))
    # Preserve license/provenance without raw conversation/QA.
    paths += [ROOT / 'data/raw/locomo' / n for n in ('LICENSE.txt', 'README.md', 'provenance.json')]
    return sorted(set(paths))


def scan(paths):
    findings = []
    credential = re.compile(rb'(?:(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    # Match long upstream literal text/answers silently, reporting only file/count.
    raw = ROOT / 'data/raw/locomo/locomo10.json'
    turns = []
    questions = set()
    complete_turns = set()
    if raw.exists():
        for conversation in json.loads(raw.read_text()):
            questions.update(q['question'].encode() for q in conversation.get('qa', []) if isinstance(q.get('question'), str) and len(q['question']) >= 18)
            c = conversation['conversation']
            for key, value in c.items():
                if re.fullmatch(r'session_\d+', key):
                    turns.extend(t['text'] for t in value if len(t.get('text', '')) >= 80)
                    complete_turns.update(re.sub(rb'\s+', b' ', t['text'].encode()) for t in value if len(t.get('text', '')) >= 18)
        phrases = {t[i:i+80].encode() for t in turns for i in range(0, len(t)-79, 40)}
    else:
        phrases = set()
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        if credential.search(data):
            findings.append({'path': relative, 'risk': 'credential-shaped string; value suppressed'})
        text = data
        if path.suffix == '.pdf':
            text = subprocess.check_output(['pdftotext', '-layout', str(path), '-'])
        if path.suffix in {'.py', '.md', '.txt', '.json', '.pdf'}:
            normalized = re.sub(rb'\s+', b' ', text)
            matches = sum(phrase in normalized for phrase in phrases)
            if matches:
                findings.append({'path': relative, 'risk': 'upstream long literal content', 'matches': matches})
            short_source_matches = sum(turn in normalized for turn in complete_turns)
            if short_source_matches:
                findings.append({'path': relative, 'risk': 'upstream complete Source Turn; value suppressed', 'matches': short_source_matches})
            qa_matches = sum(question in normalized for question in questions)
            if qa_matches:
                findings.append({'path': relative, 'risk': 'upstream literal QA question; value suppressed', 'matches': qa_matches})
    return findings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--scan-only', action='store_true')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    paths = public_paths()
    findings = scan(paths)
    catalog_available = (ROOT / 'data/raw/locomo/locomo10.json').is_file()
    report = {'status': ('PASS' if catalog_available else 'PARTIAL') if not findings else 'BLOCKED', 'files': len(paths), 'findings': findings,
              'upstream_literal_catalog_available': catalog_available,
              'known_upstream_literal_check': 'PASS' if catalog_available and not findings else ('FINDINGS' if catalog_available else 'NOT_RUN'),
              'excluded': ['var/**', '.git/**', '.env*', 'LoCoMo raw conversation and QA', 'private Gold/Trace/raw wire', 'docs/sources/**', 'old deliverables/**', 'tests/test_answer_regressions.py and tests/test_imports.py: upstream derived cases'],
              'scope': 'credential-shaped bytes, exact upstream Source spans >=80 characters and complete Source Turns >=18 characters, official QA question strings >=18 characters, including Python; no private Gold read, not a guarantee against unknown private content'}
    (args.output/'public-package-scan.json').write_text(json.dumps(report, indent=2)+'\n')
    if args.scan_only:
        print(json.dumps(report, indent=2));return
    if findings:
        raise SystemExit('Public package blocked by findings; inspect metadata-only scan report')
    archive = args.output/'m5-personal-public.tar.gz'
    if archive.exists():
        raise SystemExit('Refusing to overwrite candidate archive')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    inventory = [{'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in paths]
    # Reviewer can verify evidence without private files, network or keys.
    evidence = json.dumps({'version': 'public-evidence-v1', 'files': inventory}, indent=2).encode()+b'\n'
    (args.output/'public-evidence-manifest.json').write_bytes(evidence)
    with tarfile.open(archive, 'x:gz') as tar:
        for path in paths:
            info=tar.gettarinfo(str(path),arcname=str(path.relative_to(ROOT)))
            info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            with path.open('rb') as stream:tar.addfile(info,stream)
        import io
        info=tarfile.TarInfo('public-evidence-manifest.json');info.size=len(evidence);info.mtime=0;info.mode=0o644
        tar.addfile(info,io.BytesIO(evidence))
    manifest={'kind':'Personal Core Release — pending team integration','source_commit':source_commit,
              'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
              'archive':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive),
              'files':inventory,'public_scan':report,'controlled_data_included':False}
    (args.output/'public-package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in {'files','public_scan'}},indent=2))


if __name__=='__main__':main()
