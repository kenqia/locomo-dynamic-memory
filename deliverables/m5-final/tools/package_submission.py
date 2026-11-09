"""Build M5 materials in a new directory using the verified public allowlist."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
M5 = ROOT / "deliverables/m5-final"
# These frozen study outputs contain source excerpts. Keep originals in the
# research archive; they are deliberately absent from the submission snapshot.
CONTROLLED_STUDY_FILES = {
    "experiments/evidence-flow-20261109/audit.json",
    *("experiments/live-boundary-20261109/" + name for name in (
        "HUMAN_OUTPUTS.md", "HUMAN_REVIEW.md", "ai-review-summary.json",
        "ai-review.json", "author-audit.json", "entity-source-audit.json",
        "human-review-record.json", "human-review-submitted.txt", "outputs.json",
        "results.json", "review-packets.json")),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def copy_files(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new, nonexistent directory")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    package = output / "M5_Final_Submission"
    package.mkdir()

    manifest = json.loads((ROOT / "public-evidence-manifest.json").read_text())
    paths = set()
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise ValueError("unsafe public manifest path")
        if digest(path) != item["sha256"]:
            raise ValueError("public evidence hash mismatch: " + item["path"])
        if item["path"] not in CONTROLLED_STUDY_FILES:
            paths.add(path)
    for folder in (M5 / "figures", ROOT / "process/meetings"):
        paths.update(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts)

    spec = importlib.util.spec_from_file_location("existing_packager", ROOT / "scripts/package_personal_release.py")
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    paths = sorted(paths)
    findings = scanner.scan(paths)
    scan = {"source_files": len(paths), "findings": findings,
            "upstream_literal_catalog_available": (ROOT / "data/raw/locomo/locomo10.json").is_file(),
            "scope": "existing package scanner: credential patterns and exact known upstream text; not human media review"}
    (output / "source-scan.json").write_text(json.dumps(scan, ensure_ascii=False, indent=2) + "\n")
    if findings:
        raise SystemExit("Packaging blocked; see metadata-only source-scan.json")

    reproduction = package / "05_Reproduction"
    reproduction.mkdir()
    snapshot_manifest = {**manifest,
                         "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                                    "sha256": digest(p)} for p in paths],
                         "scope": "submission snapshot; controlled source excerpts excluded",
                         "excluded_controlled_study_files": sorted(CONTROLLED_STUDY_FILES)}
    manifest_bytes = (json.dumps(snapshot_manifest, ensure_ascii=False, indent=2) + "\n").encode()
    source_identity = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "public_manifest_sha256": digest(ROOT / "public-evidence-manifest.json"),
        "snapshot_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "excluded_controlled_study_files": sorted(CONTROLLED_STUDY_FILES),
        "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in paths],
    }
    identity_bytes = (json.dumps(source_identity, ensure_ascii=False, indent=2) + "\n").encode()
    with tarfile.open(reproduction / "source-code.tar.gz", "x:gz") as archive:
        for path in paths:
            info = archive.gettarinfo(str(path), arcname=path.relative_to(ROOT).as_posix())
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            with path.open("rb") as stream:
                archive.addfile(info, stream)
        for name, data in (("SUBMISSION_SOURCE.json", identity_bytes),
                           ("public-evidence-manifest.json", manifest_bytes)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    (reproduction / "SOURCE_VERSION.json").write_bytes(identity_bytes)
    shutil.copy2(M5 / "REPRODUCE.md", reproduction / "REPRODUCE.md")

    report = package / "01_Report"
    report.mkdir()
    for suffix in ("md", "docx", "pdf"):
        shutil.copy2(M5 / "01_Report" / ("Final_Technical_Report." + suffix), report)
    shutil.copy2(ROOT / "docs/supplement/supplement.pdf", report / "Research_Supplement.pdf")
    presentation = package / "02_Presentation"
    presentation.mkdir()
    for name in ("Final_Presentation.pptx", "Final_Presentation.pdf", "Presenter_Notes.md", "Q_and_A.md"):
        shutil.copy2(M5 / "02_Presentation" / name, presentation)
    copy_files(M5 / "03_Demo", package / "03_Demo")
    if not list((package / "03_Demo").glob("*.mp4")):
        raise ValueError("final demo video is required")
    copy_files(M5 / "figures", package / "figures")
    process = package / "04_Process"
    process.mkdir()
    shutil.copy2(M5 / "PROCESS.md", process)
    for name in ("team-workflow.md", "software-requirements-specification.md"):
        shutil.copy2(ROOT / "docs/requirements" / name, process)
    for name in ("ARCHITECTURE.md", "RUNBOOK.md", "SIDECAR_FREEZE.md"):
        shutil.copy2(ROOT / "docs/release" / name, process)
    for name in ("0001-memory-architecture.md", "0003-temporal-event-sidecar.md", "0004-sidecar-offline-adoption.md"):
        shutil.copy2(ROOT / "docs/adr" / name, process)
    copy_files(ROOT / "process/meetings", process / "meetings")
    for source, name in (("README_SUBMISSION.md", "README.md"), ("VIDEO_STATUS.md", "VIDEO_STATUS.md")):
        shutil.copy2(M5 / source, package / name)
    files = sorted(p for p in package.rglob("*") if p.is_file())
    (package / "SHA256SUMS.txt").write_text("".join(f"{digest(p)}  {p.relative_to(package).as_posix()}\n" for p in files))
    with zipfile.ZipFile(output / "m5-final.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output))
    print(json.dumps({"package": str(package), "zip": str(output / "m5-final.zip"),
                      "source_files": len(paths), "submission_files": len(files) + 1,
                      "zip_sha256": digest(output / "m5-final.zip")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
