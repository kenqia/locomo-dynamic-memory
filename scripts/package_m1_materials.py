#!/usr/bin/env python3
"""Build the M1 evidence archive from explicit repository paths and verify it."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
from html import escape
from urllib.parse import quote
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / 'process/m1'
OUTPUT = ROOT / 'deliverables/m1'
BASE = 'PROJECT-MILESTONE1-3-在阴雨天游泳'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def build(include_result=True):
    PROCESS.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if include_result:
        build(include_result=False)
        result = json.loads((OUTPUT / 'package-check.json').read_text())
        result['archive_files'] += 1
        (PROCESS / 'package-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    items = {}
    def add(path):
        source = ROOT / path
        assert source.is_file() and not source.is_symlink(), path
        items[path] = source.read_bytes()
    for path in [
        'process/m1-process-index.md',
        'process/access/m1-access.md',
        'process/versions/m1-version-record.md',
        'process/versions/git-history.txt',
        'docs/requirements/team-workflow.md',
        'docs/requirements/assets/m1-milestone-timeline.png',
        'process/snapshots/2026-10-06-m1-m2.csv',
        'process/snapshots/2026-10-06-review-sync.csv',
        'process/m2/notion-before-review-sync.json',
        'process/m2/notion-review-sync.json',
        'scripts/package_m1_materials.py',
        'scripts/build_process_documents.py',
        'scripts/build_m1_report.py',
        'scripts/build_m2_report.py',
    ]:
        add(path)
    for stem in ['process/meetings/first-meeting',
                 'process/snapshots/2026-10-06-m1-m2',
                 'process/snapshots/2026-10-06-review-sync',
                 'process/reviews/m1-member-review']:
        for extension in ['.md', '.docx', '.pdf']:
            add(stem+extension)
    for path in [
        'process/meetings/screenshots/first-meeting-participants.png',
        'process/snapshots/screenshots/notion-board-before-update.png',
        'process/access/screenshots/github-private-repository.png',
        'process/access/screenshots/github-collaborators.png',
        'process/access/screenshots/github-commit-history.png',
    ]:
        add(path)
    # These report files are delivered separately. The generated digest record
    # lets a reviewer associate the evidence archive with the exact report.
    report_paths = ['docs/requirements/team-workflow'+ext for ext in ['.md','.docx','.pdf']]
    (PROCESS/'report-sha256sums.txt').write_text(''.join(
        f'{sha((ROOT/path).read_bytes())}  {path}\n' for path in report_paths))
    add('process/m1/report-sha256sums.txt')
    if include_result:
        add('process/m1/package-check.json')
    entries = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
               '<title>M1 过程材料</title><body style="font:16px/1.6 sans-serif;max-width:1000px;margin:40px auto">',
               '<h1>M1 过程材料</h1>',
               '<p>历史任务数据与后续注记分开保留。报告独立交付，版本以报告校验文件为准。本轮过程修订尚待成员确认。</p><ul>']
    for path in sorted(items):
        entries.append(f'<li><a href="../../{quote(path,safe="/")}">{escape(path)}</a></li>')
    entries.extend(['<li><a href="file-manifest.csv">文件清单</a></li>',
                    '<li><a href="file-sha256sums.txt">文件校验</a></li>', '</ul></body></html>'])
    (PROCESS/'index.html').write_text('\n'.join(entries))
    add('process/m1/index.html')
    manifest = io.StringIO(newline='')
    writer = csv.writer(manifest, lineterminator='\n')
    writer.writerow(['仓库及包内路径','字节数','SHA-256'])
    for path, data in sorted(items.items()):
        writer.writerow([path, len(data), sha(data)])
    (PROCESS/'file-manifest.csv').write_text(manifest.getvalue(), encoding='utf-8-sig')
    add('process/m1/file-manifest.csv')
    (PROCESS/'file-sha256sums.txt').write_text(''.join(
        f'{sha(data)}  {path}\n' for path,data in sorted(items.items())))
    add('process/m1/file-sha256sums.txt')
    archive = OUTPUT/(BASE+'-过程材料.zip')
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for path,data in sorted(items.items()):
            z.writestr(BASE+'/'+path,data)
    for extension in ['.docx','.pdf']:
        shutil.copyfile(ROOT/('docs/requirements/team-workflow'+extension), OUTPUT/(BASE+'-报告'+extension))
    verify(archive,items)
    return archive

def verify(archive,items):
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist())) == len(items)
        for name,data in items.items():
            path = PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts
            assert not re.search(r'(^|/)(\.env|auth\.json|config\.toml|\.git)(/|$)',name)
            assert z.read(BASE+'/'+name) == data == (ROOT/name).read_bytes(),name
            if name.endswith(('.md','.txt','.py','.csv','.html','.json')):
                content = data.decode('utf-8-sig')
                for pattern in [r'sk-[A-Za-z0-9_-]{24,}', r'gh[pousr]_[A-Za-z0-9]{30,}', r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']:
                    assert not re.search(pattern,content), 'Possible credential in '+name
            if name.endswith('.png'):
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
        records = list(csv.DictReader(io.StringIO(items['process/m1/file-manifest.csv'].decode('utf-8-sig'))))
        for row in records:
            payload = z.read(BASE+'/'+row['仓库及包内路径'])
            assert len(payload) == int(row['字节数']) and sha(payload) == row['SHA-256']
        for line in items['process/m1/file-sha256sums.txt'].decode().splitlines():
            digest,name = line.split('  ',1)
            assert sha(z.read(BASE+'/'+name)) == digest
        for line in items['process/m1/report-sha256sums.txt'].decode().splitlines():
            digest,name = line.split('  ',1)
            assert sha((ROOT/name).read_bytes()) == digest
        from html.parser import HTMLParser
        from urllib.parse import unquote
        from posixpath import normpath,join
        class Links(HTMLParser):
            def handle_starttag(self,tag,attrs):
                if tag == 'a':
                    for key,value in attrs:
                        if key == 'href':
                            assert normpath(join('process/m1',unquote(value))) in items,value
        Links().feed(items['process/m1/index.html'].decode())
    info = subprocess.check_output(['pdfinfo',str(OUTPUT/(BASE+'-报告.pdf'))],text=True)
    pages = int(re.search(r'Pages:\s+(\d+)',info).group(1))
    assert pages == 5
    result = {'report_pages':pages,'archive_files':len(items),
              'zip_crc':'pass','payload_hashes':'pass','manifest':'pass',
              'safe_relative_paths':'pass','offline_html_links':'pass',
              'report_hashes':'pass','credential_pattern_check':'pass','all_archive_files_match_repository':True,
              'report_matches_repository':(OUTPUT/(BASE+'-报告.pdf')).read_bytes()==(ROOT/'docs/requirements/team-workflow.pdf').read_bytes(),
              'notion_updated':True,'member_review_current_revision':'pending',
              'github_remote_write':False,'submitted':False}
    if 'process/m1/package-check.json' in items:
        assert json.loads(items['process/m1/package-check.json']) == result
    (OUTPUT/'package-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    paths = [OUTPUT/(BASE+suffix) for suffix in ['-报告.docx','-报告.pdf','-过程材料.zip']]
    (OUTPUT/'sha256sums.txt').write_text(''.join(f'{sha(path.read_bytes())}  {path.name}\n' for path in paths))
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    print(build())
