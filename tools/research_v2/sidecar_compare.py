"""Frozen offline two-diagnostic comparison and bounded CPU/wall microbenchmark."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import statistics
import time
from pydantic import ValidationError
from tools.research_v2.sidecar_core import diagnose,RULE_VERSION
from tools.research_v2.sidecar_io import read_frozen
from tools.research_v2.sidecar_schema import SidecarInput
from tools.research_v2.sidecar_research import (
    baseline_fields,canonical_bytes,digest,off_on_off,RESEARCH_VERSION,
)


def _plain(value):
    return value.model_dump(mode='json') if hasattr(value,'model_dump') else value


def _timed(call):
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    value=call()
    return value,time.perf_counter_ns()-wall,time.process_time_ns()-cpu


def _stats(values):
    return {'samples':len(values),'median_ns':statistics.median(values),'min_ns':min(values),'max_ns':max(values)}


def _references_valid(snapshot,result):
    memories={c.memory_id for c in snapshot.claims};sources={s.source_id for s in snapshot.sources}
    if set(result.retained_memory_ids)!=memories:return False
    if result.record.snapshot!=snapshot:return False
    for c in result.claims:
        if c.memory_id not in memories or not set(c.source_ids)<=sources:return False
        if c.event_time.anchor_source_id and c.event_time.anchor_source_id not in c.source_ids:return False
    for link in result.record.event_links:
        if not {link.left_memory_id,link.right_memory_id}<=memories or not set(link.source_ids)<=sources:return False
    if result.query and (not set(result.query.memory_ids)<=memories or not set(result.query.source_ids)<=sources):return False
    return True


def compare_manifest(manifest_path,*,repeats=20):
    if type(repeats) is not int or not 1<=repeats<=200:raise ValueError('repeats must be 1..200')
    path=Path(manifest_path)
    data,before=read_frozen(path)
    checksum=path.with_suffix('.sha256')
    if not checksum.is_file() or checksum.read_text().split()[0]!=before:
        raise ValueError('Missing or changed frozen case digest')
    manifest=json.loads(data)
    if len(manifest['cases'])!=manifest['case_count'] or len({c['case_id'] for c in manifest['cases']})!=manifest['case_count']:
        raise ValueError('Invalid case count or identities')
    rows=[];totals={'control_cpu':0,'control_wall':0,'sidecar_cpu':0,'sidecar_wall':0}
    for ordinal,case in enumerate(manifest['cases']):
        try: snapshot=SidecarInput.model_validate(case['input'])
        except ValidationError:
            rows.append({'case_id':case['case_id'],'status':'contract_rejected','reason':'invalid_sidecar_input'})
            continue
        frozen=digest(snapshot.model_dump(mode='json'))
        # Only validated input is passed to either variant. Expected labels,
        # name/category and validity flags are deliberately not consulted.
        expected_control=baseline_fields(snapshot)
        expected_on=diagnose(snapshot,enabled=True)
        baseline_identity=digest(expected_control);on_identity=digest(_plain(expected_on))
        measurements={v:{'wall':[],'cpu':[]} for v in ('control','sidecar')}
        for round_index in range(repeats):
            order=('control','sidecar') if (round_index+ordinal)%2==0 else ('sidecar','control')
            for variant in order:
                call=(lambda:baseline_fields(snapshot)) if variant=='control' else (lambda:diagnose(snapshot,enabled=True))
                value,wall,cpu=_timed(call)
                if digest(_plain(value))!=(baseline_identity if variant=='control' else on_identity):
                    raise ValueError('Non-deterministic output detected')
                measurements[variant]['wall'].append(wall);measurements[variant]['cpu'].append(cpu)
                totals[variant+'_wall']+=wall;totals[variant+'_cpu']+=cpu
        if digest(snapshot.model_dump(mode='json'))!=frozen:raise ValueError('Input mutation')
        rollback=off_on_off(snapshot)
        if not rollback['response_identity_unchanged'] or not rollback['rollback_has_no_diagnostic']:
            raise ValueError('Rollback altered original research response')
        valid=_references_valid(snapshot,expected_on)
        if not valid:raise ValueError('Output introduced invalid reference')
        rows.append({'case_id':case['case_id'],'status':'compared',
            'input':snapshot.model_dump(mode='json'),
            'control':expected_control,'sidecar':expected_on.model_dump(mode='json'),
            'source_memory_references_valid':valid,'rollback':rollback,
            'timing':{variant:{metric:_stats(values) for metric,values in metrics.items()}
                      for variant,metrics in measurements.items()},
            'extra_median_wall_ns':statistics.median(measurements['sidecar']['wall'])-statistics.median(measurements['control']['wall']),
            'extra_median_cpu_ns':statistics.median(measurements['sidecar']['cpu'])-statistics.median(measurements['control']['cpu'])})
    after=read_frozen(path)[1]
    if before!=after:raise ValueError('Frozen manifest changed during comparison')
    completed=sum(r['status']=='compared' for r in rows)
    n=completed*repeats
    return {'comparison_version':RESEARCH_VERSION,'rule_version':RULE_VERSION,
        'mode':'SYNTHETIC_DIAGNOSTIC_ONLY','provider_calls':0,'production_query_hook':False,
        'quality_claim':'none; supplied-fields control is not production QA or a real model baseline',
        'input_sha256_before':before,'input_sha256_after':after,'input_unchanged':True,
        'environment':{'os':platform.system(),'python':platform.python_version(),'machine':platform.machine()},
        'measurement':{'repeats_per_valid_case':repeats,'warmup_per_variant':1,
            'ordering':'alternating per case and repetition','wall_clock':'perf_counter_ns','cpu_clock':'process_time_ns',
            'scope':'variant function only, validation/I-O/hash/serialization outside measurement',
            'caveat':'Local warm microbenchmark; not network latency, QA quality, billing or statistically significant evidence.'},
        'summary':{'cases':len(rows),'compared':completed,'contract_rejected':len(rows)-completed,
            'response_unchanged_all':all(r['rollback']['response_identity_unchanged'] for r in rows if r['status']=='compared'),
            'references_valid_all':all(r['source_memory_references_valid'] for r in rows if r['status']=='compared'),
            'measured_samples_per_variant':n,
            **{k+'_ns':v for k,v in totals.items()},
            'mean_extra_wall_ns':(totals['sidecar_wall']-totals['control_wall'])/n if n else None,
            'mean_extra_cpu_ns':(totals['sidecar_cpu']-totals['control_cpu'])/n if n else None},
        'cases':rows}


def render_markdown(report):
    s=report['summary'];env=report['environment']
    lines=['# ARCH-03 固定合成案例的诊断对照','',
        '两种方式：control仅检查输入已有字段；sidecar执行ARCH-02的时间、事件和有限问题诊断。control不是生产QA基线；本次不评模型质量，不生成最终答案。','',
        f"环境：{env['os']} / Python {env['python']}。案例{s['cases']}个，比较{s['compared']}个，契约拒绝{s['contract_rejected']}个。",'',
        f"输入未变：{report['input_unchanged']}；回滚原响应未变：{s['response_unchanged_all']}；引用闭合：{s['references_valid_all']}；provider calls：0。",'',
        f"每个有效案例每方式重复{report['measurement']['repeats_per_valid_case']}次，先各预热1次，交替顺序。",'',
        f"本机平均额外wall：{s['mean_extra_wall_ns']} ns；平均额外CPU：{s['mean_extra_cpu_ns']} ns。",'',
        '只测函数体；校验、序列化、文件I/O和哈希在计时外。不等同用户请求时延，不承诺其他机器同数值；负差值保留，不解释为稳定提速。','',
        '| 案例 | control | sidecar | 额外wall中位差 ns |', '| --- | --- | --- | --- |']
    for row in report['cases']:
        if row['status']!='compared':
            lines.append(f"| {row['case_id']} | 输入非法 | 按契约拒绝 | 不计时 |")
            continue
        d=row['sidecar'];q=d['query']
        if q:note='query='+q['evidence_status']+((' / '+q['answer']) if q['answer'] else '')
        elif d['record']['event_links']:note='links='+','.join(l['decision'] for l in d['record']['event_links'])
        else:note='time='+','.join(c['event_time']['status'] for c in d['claims'])
        lines.append(f"| {row['case_id']} | 保留输入字段；无新增推断 | {note} | {row['extra_median_wall_ns']} |")
    lines+=['','完整输入、两种输出、source/memory身份、逐例CPU/wall与off→on→off记录见同目录comparison.json。',
        '未把冻结预期当作推断输入，也未计算正确率；先前ARCH-02语义测试另行报告。非作者成员复核与生产Query接入仍未完成。','']
    return '\n'.join(lines)


def write_report(manifest_path,output_dir,*,repeats=20):
    out=Path(output_dir)
    # Input file and its checksum must never be used as an output directory.
    if out.exists() or out.is_symlink():raise ValueError('Use a new report directory; do not overwrite old results')
    value=compare_manifest(manifest_path,repeats=repeats)
    out.mkdir(parents=True,exist_ok=False)
    (out/'comparison.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'comparison.md').write_text(render_markdown(value),encoding='utf-8')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('tests/fixtures/sidecar_cases.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=20)
    args=p.parse_args()
    try:
        result=write_report(args.manifest,args.output,repeats=args.repeats)
    except (ValueError,TypeError,KeyError,OSError):
        p.exit(2,'Comparison failed: invalid frozen input or output; use a new directory.\n')
    print(json.dumps({'mode':result['mode'],**{k:result['summary'][k] for k in
        ('cases','compared','contract_rejected','response_unchanged_all','references_valid_all')},
        'input_unchanged':True,'provider_calls':0}))

if __name__=='__main__':main()
