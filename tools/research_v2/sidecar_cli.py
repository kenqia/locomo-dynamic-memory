"""Independent offline research CLI, default off. Not a production Query hook."""
import argparse
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from tools.research_v2.sidecar_core import RULE_VERSION, diagnose
from tools.research_v2.sidecar_io import diagnose_file, read_frozen
from tools.research_v2.sidecar_schema import SidecarInput


def run_cases(manifest_path,output_path,*,enabled=False):
    path,out=Path(manifest_path).resolve(strict=True),Path(output_path)
    if out.exists() or out.is_symlink() or out.resolve()==path:
        raise ValueError('Output must be new; preserve prior runs and frozen manifest')
    data,digest=read_frozen(path)
    # Byte-level case freeze; newline transformations must be explicit revisions.
    checksum=path.with_suffix('.sha256')
    if not checksum.is_file() or checksum.read_text().split()[0]!=digest:
        raise ValueError('Frozen manifest checksum mismatch or missing')
    manifest=json.loads(data)
    if len(manifest['cases'])!=manifest['case_count']:
        raise ValueError('Manifest case count mismatch')
    rows=[]
    for case in manifest['cases']:
        try:
            # Deliberately forward ONLY input. Expected behavior/category/name
            # never reaches inference; invalid expectations are not consulted.
            snapshot=SidecarInput.model_validate(case['input'])
            result=diagnose(snapshot,enabled=enabled)
            rows.append({'case_id':case['case_id'],'status':'diagnosed',
                         'diagnostic':result.model_dump(mode='json')})
        except ValidationError:
            rows.append({'case_id':case['case_id'],'status':'contract_rejected',
                         'reason':'invalid_sidecar_input'})
    if read_frozen(path)[1]!=digest:raise ValueError('Manifest changed during run')
    payload={'mode':'SYNTHETIC_DIAGNOSTIC_ONLY','rule_version':RULE_VERSION,
        'enabled':enabled,'input_sha256_before':digest,'input_sha256_after':digest,
        'input_unchanged':True,'cases':rows,'provider_calls':0,
        'quality_claim':'none; no real model evaluation; no semantic scorer'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as handle:
        json.dump(payload,handle,ensure_ascii=False,indent=2);handle.write('\n')
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    cases=sub.add_parser('cases');cases.add_argument('--manifest',type=Path,default=Path('tests/fixtures/sidecar_cases.json'))
    cases.add_argument('--output',type=Path,required=True);cases.add_argument('--enabled',action='store_true')
    snapshot=sub.add_parser('snapshot');snapshot.add_argument('--input',type=Path,required=True)
    snapshot.add_argument('--output',type=Path,required=True);snapshot.add_argument('--enabled',action='store_true')
    snapshot.add_argument('--format',choices=['snapshot','export'],default='snapshot')
    snapshot.add_argument('--origin',choices=['synthetic','source_snapshot'])
    snapshot.add_argument('--question');snapshot.add_argument('--as-of')
    args=parser.parse_args()
    try:
        if args.command=='cases':
            value=run_cases(args.manifest,args.output,enabled=args.enabled)
            print(json.dumps({'cases':len(value['cases']),'rejected':sum(c['status']=='contract_rejected' for c in value['cases']),
                'enabled':args.enabled,'input_unchanged':True,'provider_calls':0}))
        else:
            value=diagnose_file(args.input,args.output,enabled=args.enabled,format=args.format,
                origin=args.origin,question=args.question,as_of=args.as_of)
            print(json.dumps({'enabled':args.enabled,'input_unchanged':value['input_unchanged'],'provider_calls':0}))
    except (ValueError,KeyError,TypeError,OSError):
        # Do not print raw private content or arbitrary exception data.
        parser.exit(2,'Sidecar failed: invalid input, frozen identity, or output path. Use a new output file.\n')

if __name__=='__main__': main()
