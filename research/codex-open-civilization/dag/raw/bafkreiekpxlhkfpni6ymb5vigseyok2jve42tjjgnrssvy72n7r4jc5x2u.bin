"""Read-only replay and graph checks; --record writes one final acceptance receipt."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import snapshot

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE/'experiment'))
import probe
import boundary_probe
import quota_probe


def read(name):
    return json.loads((HERE/name).read_bytes())


def digest(name):
    return hashlib.sha256((HERE/name).read_bytes()).hexdigest()


def check_graph():
    snapshot.verify()
    index = read('dag/index.json')
    assert [r['round'] for r in index['rounds']] == [1, 2, 3]
    objects = {p.stem: snapshot.decode(p.read_bytes()) for p in (HERE/'dag/objects').glob('*.cbor')}
    prior_root = None
    prior_proposals = {}
    checked_files = 0
    for r in index['rounds']:
        number = r['round']
        receipt = read(f'dag/round-{number:02}.json')
        record = read(f'round-{number:02}-record.json')
        root = objects[r['root']]
        assert root['schema'] == 'cnr/snapshot@1' and root['round'] == number
        assert receipt['parent'] == prior_root
        assert root['parents'] == snapshot.linkset([prior_root] if prior_root else [])
        assert root['roots'] == snapshot.linkset([receipt['activity']])
        activity = objects[receipt['activity']]
        assert activity['round'] == number and activity['title'] == record['title']
        assert activity['files'] == receipt['files']
        assert [f['path'] for f in receipt['files']] == record['files']
        assert activity['proposals'] == snapshot.linkset(receipt['proposals'])
        assert activity['basis_commit'] == '15c9dfe82ecbb8f9495ab5eb1b55cd777b2f80f7'
        proposals = {objects[key]['id']: (key, objects[key]) for key in receipt['proposals']}
        assert set(proposals) == {'P1', 'P2', 'P3', 'P4', 'P5'}
        for item in record['proposals']:
            key, stored = proposals[item['id']]
            assert all(stored[k] == v for k, v in item.items())
            assert stored['author_adoption'] is False
            assert stored['authored_by'] == {'kind': 'ai', 'id': 'codex'}
            old = prior_proposals.get(item['id'])
            assert stored['previous'] == (snapshot.link(old) if old else None)
            prior_proposals[item['id']] = key
        for f in receipt['files']:
            data = (HERE/f['path']).read_bytes()
            assert len(data) == f['bytes']
            assert data == (HERE/'dag/raw'/(f['raw']['$link']+'.bin')).read_bytes()
            checked_files += 1
        prior_root = r['root']
    assert index['latest_proposals'] == prior_proposals
    reached = set()

    def walk(key):
        if key in reached:
            return
        reached.add(key)
        if key in objects:
            for child in snapshot.links(objects[key]):
                walk(child)
        else:
            assert (HERE/'dag/raw'/(key+'.bin')).is_file()

    walk(prior_root)
    raw = {p.stem for p in (HERE/'dag/raw').glob('*.bin')}
    assert reached == set(objects) | raw
    return {'rounds': 3, 'objects': len(objects), 'raw_blocks': len(raw),
            'file_version_checks': checked_files, 'latest_root': prior_root,
            'proposal_lineages': 5, 'unreachable_blocks': 0}


def check_sequential():
    plan = read('experiment/pre-registration.json')
    inputs = read('experiment/run-01/inputs.json')
    assert inputs == probe.fixtures()+probe.generated(plan['generated_cases'])
    result = [probe.run_case(case, mode) for mode in 'ABC' for case in inputs]
    assert result == read('experiment/run-01/results.json')
    report = read('experiment/run-01/summary.json')
    assert report['program_sha256'] == digest('experiment/probe.py')
    assert report['pre_registration_sha256'] == digest('experiment/pre-registration.json')
    assert report['actions_per_candidate'] == sum(len(x['actions']) for x in inputs) == 2015
    aggregate = {}
    for mode in 'ABC':
        rows = [r for r in result if r['candidate'] == mode]
        aggregate[mode] = {'traces': len(rows), 'failing_traces': sum(bool(r['failures']) for r in rows),
                           'admitted_actions': sum(r['admitted'] for r in rows),
                           'check_operations': sum(r['check_operations'] for r in rows),
                           'maximum_retained_request_ids_in_one_trace': max(r['retained_request_ids'] for r in rows)}
    assert aggregate == report['results']
    c_rows = [r for r in result if r['candidate'] == 'C']
    for case, row in zip(inputs, c_rows):
        if 'expected_C' in case:
            assert [x['accepted'] for x in row['history']] == case['expected_C']
    assert [aggregate[m]['failing_traces'] for m in 'ABC'] == [106, 101, 0]
    return {'traces_per_candidate': len(inputs), 'actions_per_candidate': 2015,
            'failing_traces': {m: aggregate[m]['failing_traces'] for m in 'ABC'}}


def check_boundaries():
    record = read('experiment/run-02/boundary-cases.json')
    assert record['program_sha256'] == digest('experiment/boundary_probe.py')
    for stored in record['cases']:
        oracle = stored['oracle_input']
        candidates = [probe.Candidate('C', oracle['caps'], g) for g in stored['candidate_local_grants']]
        actual = boundary_probe.evaluate(stored['case'], oracle['actions'], candidates,
                                         stored['effect_view_supplied_to_candidates'], oracle['grants'])
        assert actual == stored and actual['failures']
    assert len(record['cases']) == 3
    return {'counterexamples_reproduced': [r['case'] for r in record['cases']]}


def check_quotas():
    plan = read('experiment/quota-pre-registration.json')['model']
    result = read('experiment/run-03/results.json')
    rows = [quota_probe.pair(q, a, b) for q in plan['left_quota_values']
            for a in plan['request_amount_values'] for b in plan['request_amount_values']]
    assert rows == result['enumerated'] and len(rows) == 1584
    for r in rows:
        assert r['actual_effect_total'] <= 10
        assert r['accepted'] == [1 <= r['requested'][0] <= r['left_quota'],
                                 1 <= r['requested'][1] <= r['right_quota']]
    assert quota_probe.pair(6, 6, 4) == result['positive_full_utilization']
    assert quota_probe.pair(6, 7, 0) == result['stranded_capacity']
    duplicate = result['duplicate_work_counterexample']
    assert quota_probe.pair(5, 3, 3, same_id=True) == duplicate['pair']
    actions = [probe.action('shared', {'alice': 3}), probe.action('shared', {'alice': 3})]
    history = [{'index': i, 'accepted': True, 'applied_effect': a['effect']} for i, a in enumerate(actions)]
    assert probe.check_history({'caps': {'alice': 10}, 'grants': {'alice': probe.GRANTS['alice']},
                                'actions': actions}, history) == duplicate['failures']
    assert duplicate['failures']
    report = read('experiment/run-03/summary.json')
    assert report['program_sha256'] == digest('experiment/quota_probe.py')
    assert report['pre_registration_sha256'] == digest('experiment/quota-pre-registration.json')
    assert report['cases'] == len(rows) and report['global_cap_violations'] == 0
    assert report['local_admission_calls'] == 2*len(rows) == 3168
    assert report['check_operations'] == sum(r['check_operations'] for r in rows) == 17688
    return {'enumerated_pairs': len(rows), 'global_cap_violations': 0,
            'stranded_capacity_reproduced': True, 'duplicate_execution_reproduced': True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--record', action='store_true')
    args = ap.parse_args()
    if args.record and (HERE/'verification.json').exists():
        raise RuntimeError('Acceptance receipt already exists; run read-only verification.')
    result = {'schema': 'cnr/verification@1', 'status': 'pass',
              'graph': check_graph(), 'sequential_replay': check_sequential(),
              'boundary_replay': check_boundaries(), 'quota_replay': check_quotas()}
    expected_book = read('sources/evidence.json')['author_basis']['book_sha256']
    assert hashlib.sha256((ROOT/'book/current.md').read_bytes()).hexdigest() == expected_book
    result['book_sha256_unchanged'] = expected_book
    texts = {f'round-{n:02}.md': (HERE/f'round-{n:02}.md').read_text(encoding='utf-8') for n in (1, 2, 3)}
    result['cjk_characters'] = {name: len(re.findall(r'[\u4e00-\u9fff]', text)) for name, text in texts.items()}
    for path in HERE.glob('*.md'):
        for href in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in href or href.startswith('#'):
                continue
            target = (path.parent/href.split('#')[0]).resolve()
            assert target.is_relative_to(ROOT.resolve()), href
            if target == HERE/'verification.json' and args.record:
                continue
            assert target.exists(), (path.name, href)
    result['relative_markdown_links'] = 'pass'
    result['limits'] = 'Artifact identity, lineage, deterministic finite replay and unchanged book; no human, deployment, fairness or energy validation.'
    receipt = HERE/'verification.json'
    if args.record:
        final = dict(result, recorded_at=datetime.now(timezone.utc).isoformat())
        receipt.write_bytes((json.dumps(final, ensure_ascii=False, indent=2)+'\n').encode())
    elif receipt.exists():
        old = json.loads(receipt.read_bytes())
        old.pop('recorded_at')
        assert old == result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
