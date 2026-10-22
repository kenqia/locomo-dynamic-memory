"""Package M4 evidence with an offline index, source manifests and verification.

Run in the independent document environment (Pillow and PyMuPDF).
Reads saved experiment results only; no model calls or remote writes.
"""
from __future__ import annotations

import csv
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "process/m4"
OUTPUT = ROOT / "deliverables/m4"
BASE = "PROJECT-MILESTONE4-3-在阴雨天游泳"
DATE = "2026-10-22"
REPORT = "docs/design/m4-midterm-report.md"
CONTROLS = ["process/m4/package-check.json", "process/m4/file-manifest.csv", "process/m4/file-sha256sums.txt"]
GROUPS = {
    "过程说明与复核": ["process/m4-process-index.md"] + [f"process/m4/{name}" for name in [
        "draft-evidence.md", "source-notes.md", "version-record.md", "review-checklist.md",
        "member-review-record.md", "validation-record.md", "code-review.md", "status-snapshot.json",
        "git-history-baseline.txt", "pdf-validation.json", "source-validation.json", "report-sha256sums.txt"]],
    "报告与需求设计": [REPORT, "process/m4/iterations/report-v0.1.md", "process/m4/iterations/report-v0.2.md",
        "process/m4/iterations/revision-notes.md", "docs/design/assets/m4/system-architecture.png",
        "docs/design/assets/m4/system-architecture.svg", "docs/requirements/team-workflow.md", "CONTEXT.md",
        "docs/adr/0001-memory-architecture.md", "docs/adr/0002-real-model-baseline-protocol.md",
        "docs/specs/issue-4-m3-m4-dynamic-memory.md", "docs/specs/issue-15-real-deepseek-baseline.md",
        "docs/app/running.md", "docs/app/building.md", "docs/app/querying.md", "docs/app/versions.md",
        "docs/app/evaluation.md", "docs/app/relations.md", "docs/app/retrieval.md",
        "data/raw/locomo/README.md", "data/raw/locomo/provenance.json", "data/raw/locomo/LICENSE.txt"],
    "真实实验与来源核查": ["experiments/current-showcase/README.md", "experiments/current-showcase/plan.json",
        "experiments/current-showcase/plan.sha256"] + [f"experiments/current-showcase/results/{name}" for name in [
        "report.md", "analysis.md", "paired-differences.csv", "paired-results.json", "recall-results.json",
        "dynamic-review.md", "dynamic-review.json", "dynamic-packets.json", "answer-source-review.md",
        "answer-source-review.json", "answer-source-packets.json", "final-audit.json", "outcome.json"]],
    "真实结果只读页面": [f"experiments/current-showcase/web-recorded/{name}" for name in [
        "results.json", "answer-and-source.png", "history-and-effective-memory.png", "incremental-raw-trace.png",
        "insufficient-evidence.png", "strategy-switch-keeps-answer.png", "failure.png", "failure-page.txt"]],
    "受控页面与工程检查": [f"experiments/current-showcase/web-controlled/{name}" for name in [
        "issue-12-result.json", "diagnostics.json", "query-current.png", "query-historical.png", "query-conflict.png",
        "query-insufficient.png", "issue-12-evaluation.png"]] + ["process/prs/issue-15-integration.md",
        "process/prs/issue-15-checks.json", "experiments/issue-4-implementation.md",
        "experiments/issue-12-integration-validation.md", "experiments/issue-15-closure/README.md"],
    "文档构建与打包": ["scripts/build_m4_report.py", "scripts/package_m4_materials.py"],
}


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: str, value) -> None:
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True,
                          encoding="utf-8").stdout.strip()


def prepare_history() -> dict:
    for revision, name in [("7a1da75", "report-v0.1.md"), ("cfc4416", "report-v0.2.md")]:
        data = subprocess.run(["git", "show", f"{revision}:{REPORT}"], cwd=ROOT,
                              check=True, capture_output=True).stdout
        target = PROCESS / "iterations" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"Historical snapshot modified: {target.name}")
        target.write_bytes(data)
    head = git("rev-parse", "HEAD")
    status = git("-c", "core.quotepath=false", "status", "--short", "--untracked-files=normal")
    write("process/m4/git-history-baseline.txt", "M4 local Git capture; client date: " + DATE + " Asia/Shanghai\n"
          + "HEAD: " + head + "\nBranch: " + git("branch", "--show-current")
          + "\nLocal cached origin/main: " + git("rev-parse", "origin/main")
          + "\nNo network refresh in this packaging run. Working files are not claimed to be in HEAD.\n\n"
          + git("log", "-20", "--date=iso-strict", "--format=%h | %ad | %s") + "\n")
    snapshot = {"captured_on": DATE, "timezone": "Asia/Shanghai", "kind": "local_materials_inventory",
        "notion_export": False, "head": head, "branch": git("branch", "--show-current"),
        "cached_origin_main": git("rev-parse", "origin/main"), "network_refreshed_this_run": False,
        "capture_phase": "before archive generation; status is not a final commit inventory",
        "working_status_at_capture": status.splitlines(), "report_version": "v0.3",
        "implementation_baseline": "ffb2657741a535c27cc7d38d6f20d7aede94013a",
        "formal_m3_reference": "pending", "member_non_author_review": "pending",
        "notion_synced": False, "new_m4_meeting_evidence": "not_provided",
        "new_presentation_environment_test": "not_performed", "presentation_file": "not_provided",
        "remote_write_this_run": False, "submitted": False, "submission_receipt": "not_provided"}
    write_json("process/m4/status-snapshot.json", snapshot)
    return snapshot


def validate_report() -> dict:
    validation = json.loads((PROCESS / "pdf-validation.json").read_text(encoding="utf-8"))
    source = (ROOT / REPORT).read_bytes()
    pdf = ROOT / validation["pdf"]
    assert digest(source) == validation["source_sha256"], "Source changed; rebuild report before packaging"
    assert digest(pdf.read_bytes()) == validation["pdf_sha256"], "PDF changed; rebuild report before packaging"
    with pymupdf.open(pdf) as document:
        pages = len(document)
        assert 0 < pages <= 5, f"Report exceeds five pages: {pages}"
        assert pages == validation["pages"]
    word = ROOT / "docs/design/m4-midterm-report.docx"
    with ZipFile(word) as archive:
        assert archive.testzip() is None
        ET.fromstring(archive.read("word/document.xml"))
    delivered_word = OUTPUT / f"{BASE}-报告.docx"
    delivered_word.write_bytes(word.read_bytes())
    report_files = [ROOT / REPORT, word, pdf, delivered_word]
    write("process/m4/report-sha256sums.txt", "".join(
        f"{digest(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n" for path in report_files))
    text = source.decode("utf-8")
    paired = json.loads((ROOT / "experiments/current-showcase/results/paired-results.json").read_text(encoding="utf-8"))
    assert len(paired["rows"]) == 100 and all(row["status"] == "succeeded" for row in paired["rows"])
    for strategy, summary in paired["summary"].items():
        rows = [row for row in paired["rows"] if row["strategy"] == strategy and row["category"] in [1, 2, 3, 4]]
        assert len(rows) == 16
        value = sum(row["score"] for row in rows) / 16
        assert abs(value - summary["answerable_f1_failures_zero"]) < 1e-12
        assert f"{value:.4f}" in text, strategy
    recall = json.loads((ROOT / "experiments/current-showcase/results/recall-results.json").read_text(encoding="utf-8"))
    assert len(recall["rows"]) == 40
    for k in ["5", "10", "20"]:
        value = sum(row["recall_at"][k] for row in recall["rows"]) / 40
        assert f"{value * 100:.2f}%" in text, k
    return {"report_pages": pages, "report_hashes": "pass", "word_xml": "pass", "saved_metrics": "pass"}


def article_id(path: str) -> str:
    return "doc-" + digest(path.encode())[:16]


def offline_index(payload: dict[str, bytes], baseline: str) -> str:
    markdown = {path for path in payload if path.endswith(".md")}
    def inline(text: str, source: str) -> str:
        output = []
        position = 0
        for match in re.finditer(r"(!?)\[([^\]]+)\]\(([^)]+)\)", text):
            output.append(escape(text[position:match.start()]))
            image, label, url = match.groups()
            parsed = urlsplit(url)
            online = False
            if parsed.scheme or parsed.netloc:
                assert parsed.scheme in ["https", "http", "mailto"], "Unsupported URL scheme"
                target = url
                online = True
            else:
                origin = REPORT if source.startswith("process/m4/iterations/report-v") else source
                relative = posixpath.normpath(posixpath.join(posixpath.dirname(origin), unquote(parsed.path))) if parsed.path else source
                assert not relative.startswith("../") and not PurePosixPath(relative).is_absolute()
                if relative.startswith("deliverables/m4/"):
                    output.append(escape(label + "（独立交付，见 ZIP 外同名文件）"))
                    position = match.end()
                    continue
                if relative == "process/m4/index.html":
                    target = "#top"
                elif relative in markdown:
                    target = "#" + article_id(relative)
                elif relative in payload or relative in CONTROLS:
                    target = "../../" + quote(relative, safe="/")
                else:
                    target = f"https://github.com/kenqia/locomo-dynamic-memory/blob/{baseline}/{quote(relative, safe='/')}"
                    online = True
            suffix = "（在线补充）" if online else ""
            if image and not online:
                output.append(f'<img src="{escape(target, quote=True)}" alt="{escape(label, quote=True)}">')
            else:
                output.append(f'<a href="{escape(target, quote=True)}">{escape(label + suffix)}</a>')
            position = match.end()
        output.append(escape(text[position:]))
        return "".join(output)
    def render(path: str) -> str:
        lines = payload[path].decode("utf-8-sig").splitlines()
        output = []
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            index += 1
            if not line or line.startswith("<!--"):
                continue
            if line.startswith("```"):
                code = []
                while index < len(lines) and not lines[index].strip().startswith("```"):
                    code.append(lines[index])
                    index += 1
                index += 1
                output.append("<pre>" + escape("\n".join(code)) + "</pre>")
            elif line.startswith("|"):
                rows = [line]
                while index < len(lines) and lines[index].strip().startswith("|"):
                    rows.append(lines[index].strip())
                    index += 1
                output.append("<div class='table-wrap'><table>")
                header = True
                for row in rows:
                    cells = [cell.strip() for cell in row.strip("|").split("|")]
                    if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                        continue
                    tag = "th" if header else "td"
                    output.append("<tr>" + "".join(f"<{tag}>" + inline(cell, path) + f"</{tag}>" for cell in cells) + "</tr>")
                    header = False
                output.append("</table></div>")
            elif line.startswith("#"):
                level = min(6, len(line) - len(line.lstrip("#")) + 1)
                output.append(f"<h{level}>" + inline(line.lstrip("# "), path) + f"</h{level}>")
            else:
                output.append("<p>" + inline(line, path) + "</p>")
        return "\n".join(output)
    body = ["<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'><title>M4 过程材料</title>",
        "<style>body{font:16px/1.75 system-ui,'Microsoft YaHei',sans-serif;color:#203247;margin:0}main{max-width:1100px;margin:32px auto;padding:0 24px 64px}a{color:#245d8d}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #ccd6e0;padding:7px;vertical-align:top;text-align:left}th{background:#edf3f8}.table-wrap{overflow:auto}img{max-width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:12px}article{border-top:2px solid #d6e0ea;padding-top:24px;margin-top:40px}code{overflow-wrap:anywhere}</style></head><body><main>",
        "<h1 id='top'>M4 过程材料离线阅读页</h1><p>在阴雨天游泳 · Team 3 · 2026-10-22</p>",
        "<p>报告 PDF 独立交付，含索引共 5 页。成员复核、正式 M3 引用、Notion 同步及正式提交仍待补齐。本页不运行代码或模型。</p>",
        "<p>主要说明已内嵌；JSON/CSV 和截图随包。标注“在线补充”的链接不属于离线载荷，需要网络和仓库权限。</p>"]
    for category, paths in GROUPS.items():
        body.append("<h2>" + escape(category) + "</h2><ul>")
        for path in paths:
            target = "#" + article_id(path) if path in markdown else "../../" + quote(path, safe="/")
            body.append(f'<li><a href="{target}">{escape(path)}</a></li>')
        body.append("</ul>")
    body.append("<h2>校验与清单</h2><ul>")
    for path in CONTROLS:
        body.append(f'<li><a href="../../{path}">{path}</a></li>')
    body.append("</ul>")
    for path in sorted(markdown):
        body.append(f'<article id="{article_id(path)}"><p><code>{escape(path)}</code></p>' + render(path) + "</article>")
    return "\n".join(body + ["</main></body></html>\n"])


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attributes):
        for key, value in attributes:
            if key == "id":
                self.ids.add(value)
            if (tag == "a" and key == "href") or (tag == "img" and key == "src"):
                self.links.append(value)


def check_html(data: bytes, names: set[str]) -> int:
    parser = Links()
    parser.feed(data.decode("utf-8"))
    local = 0
    for link in parser.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            assert parsed.scheme in ["https", "http", "mailto"]
            continue
        if not parsed.path:
            assert parsed.fragment in parser.ids, link
        else:
            target = posixpath.normpath(posixpath.join("process/m4", unquote(parsed.path)))
            assert target in names, target
        local += 1
    return local


def check_payload(payload: dict[str, bytes]) -> dict:
    for name, data in payload.items():
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts
        assert not any(part in [".git", ".env", "auth.json", "memory.sqlite3"] for part in path.parts)
        if name.endswith(".png"):
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        elif name.endswith(".svg"):
            ET.fromstring(data)
        elif name.endswith(".json"):
            json.loads(data)
        elif name.endswith(".csv"):
            list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
        if name.endswith((".md", ".txt", ".py", ".json", ".csv", ".html", ".svg")):
            for pattern in [rb"sk-[A-Za-z0-9_-]{24,}", rb"gh[pousr]_[A-Za-z0-9]{30,}",
                            rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"]:
                assert not re.search(pattern, data), "Credential pattern in " + name
    links = check_html(payload["process/m4/index.html"], set(payload) | set(CONTROLS))
    return {"safe_relative_paths": "pass", "png_svg_readability": "pass", "json_csv_parsing": "pass",
            "credential_pattern_check": "pass", "offline_html_links": "pass", "local_html_links_checked": links}


def assemble(payload: dict[str, bytes], report: dict) -> Path:
    write_json(CONTROLS[0], report)
    items = {**payload, CONTROLS[0]: (ROOT / CONTROLS[0]).read_bytes()}
    category_map = {name: category for category, paths in GROUPS.items() for name in paths}
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["仓库及包内路径", "材料类别", "字节数", "SHA-256"])
    for name, data in sorted(items.items()):
        writer.writerow([name, category_map.get(name, "自动索引与校验"), len(data), digest(data)])
    (ROOT / CONTROLS[1]).write_bytes(stream.getvalue().encode("utf-8-sig"))
    items[CONTROLS[1]] = (ROOT / CONTROLS[1]).read_bytes()
    write(CONTROLS[2], "".join(f"{digest(data)}  {name}\n" for name, data in sorted(items.items())))
    items[CONTROLS[2]] = (ROOT / CONTROLS[2]).read_bytes()
    archive_path = OUTPUT / f"{BASE}-过程材料.zip"
    with ZipFile(archive_path, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(items.items()):
            archive.writestr(BASE + "/" + name, data)
    return archive_path


def verify(archive_path: Path) -> dict:
    with ZipFile(archive_path) as archive:
        assert archive.testzip() is None, "ZIP CRC failure"
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate ZIP entries"
        assert all(name.startswith(BASE + "/") for name in names)
        payload = {name[len(BASE)+1:]: archive.read(name) for name in names}
        for name, data in payload.items():
            assert not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
            assert data == (ROOT / name).read_bytes(), "Repository mismatch: " + name
        checks = json.loads(payload[CONTROLS[0]])
        assert checks["archive_files"] == len(payload)
        rows = list(csv.DictReader(io.StringIO(payload[CONTROLS[1]].decode("utf-8-sig"))))
        expected_manifest = set(payload) - set(CONTROLS[1:])
        assert len(rows) == len(expected_manifest)
        assert {row["仓库及包内路径"] for row in rows} == expected_manifest
        for row in rows:
            data = payload[row["仓库及包内路径"]]
            assert len(data) == int(row["字节数"]) and digest(data) == row["SHA-256"]
        sums = [line.split("  ", 1) for line in payload[CONTROLS[2]].decode("utf-8").splitlines()]
        assert {name for _, name in sums} == set(payload) - {CONTROLS[2]}
        for expected, name in sums:
            assert digest(payload[name]) == expected
        for line in payload["process/m4/report-sha256sums.txt"].decode("utf-8").splitlines():
            expected, name = line.split("  ", 1)
            assert digest((ROOT / name).read_bytes()) == expected, name
        assert check_payload(payload)["offline_html_links"] == "pass"
        assert not any(name.endswith((".docx", ".pdf", ".sqlite3", ".zip")) for name in payload)
    return checks


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PROCESS.mkdir(parents=True, exist_ok=True)
    snapshot = prepare_history()
    report_checks = validate_report()
    payload = {}
    selected = [path for paths in GROUPS.values() for path in paths]
    assert len(selected) == len(set(selected)), "Duplicate explicit selection"
    for name in selected:
        source = ROOT / name
        assert source.is_file() and not source.is_symlink(), name
        payload[name] = source.read_bytes()
    html = offline_index(payload, snapshot["implementation_baseline"])
    write("process/m4/index.html", html)
    payload["process/m4/index.html"] = (PROCESS / "index.html").read_bytes()
    checks = {"organized_on": DATE, "archive_files": len(payload) + len(CONTROLS),
        "implementation_baseline": snapshot["implementation_baseline"], "document_capture_head": snapshot["head"],
        **report_checks, **check_payload(payload), "zip_crc": "pass", "payload_hashes": "pass", "manifest": "pass",
        "all_archive_files_match_repository": True, "report_outputs_separate": True,
        "historical_report_snapshots": 2, "member_review": "pending", "formal_m3_reference": "pending",
        "notion_snapshot": "not_provided", "notion_updated": False, "new_meeting_evidence": "not_provided",
        "remote_write": False, "submitted": False, "model_calls_this_run": 0}
    archive_path = assemble(payload, checks)
    assert verify(archive_path) == checks
    (OUTPUT / "package-check.json").write_bytes((PROCESS / "package-check.json").read_bytes())
    deliverables = [OUTPUT / f"{BASE}-报告.pdf", OUTPUT / f"{BASE}-报告.docx", archive_path]
    write("deliverables/m4/sha256sums.txt", "".join(f"{digest(path.read_bytes())}  {path.name}\n" for path in deliverables))
    print(json.dumps({"archive": archive_path.relative_to(ROOT).as_posix(), **checks}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    build()
