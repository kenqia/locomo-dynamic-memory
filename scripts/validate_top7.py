"""Read-only validation of user-provided iteration records; no model calls."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'version_id', 'issue_id', 'failure_stage', 'affected_cases', 'severity',
          'root_cause', 'proposed_change', 'regression_status', 'evidence',
          'acceptance_criteria', 'verification', 'source_version_ids', 'required_gates'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_verified(issue):
    if issue['regression_status'] != '已验证':
        return
    verification = issue['verification']
    require(verification['acceptance_met'] is True, 'verified issue lacks accepted evidence')
    gates = issue['required_gates']
    require(bool(gates) and set(gates) <= {'offline', 'live', 'semantic'}, 'invalid verification gates')
    require(all(verification.get(gate) == 'passed' for gate in gates), 'verified issue has unpassed gates')
    require(bool(verification.get('evidence_refs')), 'verified issue has no validation evidence')
    for evidence in verification['evidence_refs']:
        path = Path(evidence['worktree']) / evidence['path']
        require(path.is_file() and digest(path) == evidence['sha256'], 'validation evidence missing or changed')


def check_versions(versions):
    for version in versions.values():
        if version.get('identity_file') is not None:
            path = Path(version['identity_file'])
            if not path.is_absolute():
                path = Path(version['worktree']) / path
            require(path.is_file(), 'identity file missing: ' + str(path))
            require(digest(path) == version['identity_file_sha256'], 'identity file hash changed: ' + str(path))


def check_issue(issue, versions):
    require(FIELDS <= issue.keys(), 'missing issue fields')
    require(issue['version_id'] in versions, 'unknown current issue version')
    require(set(issue['source_version_ids']) <= versions.keys(), 'unknown source version')
    require(issue['root_cause']['status'] in {'已证实', '疑似', '未知'}, 'invalid root cause status')
    require(issue['regression_status'] in {'未修', '已修待测', '已验证', '复发'}, 'invalid regression status')
    check_verified(issue)
    for subproblem in issue.get('subproblems', []):
        check_verified(subproblem)
    for case in issue['affected_cases']:
        require(case['version_id'] in versions, 'unknown case version')
        require(bool(case['scope']) and bool(case['unit']), 'case lacks scope or unit')
        affected, denominator = case['affected'], case['denominator']
        require(denominator is None or type(denominator) is int and denominator >= 0, 'invalid denominator')
        require(affected is None or type(affected) is int and affected >= 0, 'invalid affected count')
        if affected is not None and denominator is not None:
            require(affected <= denominator, 'affected count exceeds denominator')
        if affected is None or denominator is None:
            require(bool(case.get('limitations')), 'unknown count lacks explanation')
    require(bool(issue['evidence']), 'issue lacks evidence references')
    for evidence in issue['evidence']:
        require(evidence['version_id'] in issue['source_version_ids'], 'evidence version not declared')
        require(evidence['worktree'] == versions[evidence['version_id']]['worktree'], 'evidence worktree mismatch')
        path = Path(evidence['worktree']) / evidence['path']
        require(path.is_file(), 'evidence file missing: ' + str(path))
        require(digest(path) == evidence['sha256'], 'evidence hash changed: ' + str(path))


def validate(directory):
    registry = read(directory / 'issues.json')
    versions, issues = registry['versions'], registry['issues']
    check_versions(versions)
    ids = [i['issue_id'] for i in issues]
    require(len(ids) == len(set(ids)), 'duplicate stable issue ID')
    require(registry['current_version_id'] in versions, 'unknown registry version')
    for issue in issues:
        check_issue(issue, versions)
    rounds = sorted((directory / 'rounds').glob('*.json'))
    require(bool(rounds), 'no user-provided rounds')
    snapshots = sorted((directory / 'versions').glob('*.json'))
    anchored_rounds = {read(path)['round_id'] for path in snapshots}
    for path in rounds:
        record = read(path)
        require(record.get('round_id', path.stem) in anchored_rounds, 'round lacks an immutable snapshot anchor')
        check_versions(record['versions'])
        source = record.get('source_record')
        if source:
            source_path = directory / source['path']
            require(source_path.is_file() and digest(source_path) == source['sha256'], 'user source record changed')
        items = record['items']
        require(record['provided_by'] == 'user', 'round must be user-provided')
        require(record['order_policy'] == 'preserve_user_order', 'round order policy changed')
        require(0 <= len(items) <= 7, 'round exceeds seven items')
        require([i['rank'] for i in items] == list(range(1, len(items) + 1)), 'invalid user ranks')
        item_ids = [i['issue_id'] for i in items]
        require(len(item_ids) == len(set(item_ids)), 'duplicate round issue ID')
        require(set(item_ids) <= set(ids), 'round references unregistered issue')
        for item in items:
            check_issue(item, record['versions'])
    for path in snapshots:
        snapshot = read(path)
        round_path = directory / 'rounds' / (snapshot['round_id'] + '.json')
        require(digest(round_path) == snapshot['round_sha256'], 'initial round was changed')
        original = read(round_path)['items']
        require(snapshot['issue_ids'] == [i['issue_id'] for i in original], 'snapshot changed user order')
        require(snapshot['version_id'] in versions, 'unknown snapshot version')
        if 'versions' in snapshot:
            check_versions(snapshot['versions'])
            for issue in snapshot.get('issues', []):
                check_issue(issue, snapshot['versions'])
    return dict(status='verified', issues=len(issues), user_rounds=len(rounds),
                version_snapshots=len(snapshots), new_provider_calls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=ROOT / 'process/top7')
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.directory.resolve()), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, 'Top 7 validation failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
