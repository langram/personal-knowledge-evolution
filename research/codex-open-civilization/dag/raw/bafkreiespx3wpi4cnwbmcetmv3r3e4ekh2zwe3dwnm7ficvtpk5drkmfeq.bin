"""Finite quota composition probe, with utilization and duplicate-work limits retained."""
import hashlib
import json
from pathlib import Path

from probe import GRANTS, Candidate, action, check_history

HERE = Path(__file__).resolve().parent


def pair(left_quota, left_amount, right_amount, same_id=False):
    caps = [{'alice': left_quota}, {'alice': 10-left_quota}]
    candidates = [Candidate('C', cap, {'alice': GRANTS['alice'].copy()}) for cap in caps]
    actions = [action('shared' if same_id else name, {'alice': amount})
               for name, amount in [('left', left_amount), ('right', right_amount)]]
    accepted = [c.admit(a, a['effect']) for c, a in zip(candidates, actions)]
    effects = [a['effect']['alice'] if ok else 0 for a, ok in zip(actions, accepted)]
    return {'left_quota': left_quota, 'right_quota': 10-left_quota,
            'requested': [left_amount, right_amount], 'same_id': same_id,
            'accepted': accepted, 'actual_effect_total': sum(effects),
            'check_operations': sum(c.checks for c in candidates)}


def write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def main():
    destination = HERE / 'run-03'
    destination.mkdir(exist_ok=False)
    plan = json.loads((HERE/'quota-pre-registration.json').read_bytes())
    model = plan['model']
    assert model['global_cap'] == 10
    rows = [pair(q, a, b) for q in model['left_quota_values']
            for a in model['request_amount_values'] for b in model['request_amount_values']]
    full = pair(6, 6, 4)
    stranded = pair(6, 7, 0)
    replay = pair(5, 3, 3, same_id=True)
    duplicate_actions = [action('shared', {'alice': 3}), action('shared', {'alice': 3})]
    history = [{'index': i, 'accepted': ok,
                'applied_effect': duplicate_actions[i]['effect'] if ok else {}}
               for i, ok in enumerate(replay['accepted'])]
    duplicate_failures = check_history({'caps': {'alice': 10},
                                      'grants': {'alice': GRANTS['alice'].copy()},
                                      'actions': duplicate_actions}, history)
    details = {'enumerated': rows, 'positive_full_utilization': full,
               'stranded_capacity': stranded,
               'duplicate_work_counterexample': {'pair': replay, 'failures': duplicate_failures}}
    write(destination/'results.json', details)
    assert len(rows) == 1584
    assert all(r['actual_effect_total'] <= 10 for r in rows)
    for r in rows:
        expected = [1 <= r['requested'][0] <= r['left_quota'],
                    1 <= r['requested'][1] <= r['right_quota']]
        assert r['accepted'] == expected
    assert full['accepted'] == [True, True] and full['actual_effect_total'] == 10
    assert stranded['accepted'] == [False, False]
    assert replay['accepted'] == [True, True]
    assert any('replayed-request' in f['problems'] for f in duplicate_failures)
    report = {'status': 'bounded-cap-result-and-residual-counterexample-reproduced',
              'cases': len(rows), 'local_admission_calls': 2*len(rows),
              'check_operations': sum(r['check_operations'] for r in rows),
              'global_cap_violations': sum(r['actual_effect_total'] > 10 for r in rows),
              'formula_acceptance_checks': 'pass', 'positive_full_use': 'pass',
              'stranded_capacity': stranded,
              'global_duplicate_execution': 'still possible; expected counterexample retained',
              'pre_registration_sha256': hashlib.sha256((HERE/'quota-pre-registration.json').read_bytes()).hexdigest(),
              'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Two independent sequential local nodes with truthful effects, fixed grants, fixed disjoint quotas and at most one request each. No live distributed system.'}
    write(destination/'summary.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
