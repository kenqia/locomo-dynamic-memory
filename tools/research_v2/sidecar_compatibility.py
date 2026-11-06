"""ARCH-04 compatibility on two new SYNTHETIC complete Build fixtures.

Uses real public APIs/storage with controlled model and embedding adapters from
existing tests. Never opens historical/live DBs or makes external provider calls.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile

from tools.research_v2.sidecar_io import diagnose_file
from tools.research_v2.sidecar_research import research_view
from tools.research_v2.sidecar_schema import SidecarInput

ROOT=Path(__file__).resolve().parents[2]


def sample_data():
    return [{'sample_id':'conv-a','conversation':{
        'speaker_a':'Alex','speaker_b':'Sam',
        'session_1_date_time':'1:00 pm on 1 May, 2023',
        'session_1':[{'dia_id':'D1:1','speaker':'Alex','text':'I live in Paris on May 1, 2023.'},
                     {'dia_id':'D1:2','speaker':'Sam','text':'I work in London.'}],
        'session_2_date_time':'1:00 pm on 2 May, 2023',
        'session_2':[{'dia_id':'D2:1','speaker':'Alex','text':'I moved from Paris to Rome on 2 May 2023.'}]},
        'qa':[{'question':'Where?','answer':'ANNOTATION ONLY','evidence':['D1:1']}]}]


def run_compatibility(output_dir):
    out=Path(output_dir)
    if out.exists() or out.is_symlink():raise ValueError('Use a new compatibility output directory')
    # Explicit test-only dependencies, as in existing offline demo tooling.
    tests=str(ROOT/'tests')
    if tests not in sys.path:sys.path.insert(0,tests)
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.config import Settings
    from locomo_memory.model import DeepSeekModel
    from test_queries import complete_build,query_provider
    from test_versions import complete,provider
    from test_retrieval import ControlledEmbedder
    rows=[]
    with tempfile.TemporaryDirectory(prefix='sidecar-compat-') as temp:
        work=Path(temp)
        for name,handler,builder in [('single-source-temporal',query_provider,complete_build),
                                      ('multi-source-preference',provider,complete)]:
            location=work/name;location.mkdir()
            settings=Settings(db_path=location/'synthetic.sqlite3')
            calls=[]
            def transport(request):
                calls.append(1)
                return handler(request)
            controlled=DeepSeekModel(settings,api_key='synthetic-offline-only',transport=httpx.MockTransport(transport))
            with TestClient(create_app(settings,model=controlled,embedder=ControlledEmbedder())) as client:
                built=builder(client,deepcopy(sample_data()))
                bid=built[1] if isinstance(built,tuple) else built
                response=client.get(f'/builds/{bid}/export')
                if response.status_code!=200:raise ValueError('Synthetic fixture export failed')
                bundle=response.json()
            exported=location/'frozen-export.json'
            exported.write_text(json.dumps(bundle,ensure_ascii=False,sort_keys=True),encoding='utf-8')
            before_db=hashlib.sha256(settings.db_path.read_bytes()).hexdigest()
            before_export=hashlib.sha256(exported.read_bytes()).hexdigest()
            prior_calls=len(calls)
            value=diagnose_file(exported,location/'diagnostic.json',enabled=True,format='export',origin='synthetic')
            snapshot=SidecarInput.model_validate(value['diagnostic']['record']['snapshot'])
            before=json.dumps(bundle,sort_keys=True)
            disabled=research_view(bundle,snapshot)
            enabled=research_view(bundle,snapshot,enabled=True)
            rollback=research_view(bundle,snapshot,enabled=False)
            after_db=hashlib.sha256(settings.db_path.read_bytes()).hexdigest()
            after_export=hashlib.sha256(exported.read_bytes()).hexdigest()
            checks={
                'complete_export_valid':bundle['build']['status']=='complete',
                'build_fingerprint_preserved':snapshot.provenance.build_fingerprint==bundle['build']['fingerprint'],
                'memory_ids_preserved':set(value['diagnostic']['retained_memory_ids'])=={m['memory_id'] for m in bundle['memories']},
                'database_bytes_unchanged':before_db==after_db,
                'export_bytes_unchanged':before_export==after_export,
                'response_identity_unchanged':disabled.response is enabled.response is rollback.response is bundle,
                'response_value_unchanged':before==json.dumps(bundle,sort_keys=True),
                'diagnostic_enabled':enabled.status=='diagnosed',
                'rollback_disabled':rollback.status=='disabled' and rollback.diagnostic is None,
                'no_extra_controlled_calls':len(calls)==prior_calls,
            }
            if not all(checks.values()):raise ValueError('Synthetic compatibility check failed')
            rows.append({'fixture':name,'origin':'synthetic','build_id':bid,
                'build_fingerprint':bundle['build']['fingerprint'],
                'export_schema':bundle['schema_version'],'memory_count':len(bundle['memories']),
                'source_count':len(bundle['sources']),'relation_count':len(bundle['relations']),
                'multi_source_memory':any(len(m['source_ids'])>1 for m in bundle['memories']),
                'database_sha256_before':before_db,'database_sha256_after':after_db,
                'export_sha256_before':before_export,'export_sha256_after':after_export,
                'checks':checks,'controlled_setup_calls':prior_calls,'external_provider_calls':0})
    result={'mode':'SYNTHETIC_COMPATIBILITY_ONLY','fixtures':rows,
        'all_passed':all(all(r['checks'].values()) for r in rows),
        'environment':{'os':platform.system(),'python':platform.python_version()},
        'external_provider_calls':0,'real_historical_builds_checked':0,
        'limits':'Two synthetic complete Build fixtures, not two real historical research Builds. No real QA quality evaluation.',
        'temporary_databases_removed':True}
    out.mkdir(parents=True,exist_ok=False)
    (out/'compatibility.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 两个合成完整Build的兼容检查','',result['limits'],'',
        '| Fixture | Memory | Source | 多来源Memory | 所有检查 |', '| --- | --- | --- | --- | --- |']
    for r in rows:
        lines.append(f"| {r['fixture']} | {r['memory_count']} | {r['source_count']} | {r['multi_source_memory']} | {all(r['checks'].values())} |")
    lines+=['','由实际公开API与SQLite构建，生成和Embedding均受控；没有真实模型调用。',
        '诊断前后原数据库及导出字节摘要相同，Build身份保留，开启/关闭不改写原响应。',
        '数据库仅在新临时目录创建并删除，报告不包含数据库或模型wire。真实成员复核仍待完成。','']
    (out/'compatibility.md').write_text('\n'.join(lines),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:result=run_compatibility(args.output)
    except (ValueError,TypeError,KeyError,OSError):p.exit(2,'Compatibility failed; inspect tests and use a new output directory.\n')
    print(json.dumps({'fixtures':len(result['fixtures']),'all_passed':result['all_passed'],
        'external_provider_calls':0,'real_historical_builds_checked':0,
        'temporary_databases_removed':result['temporary_databases_removed']}))

if __name__=='__main__':main()
