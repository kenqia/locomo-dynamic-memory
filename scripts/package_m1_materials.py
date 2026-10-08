#!/usr/bin/env python3
"""Package M1 evidence by the six categories in m1-process-index.md."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urlsplit
from posixpath import normpath, join, dirname
import csv
import hashlib
import io
import json
import re
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / 'process/m1'
OUTPUT = ROOT / 'deliverables/m1'
BASE = 'PROJECT-MILESTONE1-3-在阴雨天游泳'

# Explicit sources only; each category is flat inside the archive.
CATEGORIES = {
    '首次会议': ['process/meetings/first-meeting.md', 'process/meetings/first-meeting.pdf',
                 'process/meetings/screenshots/first-meeting-participants.png'],
    '仓库与成员访问': ['process/access/m1-access.md',
                       'process/access/screenshots/github-private-repository.png',
                       'process/access/screenshots/github-collaborators.png',
                       'process/access/screenshots/github-commit-history.png'],
    '任务快照': ['process/snapshots/' + stem + ext
                 for stem in ('2026-10-06-m1-m2', '2026-10-06-review-sync')
                 for ext in ('.csv', '.md', '.pdf')],
    'Notion原始截图': ['process/snapshots/screenshots/notion-board-before-update.png'],
    '成员反馈': ['process/reviews/m1-member-review.md', 'process/reviews/m1-member-review.pdf'],
    '版本记录': ['process/versions/m1-version-record.md', 'process/versions/git-history.txt'],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive_content(source, data):
    # Only packaged copies adjust screenshot links. Original evidence is untouched.
    if source in ('process/meetings/first-meeting.md', 'process/access/m1-access.md'):
        return data.decode('utf-8').replace('](screenshots/', '](').encode('utf-8')
    return data


def verify_payload(items, sources):
    for name, data in items.items():
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts, name
        assert len(path.parts) <= 2, name
        if len(path.parts) == 2:
            assert path.parts[0] in CATEGORIES, name
        if name in sources:
            assert data == archive_content(sources[name], (ROOT / sources[name]).read_bytes()), name
        if name.endswith(('.md', '.txt', '.csv', '.html', '.json')):
            content = data.decode('utf-8-sig')
            for pattern in [r'sk-[A-Za-z0-9_-]{24,}', r'gh[pousr]_[A-Za-z0-9]{30,}',
                            r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']:
                assert not re.search(pattern, content), 'Possible credential in ' + name
        if name.endswith('.png'):
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
        if name.endswith('.md'):
            for target in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8-sig')):
                link = urlsplit(target)
                if not link.scheme and not link.netloc and link.path:
                    assert normpath(join(dirname(name), unquote(link.path))) in items, target

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                for key, value in attrs:
                    if key == 'href':
                        assert unquote(value) in items, value

    Links().feed(items['index.html'].decode('utf-8'))


def verify_archive(archive, items):
    with ZipFile(archive) as z:
        assert z.testzip() is None, 'ZIP CRC failure'
        assert len(z.namelist()) == len(set(z.namelist())) == len(items)
        assert set(z.namelist()) == {BASE + '/' + name for name in items}
        for name, data in items.items():
            assert z.read(BASE + '/' + name) == data, name
    records = list(csv.DictReader(io.StringIO(items['file-manifest.csv'].decode('utf-8-sig'))))
    assert {row['包内路径'] for row in records} == set(items) - {'file-manifest.csv', 'file-sha256sums.txt'}
    for row in records:
        payload = items[row['包内路径']]
        assert len(payload) == int(row['字节数']) and sha(payload) == row['SHA-256']
        if row['仓库来源']:
            assert sha((ROOT / row['仓库来源']).read_bytes()) == row['来源SHA-256']
    checks = items['file-sha256sums.txt'].decode('utf-8').splitlines()
    assert len(checks) == len(items) - 1
    for line in checks:
        digest, name = line.split('  ', 1)
        assert sha(items[name]) == digest, name
    for line in items['版本记录/report-sha256sums.txt'].decode('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        assert sha((ROOT / name).read_bytes()) == digest, name


def build():
    PROCESS.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    items, sources = {}, {}

    def add(source, name):
        path = ROOT / source
        assert path.is_file() and not path.is_symlink(), source
        assert name not in items, name
        items[name] = archive_content(source, path.read_bytes())
        sources[name] = source

    def generated(name, content, filename=None):
        data = content.encode('utf-8')
        (PROCESS / (filename or name)).write_bytes(data)
        items[name] = data

    add('process/m1-process-index.md', 'm1-process-index.md')
    for category, paths in CATEGORIES.items():
        for source in paths:
            add(source, category + '/' + Path(source).name)
    report_paths = ['docs/requirements/team-workflow' + ext for ext in ('.md', '.docx', '.pdf')]
    generated('版本记录/report-sha256sums.txt', ''.join(
        f'{sha((ROOT / path).read_bytes())}  {path}\n' for path in report_paths), 'report-sha256sums.txt')
    entries = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
               '<title>M1过程材料</title><body><h1>M1过程材料</h1>',
               '<p>按材料说明分为六类。报告独立交付；当前修订待成员复核。</p>',
               '<p>清单记录包内路径、仓库来源及两者哈希。会议和访问记录的包内 Markdown 仅调整截图链接。</p>',
               '<p>清单不列自身及哈希文件；哈希文件覆盖清单但不包含自身。</p>',
               '<a href="m1-process-index.md">材料说明</a>']
    for category in CATEGORIES:
        entries.append('<h2>' + escape(category) + '</h2><ul>')
        for name in sorted(items):
            if name.startswith(category + '/'):
                entries.append(f'<li><a href="{quote(name)}">{escape(Path(name).name)}</a></li>')
        entries.append('</ul>')
    entries.append('<h2>校验文件</h2><ul>')
    for name in ('file-manifest.csv', 'file-sha256sums.txt', 'package-check.json'):
        entries.append(f'<li><a href="{name}">{name}</a></li>')
    entries.append('</ul></body></html>')
    generated('index.html', '\n'.join(entries))
    info = subprocess.run(['pdfinfo', str(ROOT / report_paths[-1])],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    match = re.search(r'Pages:\s+(\d+)', info.stdout.decode('utf-8', errors='replace'))
    assert match, 'pdfinfo did not report a page count'
    pages = int(match.group(1))
    assert 1 <= pages <= 5, f'M1 report exceeds the 5-page limit: {pages}'
    for ext in ('.docx', '.pdf'):
        assert (OUTPUT / (BASE + '-报告' + ext)).read_bytes() == (ROOT / ('docs/requirements/team-workflow' + ext)).read_bytes()
    result = {'report_pages': pages, 'archive_files': len(items) + 3,
              'categories': list(CATEGORIES), 'zip_crc': 'pass', 'payload_hashes': 'pass',
              'manifest': 'pass', 'safe_relative_paths': 'pass', 'offline_html_links': 'pass',
              'markdown_links': 'pass', 'source_mapping': 'pass', 'report_hashes': 'pass',
              'credential_pattern_check': 'pass', 'report_matches_repository': True,
              'member_review_current_revision': 'pending', 'notion_updated': False,
              'github_remote_write': False, 'submitted': False}
    generated('package-check.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    buf = io.StringIO(newline='')
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(['包内路径', '仓库来源', '字节数', 'SHA-256', '来源SHA-256'])
    for name, data in sorted(items.items()):
        source = sources.get(name, '')
        writer.writerow([name, source, len(data), sha(data), sha((ROOT / source).read_bytes()) if source else ''])
    manifest = buf.getvalue().encode('utf-8-sig')
    (PROCESS / 'file-manifest.csv').write_bytes(manifest)
    items['file-manifest.csv'] = manifest
    generated('file-sha256sums.txt', ''.join(f'{sha(data)}  {name}\n' for name, data in sorted(items.items())))
    verify_payload(items, sources)
    archive = OUTPUT / (BASE + '-过程材料.zip')
    temporary = archive.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as z:
        for name, data in sorted(items.items()):
            z.writestr(BASE + '/' + name, data)
    verify_archive(temporary, items)
    assert result['archive_files'] == len(items)
    temporary.replace(archive)
    (OUTPUT / 'package-check.json').write_bytes(items['package-check.json'])
    paths = [OUTPUT / (BASE + suffix) for suffix in ('-报告.docx', '-报告.pdf', '-过程材料.zip')]
    (OUTPUT / 'sha256sums.txt').write_text(''.join(f'{sha(path.read_bytes())}  {path.name}\n' for path in paths), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return archive


if __name__ == '__main__':
    print(build())
