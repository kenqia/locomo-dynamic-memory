#!/usr/bin/env python3
"""Compare appendix numbers with existing evidence; never execute an experiment.

Uses only standard-library file reads and ``git show`` of published archive
entries. Prints metadata/numbers/SHA only. Does not read credentials, Gold,
private logs, raw model responses, SQLite or original conversation files.
Missing local research evidence is reported UNAVAILABLE, never reconstructed.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "3e64811ca4047192f0e3db8a587d013396f04fa8"


def numeric_leaves(value, path=""):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from numeric_leaves(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from numeric_leaves(child, f"{path}[{index}]")


class Audit:
    def __init__(self, root, research):
        self.root, self.research = root, research
        self.metrics = json.loads((root / "docs/supplement/data/metrics.json").read_text())
        self.fields, self.sources, self.errors = {}, {}, []

    def source(self, name, relative, *, research=False, git=False):
        if name in self.sources:
            return self.sources[name]["content"]
        try:
            if git:
                raw = subprocess.check_output(
                    ["git", "show", f"{ARCHIVE}:{relative}"], cwd=self.root,
                    stderr=subprocess.DEVNULL,
                )
                location = f"git:{ARCHIVE}:{relative}"
            else:
                path = (self.research if research else self.root) / relative
                raw = path.read_bytes()
                location = str(path)
            content = json.loads(raw) if relative.endswith(".json") else raw.decode()
            self.sources[name] = {"location": location, "sha256": hashlib.sha256(raw).hexdigest(),
                                  "bytes": len(raw), "status": "AVAILABLE", "content": content}
            return content
        except (OSError, subprocess.CalledProcessError, ValueError):
            self.sources[name] = {"location": relative, "status": "UNAVAILABLE", "content": None}
            return None

    def compare(self, path, expected, source, selector, *, report=False, tolerance=0.000000501):
        actual = dict(numeric_leaves(self.metrics))[path]
        status = "PASS_REPORT" if report else "PASS_JSON"
        if not math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=tolerance):
            status = "MISMATCH"
        self.fields[path] = {"actual": actual, "expected": expected, "status": status,
                             "source": source, "selector": selector, "absolute_tolerance": tolerance}

    def triplet(self, path, source, value, *, mean="mean", ci="bootstrap95"):
        for key, expected in zip(("d", "lo", "hi"), (value[mean], *value[ci])):
            self.compare(f"{path}.{key}", expected, source, f"{mean}/{ci}")

    def report_values(self, name, relative, pattern, paths, *, git=True):
        text = self.source(name, relative, git=git, research=not git)
        if text is None:
            return
        match = re.search(pattern, text, re.S)
        if not match:
            self.errors.append({"source": name, "reason": "Expected public report pattern unavailable"})
            return
        for path, value in zip(paths, match.groups(), strict=True):
            self.compare(path, float(value), name, "curated report expression", report=True)

    def run_json(self):
        base = "experiments/m5-development/"
        c = [self.source(f"C{i}", base + directory + "/metrics-summary.json") for i, directory in
             enumerate(("level-c-results-v1", "level-c-input-v2-results-v1"))]
        e = self.source("E", base + "level-e-results-v1/official-scores.json")
        ep = self.source("E-paired", base + "level-e-results-v1/source-review-paired.json")
        er = self.source("E-runtime", base + "level-e-runtime-terminal-v1.json")
        es = self.source("E-source", base + "level-e-results-v1/source-review-summary.json")
        cp = self.source("C1-paired", base + "level-c-input-v2-results-v1/semantic-paired-differences.json")
        for index, value in enumerate(c):
            if value is None:
                continue
            name = f"C{index}"
            ordinary = value["strata"]["ordinary"]
            for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                self.compare(f"f1_by_stage.rows[{index + 2}].{letter}", ordinary["groups"][arm]["failure_zero_mean"], name, "strata.ordinary.groups.failure_zero_mean")
                self.compare(f"cost_ratio.rows[{index + 1}].{letter}", value["cost_by_arm"][arm]["all_attempts"]["reported_usage_peak_cache_miss_upper_usd"], name, "cost_by_arm.all_attempts.reported_usage_peak_cache_miss_upper_usd")
                for position, key in enumerate(("succeeded", "planned")):
                    expected = sum(value["strata"][s]["groups"][arm][key] for s in ("ordinary", "diagnostic"))
                    self.compare(f"success.rows[{index + 3}].{letter}[{position}]", expected, name, f"sum strata {key}")
                for stratum_index, stratum in enumerate(("ordinary", "diagnostic")):
                    for percentile_index, percentile in enumerate(("p50", "p95")):
                        self.compare(f"latency.rows[{index * 2 + stratum_index}].{letter}[{percentile_index}]", value["runtime"][f"{stratum}/{arm}"]["item_elapsed_seconds"][percentile], name, f"runtime.{stratum}/{arm}.item_elapsed_seconds.{percentile}", tolerance=0.000501)
            self.compare(f"f1_by_stage.rows[{index + 2}].n", ordinary["groups"]["dynamic"]["planned"], name, "strata.ordinary.groups.dynamic.planned")
            for stratum_index, stratum in enumerate(("ordinary", "diagnostic")):
                comparison = value["strata"][stratum]["comparisons"]["all_scorable"]
                self.triplet(f"forest.answer_f1[{index * 2 + stratum_index}]", name, comparison)
                for key, original in (("up", "improved"), ("down", "regressed"), ("tie", "unchanged")):
                    self.compare(f"paired_wlt.rows[{index * 2 + stratum_index + 1}].{key}", comparison[original], name, f"strata.{stratum}.comparisons.all_scorable.{original}")
            self.compare(f"budget_progression.rows[{index + 4}].D_ok", sum(value["strata"][s]["groups"]["dynamic"]["succeeded"] for s in ("ordinary", "diagnostic")), name, "sum strata dynamic succeeded")
            self.compare(f"budget_progression.rows[{index + 4}].D_n", value["questions"], name, "questions")
        if e is not None:
            for index, key in enumerate(("factual_f1", "adversarial_literal_refusal")):
                metric = e["category_metrics"][key]
                self.triplet(f"forest.answer_f1[{index + 4}]", "E", metric["paired_dynamic_minus_hybrid"])
                for k, original in (("up", "improved"), ("down", "regressed"), ("tie", "unchanged")):
                    self.compare(f"paired_wlt.rows[{index + 5}].{k}", metric["paired_dynamic_minus_hybrid"][original], "E", f"category_metrics.{key}.paired_dynamic_minus_hybrid.{original}")
            self.triplet("forest.answer_f1[6]", "E", e["paired_dynamic_minus_hybrid"])
            factual = e["category_metrics"]["factual_f1"]["summary"]
            for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                self.compare(f"f1_by_stage.rows[4].{letter}", factual[arm]["failure_zero_mean"], "E", "category_metrics.factual_f1.summary.failure_zero_mean")
                for position, key in enumerate(("succeeded", "planned")):
                    self.compare(f"success.rows[5].{letter}[{position}]", e["summary"][arm][key], "E", f"summary.{arm}.{key}")
                for stage, original in (("initial", "initial"), ("expanded", "expanded"), ("delivered", "answer_delivered"), ("effective", "effective")):
                    if letter == "H" and stage == "effective":
                        continue
                    for position, k in enumerate((5, 10, 20)):
                        values = [item["source_recall"][original][str(k)] for item in e["items"] if item["arm"] == arm and item["source_recall"][original][str(k)] is not None]
                        self.compare(f"recall_funnel_e25.{letter}.{stage}[{position}]", sum(values) / len(values), "E", f"mean all non-null items {arm}.{original}@{k}; failures retained")
            self.compare("f1_by_stage.rows[4].n", factual["dynamic"]["planned"], "E", "category_metrics.factual_f1.summary.dynamic.planned")
            for position, k in enumerate((5, 10, 20)):
                observed = sorted(int(k) for k in e["items"][0]["source_recall"]["initial"])
                self.compare(f"recall_funnel_e25.K[{position}]", observed[position], "E", "items source_recall rank keys")
        if ep is not None:
            for index, key in enumerate(("source_support", "citation_support", "abstention", "wrong_time", "list_omission")):
                self.triplet(f"forest.source_review[{index}]", "E-paired", ep["overall"][key]["metric"])
        if cp is not None:
            self.triplet("forest.source_review[5]", "C1-paired", cp["summary"]["ordinary"]["metrics"]["source_support"])
        if er is not None:
            for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                group = er["groups"][f"all/{arm}"]
                self.compare(f"cost_ratio.rows[3].{letter}", group["costs"]["all_attempts"]["adapter_reported"]["reported_usage_peak_cache_miss_upper_usd"], "E-runtime", "groups.all.costs.all_attempts.adapter_reported")
                for index, percentile in enumerate(("p50", "p95")):
                    self.compare(f"latency.rows[4].{letter}[{index}]", group["elapsed_seconds"][percentile], "E-runtime", f"groups.all.elapsed_seconds.{percentile}", tolerance=0.000501)
        if es is not None:
            for index, key in enumerate(("source_support", "citation_support", "abstention", "wrong_time", "wrong_event", "list_omission", "wrong_person")):
                for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                    for position, field in enumerate(("positive", "denominator")):
                        self.compare(f"source_review_e25.rows[{index}].{letter}[{position}]", es["by_arm"][arm][key][field], "E-source", f"by_arm.{arm}.{key}.{field}")
        failures = self.source("C-failures", base + "level-c-results-v1/failures.json")
        if failures is not None:
            counts = Counter(item["error_code"] for item in failures)
            for key, original in (("请求字节上限拒绝", "physical_request_policy_rejected"), ("完整解析输入超预算", "complete_resolution_input_budget_exceeded")):
                self.compare(f"failures.groups[2].items.{key}", counts[original], "C-failures", f"count error_code={original}")
        failures = self.source("E-failures", base + "level-e-failures-terminal-v1.json")
        if failures is not None:
            counts = Counter(item["error_code"] for item in failures["items"])
            for key, original in (("invalid_output", "invalid_output"), ("HTTP 402 余额不足", "model_http_error")):
                self.compare(f"failures.groups[4].items.{key}", counts[original], "E-failures", f"count error_code={original}")
        recovery = self.source("conv44-recovery", base + "conv44-relation-recovery-independent-preparation-v1.json")
        if recovery is not None:
            for key, original in (("未知来源 ID 违约", "known_source_required"), ("同状态维度违约", "same_state_dimension_required")):
                self.compare(f"failures.groups[3].items.{key}", recovery["final_error_counts"][original], "conv44-recovery", f"final_error_counts.{original}")

    def run_research(self):
        p6 = self.source("phase6", "experiments/research-v2/phase6/replay-final/summary.json", research=True)
        if p6 is not None:
            for index, row in enumerate(self.metrics["e7a_hits"]["rows"]):
                group = p6["by_conversation"][row["conv"]]
                self.compare(f"e7a_hits.rows[{index}].n", group["baseline"]["reference_source_incidences"], "phase6", f"{row['conv']}.baseline.reference_source_incidences")
                for key, arm in (("base", "baseline"), ("A", "e7a"), ("AB", "e7ab")):
                    self.compare(f"e7a_hits.rows[{index}].{key}", group[arm]["candidate_reference_hits"], "phase6", f"{row['conv']}.{arm}.candidate_reference_hits")
        p8 = self.source("phase8", "experiments/research-v2/phase8/retrieval-statistics.json", research=True)
        if p8 is not None:
            self.triplet("forest.source_review[6]", "phase8", p8["all"]["stages"]["delivered"], mean="paired_delta", ci="bootstrap_95_ci")
            for index in range(3):
                group = p8["by_category"][str(index + 1)]
                self.compare(f"ce_by_category_e18.rows[{index}].n", group["proxy_applicable"], "phase8", f"by_category.{index + 1}.proxy_applicable")
                self.compare(f"ce_by_category_e18.rows[{index}].d", group["stages"]["delivered"]["paired_delta"], "phase8", f"by_category.{index + 1}.stages.delivered.paired_delta")
        attribution = self.source("phase7-attribution", "experiments/research-v2/phase7/failure-attribution.json", research=True)
        if attribution is not None:
            stages = {s["stage"]: s for s in attribution["stages"]}
            for key, stage in (("初始召回疑似缺口", "Initial Retrieval"), ("有效选择疑似缺口", "Resolution Evidence Selection"), ("无来源关联", "Extraction Coverage"), ("已交付仍遗漏", "Answer Generation")):
                self.compare(f"attribution_e16.source_chain_35.{key}", stages[stage]["suspected_source_path_incidences"], "phase7-attribution", f"stages.{stage}.suspected_source_path_incidences")
            diagnostic = attribution["independent_semantic_diagnostic"]
            for key, field in (("具体事实抽取遗漏", "confirmed_specific_fact_extraction_gaps"), ("已有事实未召回/未交付", "confirmed_existing_fact_initial_miss_not_recovered"), ("已交付仍过度拒答", "confirmed_answer_stage_overrefusal")):
                self.compare(f"attribution_e16.confirmed_8.{key}", len(diagnostic[field]), "phase7-attribution", f"independent_semantic_diagnostic len({field})")
            self.compare("attribution_e16.confirmed_8.Answer 预算丢失", diagnostic["confirmed_answer_budget_losses"], "phase7-attribution", "independent_semantic_diagnostic.confirmed_answer_budget_losses")

    def run_reports(self):
        prefix = "docs/research-process/entries/"
        self.report_values("showcase", prefix + "SHOW-01.md", r"16可回答题F1：full([.\d]+)/vector([.\d]+)/hybrid([.\d]+)/dynamic([.\d]+)/raw([.\d]+)；Recall@5/10/20=([.\d]+)/([.\d]+)/([.\d]+)", [*[f"showcase_e5.f1[{i}]" for i in range(5)], *[f"showcase_e5.recall_at.{k}" for k in (5, 10, 20)]])
        self.report_values("showcase", prefix + "SHOW-01.md", r"(16)可回答题F1：full[.\d]+/vector[.\d]+/hybrid([.\d]+)/dynamic([.\d]+)", ["f1_by_stage.rows[0].n", "f1_by_stage.rows[0].H", "f1_by_stage.rows[0].D"])
        self.report_values("baseline-paired-archive", prefix + "V2-05.md", r"(136)胜/(110)负/(459)平", [f"paired_wlt.rows[0].{k}" for k in ("up", "down", "tie")])
        self.report_values("baseline-paired-archive", prefix + "V2-05.md", r"Dynamic完整分母([.\d]+)，Hybrid含unknown上下界\[([.\d]+),", ["f1_by_stage.rows[1].D", "f1_by_stage.rows[1].H"])
        self.report_values("baseline-paired-archive", prefix + "V2-05.md", r"## 统计分母\s+(\d+)", ["f1_by_stage.rows[1].n"])
        self.report_values("first-build", prefix + "R15-01.md", r"关系(89)成功/(29)失败/(1)中断/(173)待执行", [f"failures.groups[0].items.{key}" for key in ("成功", "失败", "中断", "待执行")])
        self.report_values("reader-v2", prefix + "TOP7-04.md", r"完成语义(2)/(8)→(6)/(8)", [f"iteration_pairs.rows[0].{side}[{i}]" for side in ("before", "after") for i in range(2)])
        self.report_values("thinking", prefix + "TOP7-03.md", r"low(8)/(8)完成语义过/direct2/8/disabled(3)/(8)", [f"iteration_pairs.rows[1].{side}[{i}]" for side in ("before", "after") for i in range(2)])
        text = self.source("verbatim", prefix + "VERB-01.md", git=True)
        if text is not None:
            whole = re.search(r"整体正确(\d+)/(\d+)、(\d+)/(\d+)、(\d+)/(\d+)", text)
            facts = re.search(r"干净必需事实(\d+)/(\d+)、(\d+)/(\d+)、(\d+)/(\d+)", text)
            if whole and facts:
                for index, values in ((2, [*whole.groups()[:2], *whole.groups()[2:4]]), (3, [*facts.groups()[:2], *facts.groups()[2:4]]), (4, [*facts.groups()[:2], *facts.groups()[4:6]])):
                    for path, expected in zip([f"iteration_pairs.rows[{index}].{side}[{i}]" for side in ("before", "after") for i in range(2)], values):
                        self.compare(path, expected, "verbatim", "overall/clean required facts report", report=True)
        for name, file, pattern, index in (("window", "TOP145-01", r"整体(4)/(8)vs(4)/(8)", 5), ("first-check", "TOP145-03", r"首次检查总(23)/(32)vs(23)/(32)", 6), ("patch", "TOP145-04", r"语义(2)/(12)vs(2)/(12)", 7)):
            self.report_values(name, prefix + file + ".md", pattern, [f"iteration_pairs.rows[{index}].{side}[{i}]" for side in ("before", "after") for i in range(2)])
        self.report_values("patch", prefix + "TOP145-04.md", r"前文\+复核均(8)/(8)，(109185)→(78242)token", ["iteration_pairs.rows[8].before[0]", "iteration_pairs.rows[8].before[1]", "iteration_pairs.tokens[0].tokens", "iteration_pairs.tokens[1].tokens"])
        for i in range(2):
            path = f"iteration_pairs.rows[8].after[{i}]"
            before = self.fields.get(f"iteration_pairs.rows[8].before[{i}]")
            if before:
                self.compare(path, before["expected"], "patch", "same report states both arms 均8/8", report=True)
        for index, file in enumerate(("SMOKE_RETRY_32768.md", "RESOLUTION_SMOKE_96000.md")):
            name = f"smoke{index}"
            text = self.source(name, "docs/research-v2/" + file, research=True)
            if text is not None:
                for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                    match = re.search(r"\| " + arm + r" \| (\d+)/(\d+) \|", text)
                    if match:
                        for position, value in enumerate(match.groups()):
                            self.compare(f"success.rows[{index}].{letter}[{position}]", value, name, f"table {arm} succeeded/planned", report=True)
                        if letter == "D":
                            for key, value in zip(("D_ok", "D_n"), match.groups()):
                                self.compare(f"budget_progression.rows[{index + 1}].{key}", value, name, "Dynamic succeeded/planned", report=True)
        first = self.source("first-smoke", "docs/research-v2/SMOKE_RESULT.md", research=True)
        if first is not None and "20" in first and ("未执行" in first or "阻塞" in first):
            self.compare("budget_progression.rows[0].D_ok", 0, "first-smoke", "Build failed; QA NOT EXECUTED, not observed QA failure rate", report=True)
            self.compare("budget_progression.rows[0].D_n", 5, "first-smoke", "planned 20 QA / four strategies = 5; not an executed denominator", report=True)
        phase8 = self.source("phase8-report", "docs/research-v2/PHASE8_RESULTS.md", research=True)
        if phase8 is not None:
            match = re.search(r"原 QA 成功 / 失败 / unknown \| (\d+) / (\d+) / (\d+) \| not_measured \| (\d+) / (\d+) / (\d+)", phase8)
            if match:
                numbers = list(map(int, match.groups()))
                for letter, start in (("H", 0), ("D", 3)):
                    for pos, expected in enumerate((numbers[start], sum(numbers[start:start + 3]))):
                        self.compare(f"success.rows[2].{letter}[{pos}]", expected, "phase8-report", "frozen original QA outcomes (not replay success)", report=True)
                for key, expected in (("D_ok", numbers[3]), ("D_n", sum(numbers[3:]))):
                    self.compare(f"budget_progression.rows[3].{key}", expected, "phase8-report", "original Dynamic QA outcomes", report=True)
        paired = self.source("paired-report", "docs/research-v2/PHASE3_PAIRED_DIAGNOSIS.md", research=True)
        if paired is not None:
            for letter, arm in (("H", "hybrid_no_resolution"), ("D", "dynamic")):
                match = re.search(r"\| " + arm + r" \|[^\n]*?¥([\d.]+) / ¥", paired)
                if match:
                    self.compare(f"cost_ratio.rows[0].{letter}", match.group(1), "paired-report", "known CNY Query cost INCLUDING reported cache hit/miss pricing, not all-input-cache-miss", report=True)
        failures = self.source("baseline-failures", "experiments/research-v2/phase3/dynamic-failures.json", research=True)
        if failures is not None:
            count = sum(item["error"]["code"] == "complete_resolution_input_budget_exceeded" for item in failures)
            self.compare("failures.groups[1].items.完整解析输入超预算", count, "baseline-failures", "count exact error code")
            self.compare("failures.groups[1].items.其他", len(failures) - count, "baseline-failures", "all remaining original failed items")

    def report(self):
        numeric = dict(numeric_leaves(self.metrics))
        sections = defaultdict(lambda: Counter())
        unverified = []
        for path in numeric:
            section = path.split(".", 1)[0]
            sections[section]["numeric_fields"] += 1
            if path in self.fields:
                sections[section][self.fields[path]["status"]] += 1
            else:
                sections[section]["UNVERIFIED"] += 1
                unverified.append(path)
        sections["timeline"] = {"numeric_fields": 0, "authored_date_intervals": len(self.metrics["timeline"]),
                                "status": "PARTIAL", "reason": "Date strings are outside numerical-leaf comparison; no independent clock certification"}
        mismatches = [path for path, result in self.fields.items() if result["status"] == "MISMATCH"]
        sources = {k: {field: value for field, value in record.items() if field != "content"}
                   for k, record in self.sources.items()}
        return {"version": "independent-supplement-metrics-audit-v1", "tool": "scripts/verify_supplement_metrics.py",
                "authored_by": "/root/release_spec_review",
                "status": "FAIL" if mismatches else "PARTIAL", "numeric_fields": len(numeric),
                "checked_numeric_fields": len(self.fields), "numeric_mismatches": mismatches,
                "unverified_numeric_fields": unverified, "sections": dict(sections), "fields": self.fields,
                "sources": sources, "source_pattern_errors": self.errors,
                "metrics_sha256": hashlib.sha256((self.root / "docs/supplement/data/metrics.json").read_bytes()).hexdigest(),
                "limitations": ["PASS_JSON compares existing public aggregates/score records; it does not re-score answers or establish semantic truth.",
                                "PASS_REPORT checks frozen published archive excerpts or local narrative tables; original historical raw runs are not re-executed.",
                                "Timeline's 26 authored date intervals, labels, kept booleans and narrative causality are not numerical-leaf checks and remain PARTIAL.",
                                "Some research summaries exist only in an uncommitted sibling worktree. Source SHA records current bytes, not an asserted Git execution commit.",
                                "cost_ratio._note overgeneralizes cache-miss pricing: E12 CNY known cost uses reported cache hit/miss pricing; M5 USD rows use peak cache-miss upper estimates.",
                                "Appendix historical conv44 distribution and E22/E23 single-variable claim require the separate Release errata."],
                "provider_requests": 0, "gold_read": False, "credentials_read": False,
                "private_logs_read": False, "database_opened": False, "experiment_runner_invoked": False,
                "writes_by_verifier": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--research-root", type=Path, default=ROOT.parent / "research-next-20261101")
    args = parser.parse_args()
    audit = Audit(args.root.resolve(), args.research_root.resolve())
    for stage in (audit.run_json, audit.run_research, audit.run_reports):
        try:
            stage()
        except (KeyError, TypeError, ValueError, IndexError) as error:
            audit.errors.append({"stage": stage.__name__, "reason": type(error).__name__})
    result = audit.report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["numeric_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
