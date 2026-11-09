"""Compare exact temporal parsing before/after, without a model or Gold answers."""
import argparse
import hashlib
import json
import subprocess
import types
from pathlib import Path

from locomo_memory.temporal import explicit_question_date, question_interval


# Independent literal expectations, not generated from the implementation.
CASES = [
    ('Where on 2023-07-22?', '2023-07-22', None),
    ('Where on July 22, 2023?', '2023-07-22', None),
    ('Where on 22 July 2023?', '2023-07-22', None),
    ('Where on Jul 22, 2023?', '2023-07-22', None),
    ('Where before 2023-07-22?', None, (None, '2023-07-22')),
    ('Where after July 22, 2023?', None, ('2023-07-22', None)),
    ('Where since 22 July 2023?', None, ('2023-07-22', None)),
    ('What was known by 2023-07-22?', None, (None, '2023-07-22')),
    ('Where until 2023-07-22?', None, (None, '2023-07-22')),
    ('Where during July 2023?', None, ('2023-07-01', '2023-07-31')),
    ('Where during February 2024?', None, ('2024-02-01', '2024-02-29')),
    ('Where during February 2023?', None, ('2023-02-01', '2023-02-28')),
    ('Where during Apr 2023?', None, ('2023-04-01', '2023-04-30')),
    ('Where during December 2023?', None, ('2023-12-01', '2023-12-31')),
    ('Where before Paris on 2023-07-22?', '2023-07-22', None),
    ('What did Alex receive from John on July 22, 2023?', '2023-07-22', None),
    ('Where between July 2023 and August 2023?', None, None),
    ('Where from 2023-07-01 to 2023-07-31?', None, None),
    ('Where on 2023-02-30?', None, None),
    ('Where now?', None, None),
]


def run(baseline_ref):
    source = subprocess.check_output(['git', 'show', baseline_ref+':src/locomo_memory/temporal.py'])
    baseline = types.ModuleType('baseline_temporal')
    exec(compile(source, 'baseline_temporal.py', 'exec'), baseline.__dict__)
    rows = []
    for question, expected_point, expected_bounds in CASES:
        before = baseline.explicit_question_date(question)
        after = explicit_question_date(question)
        interval = question_interval(question) if after is None else None
        before_point = before.isoformat() if before else None
        after_point = after.isoformat() if after else None
        bounds = (interval['start'], interval['end']) if interval else None
        rows.append(dict(question=question, expected_point=expected_point, expected_bounds=expected_bounds,
            before_point=before_point, after_point=after_point, after_interval=interval,
            before_pass=before_point == expected_point and expected_bounds is None,
            after_pass=after_point == expected_point and bounds == expected_bounds))
    return dict(scope='20 synthetic temporal parsing boundaries; not answer quality or model coreference',
        baseline_ref=baseline_ref, baseline_temporal_sha256=hashlib.sha256(source).hexdigest(),
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        model_calls=0, before_passed=sum(row['before_pass'] for row in rows),
        after_passed=sum(row['after_pass'] for row in rows), total=len(rows), cases=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.baseline_ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('total', 'before_passed', 'after_passed', 'model_calls')}))


if __name__ == '__main__':
    main()
