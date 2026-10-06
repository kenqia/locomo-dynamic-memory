#!/usr/bin/env python3
"""Package only the explicit M2 evidence list, then validate ZIP and hashes."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urlsplit
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"deliverables/m2"
PROCESS=ROOT/"process/m2"
BASE="PROJECT-MILESTONE2-3-在阴雨天游泳"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def markdown_html(text):
    out=[];i=0;lines=text.splitlines()
    while i<len(lines):
        line=lines[i].strip()
        if not line or line.startswith("<!--"):
            i+=1;continue
        if line.startswith("```"):
            i+=1;block=[]
            while i<len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]);i+=1
            out.append("<pre>"+escape("\n".join(block))+"</pre>")
        elif line.startswith("#"):
            n=len(line)-len(line.lstrip("#"))
            n=min(n+1,6)
            out.append(f"<h{n}>"+escape(line.lstrip("#").strip())+f"</h{n}>")
        elif line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                vals=[s.strip() for s in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?",v) for v in vals):
                    rows.append(vals)
                i+=1
            out.append("<div class='table-wrap'><table>")
            for r,vals in enumerate(rows):
                tag="th" if r==0 else "td"
                out.append("<tr>"+"".join(f"<{tag}>"+escape(v)+f"</{tag}>" for v in vals)+"</tr>")
            out.append("</table></div>")
            continue
        else:
            out.append("<p>"+escape(line)+"</p>")
        i+=1
    return "\n".join(out)

def build():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    PROCESS.mkdir(parents=True,exist_ok=True)
    items={}
    def add(path):
        path=Path(path)
        src=ROOT/path
        assert src.is_file(),str(src)
        assert not src.is_symlink(),str(src)
        items[path.as_posix()]=src.read_bytes()
    add("process/m2-process-index.md")
    # The report PDF/Word are separate deliverables, as in the M1 package.
    add("docs/requirements/vision-and-scope.md")
    add("docs/sources/m2-real-world-memory-research.md")
    add("process/m2/iterations/vision-and-scope-before-research.md")
    add("process/m2/iterations/vision-and-scope-initial-draft.md")
    add("process/m2/iterations/revision-notes.md")
    add("docs/decisions/m2-proposal-interview.md")
    add("CONTEXT.md")
    for path in sorted((ROOT/"docs/requirements/assets/m2").iterdir()):
        if path.suffix in [".png",".svg"]:
            add(path.relative_to(ROOT))
    for name in ["build_m2_report.py","package_m2_materials.py"]:
        add("scripts/"+name)
    for path in sorted((ROOT/"process/m2/reference-images").glob("*.png")):
        add(path.relative_to(ROOT))
    for ext in [".md",".docx",".pdf"]:
        add("process/meetings/first-meeting"+ext)
    add("process/meetings/screenshots/first-meeting-participants.png")
    add("docs/requirements/team-workflow.md")
    add("docs/requirements/assets/m1-milestone-timeline.png")
    add("process/m2/m2-tasks-historical-20261006.csv")
    for ext in [".md",".docx",".pdf"]:
        add("process/snapshots/2026-10-06-m1-m2"+ext)
    for name in ["source-notes.md","review-checklist.md","validation-record.md",
                 "version-record.md","git-history-baseline.txt"]:
        add("process/m2/"+name)

    sections=[
        ("材料说明","process/m2-process-index.md"),
        ("方案确认","docs/decisions/m2-proposal-interview.md"),
        ("本次修订","process/m2/iterations/revision-notes.md"),
        ("材料来源","process/m2/source-notes.md"),
        ("待成员复核","process/m2/review-checklist.md"),
        ("本地检查","process/m2/validation-record.md"),
        ("版本说明","process/m2/version-record.md")]

    links=[
        ("报告 Markdown","docs/requirements/vision-and-scope.md"),
        ("联网调研与一手来源","docs/sources/m2-real-world-memory-research.md"),
        ("联网调研前的报告","process/m2/iterations/vision-and-scope-before-research.md"),
        ("总体架构图","docs/requirements/assets/m2/system-architecture.png"),
        ("记录与检索流程图","docs/requirements/assets/m2/recording-retrieval-flow.png"),
        ("首次会议纪要 PDF","process/meetings/first-meeting.pdf"),
        ("原会议截图","process/meetings/screenshots/first-meeting-participants.png"),
        ("M2 历史任务 CSV","process/m2/m2-tasks-historical-20261006.csv"),
        ("M1/M2 原始历史快照 PDF","process/snapshots/2026-10-06-m1-m2.pdf"),
    ]
    style="""body{font:16px/1.75 system-ui,'Noto Sans CJK SC','Microsoft YaHei',sans-serif;color:#202a35;background:#fff;margin:0}
main{max-width:1000px;margin:40px auto;padding:0 24px 60px}h1{font-size:30px}h2{font-size:23px}h3{font-size:19px}a{color:#245d8d}
nav ul{padding-left:24px}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #d9d9d9;padding:8px 12px;text-align:left;vertical-align:middle}
th{background:#e7edf4}.table-wrap{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 monospace}summary{cursor:pointer;font-size:19px;font-weight:600;padding:14px 0}
details{border-top:1px solid #d9d9d9;margin-top:20px}img{max-width:100%;height:auto}footer{font-size:14px;color:#5f6e7c;margin-top:40px}"""
    body=["<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
          "<title>M2 过程材料阅读说明</title><style>"+style+"</style><main>",
          "<h1>M2 项目提案过程材料</h1>",
          "<p>在阴雨天游泳 · Team ID 3 · 2026-10-06</p>",
          "<p>本轮报告和过程包已本地制作。方案经组长确认全组接受，文件仍待成员复核。未合并、推送、更新 Notion 或正式提交。</p>",
          "<p>报告 PDF 和 Word 独立交付。过程包保留仓库相对路径，全部文件可在仓库中找到对应原件。</p>",
          "<nav><h2>文件入口</h2><ul>"]
    for label,path in links:
        body.append(f'<li><a href="../../{quote(path,safe="/")}">{escape(label)}</a></li>')
    body.append("</ul></nav>")
    for title,path in sections:
        body.append("<details"+(" open" if title=="材料说明" else "")+"><summary>"+escape(title)+"</summary>")
        body.append(markdown_html(items[path].decode("utf-8-sig")))
        body.append("</details>")
    body.append("<h2>全部文件</h2><ul>")
    for path in sorted(items):
        body.append(f'<li><a href="../../{quote(path,safe="/")}">{escape(path)}</a></li>')
    for path in ["process/m2/file-manifest.csv","process/m2/file-sha256sums.txt"]:
        body.append(f'<li><a href="../../{quote(path,safe="/")}">{escape(path)}</a></li>')
    body.append("</ul><footer>解压后离线阅读。原始材料保留当时状态，候选图不作为实现截图。具体共享与提交范围由项目负责人核对。</footer></main></html>")
    (PROCESS/"index.html").write_text("\n".join(body),encoding="utf-8")
    add("process/m2/index.html")

    # A manifest hashes the payload. A checksum file also hashes the manifest.
    # Neither file hashes itself.
    buf=io.StringIO(newline="")
    writer=csv.writer(buf,lineterminator="\n")
    writer.writerow(["仓库及包内路径","字节数","SHA-256"])
    for path,data in sorted(items.items()):
        writer.writerow([path,len(data),sha(data)])
    (PROCESS/"file-manifest.csv").write_bytes(buf.getvalue().encode("utf-8-sig"))
    add("process/m2/file-manifest.csv")
    (PROCESS/"file-sha256sums.txt").write_text("".join(f"{sha(data)}  {path}\n" for path,data in sorted(items.items())),encoding="utf-8")
    add("process/m2/file-sha256sums.txt")
    zip_path=OUTPUT/(BASE+"-过程材料.zip")
    with ZipFile(zip_path,"w",ZIP_DEFLATED,compresslevel=6) as z:
        for path,data in sorted(items.items()):
            z.writestr(BASE+"/"+path,data)
    for ext in [".pdf",".docx"]:
        shutil.copy2(ROOT/("docs/requirements/vision-and-scope"+ext),OUTPUT/(BASE+"-报告"+ext))
    verify(zip_path)
    return zip_path

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.links.extend(v for k,v in attrs if k=="href")

def verify(zip_path):
    with ZipFile(zip_path) as z:
        assert z.testzip() is None,"ZIP CRC failure"
        archived=z.namelist(); assert len(archived)==len(set(archived))
        assert all(n.startswith(BASE+"/") for n in archived)
        names=[n[len(BASE)+1:] for n in archived]
        def read(name):
            return z.read(BASE+"/"+name)
        for name in names:
            p=PurePosixPath(name)
            assert not p.is_absolute() and ".." not in p.parts,name
            assert not re.search(r"(^|/)(\.env|auth\.json|config\.toml|\.git)(/|$)",name),name
            assert (ROOT/name).is_file(),"ZIP-only file: "+name
            assert read(name)==(ROOT/name).read_bytes(),"Repository mismatch: "+name
            if name.endswith(".png"):
                with Image.open(io.BytesIO(read(name))) as img:img.verify()
            if name.endswith(".svg"):ET.fromstring(read(name))
        checks=read("process/m2/file-sha256sums.txt").decode().splitlines()
        for line in checks:
            digest,name=line.split("  ",1)
            assert sha(read(name))==digest,name
        with io.TextIOWrapper(io.BytesIO(read("process/m2/file-manifest.csv")),encoding="utf-8-sig",newline="") as f:
            records=list(csv.DictReader(f))
        for row in records:
            data=read(row["仓库及包内路径"])
            assert len(data)==int(row["字节数"]) and sha(data)==row["SHA-256"],row["仓库及包内路径"]
        parser=Links();parser.feed(read("process/m2/index.html").decode())
        for link in parser.links:
            parsed=urlsplit(link)
            assert not parsed.scheme and not parsed.netloc,link
            from posixpath import normpath,join,dirname
            assert normpath(join("process/m2",unquote(parsed.path))) in names,link
        for path in ["docs/requirements/vision-and-scope.md","docs/requirements/team-workflow.md","process/meetings/first-meeting.md"]:
            for src in re.findall(r"!\[.*?\]\((.*?)\)|\[[^\]]*\]\(([^)]+\.png)\)",read(path).decode()):
                target=next(s for s in src if s)
                assert normpath(join(dirname(path),target)) in names,target
        with (ROOT/"process/snapshots/2026-10-06-m1-m2.csv").open(encoding="utf-8-sig",newline="") as f:
            original=[r for r in csv.DictReader(f) if r["里程碑"]=="M2"]
        extracted=list(csv.DictReader(io.StringIO(read("process/m2/m2-tasks-historical-20261006.csv").decode("utf-8-sig"))))
        assert extracted==original and len(extracted)==10,"Historical tasks changed"
        for name in names:
            if name.endswith((".md",".txt",".py",".csv",".html",".svg")):
                # Report existence and path only; never print a matching value.
                data=read(name).decode("utf-8-sig")
                for pattern in [r"sk-[A-Za-z0-9_-]{24,}",r"gh[pousr]_[A-Za-z0-9]{30,}",r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"]:
                    assert not re.search(pattern,data),"Possible credential found in "+name
        assert "docs/requirements/vision-and-scope.pdf" not in names
        assert "docs/requirements/vision-and-scope.docx" not in names
    pdfinfo=subprocess.check_output(["pdfinfo",str(OUTPUT/(BASE+"-报告.pdf"))],text=True)
    pages=int(re.search(r"Pages:\s+(\d+)",pdfinfo).group(1))
    assert pages==5,pages
    report={
        "report_pages":pages,"archive_files":len(names),
        "zip_crc":"pass","payload_hashes":"pass","manifest":"pass",
        "safe_relative_paths":"pass","offline_html_links":"pass","markdown_image_links":"pass",
        "png_svg_readability":"pass","historical_m2_tasks":10,
        "historical_states_unchanged":True,"credential_pattern_check":"pass",
        "report_matches_repository":(OUTPUT/(BASE+"-报告.pdf")).read_bytes()==(ROOT/"docs/requirements/vision-and-scope.pdf").read_bytes(),
        "all_archive_files_match_repository":True,
        "member_review":"pending","notion_updated":False,"remote_write":False,"submitted":False,
    }
    (OUTPUT/"package-check.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    deliverables=[OUTPUT/(BASE+suffix) for suffix in ["-报告.pdf","-报告.docx","-过程材料.zip"]]
    (OUTPUT/"sha256sums.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in deliverables),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    print("Created "+str(build()))
