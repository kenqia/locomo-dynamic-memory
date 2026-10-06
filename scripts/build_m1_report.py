#!/usr/bin/env python3
"""Rebuild the M1 Word report using the shared report layout."""
from build_m2_report import ROOT, build

if __name__ == "__main__":
    build(ROOT / "docs/requirements/team-workflow.md", milestone="M1")
