"""Keep counterexamples outside probe.py's sequential, truthful-view assumptions."""
import copy
import hashlib
import json
from pathlib import Path

from probe import CAPS, GRANTS, Candidate, action, check_history

HERE = Path(__file__).resolve().parent


def evaluate(name, actions, candidates, supplied_effects, authoritative_grants):
    history = []
    for i, (a, candidate, supplied) in enumerate(zip(actions, candidates, supplied_effects)):
        accepted = candidate.admit(a, supplied)
        history.append({'index': i, 'accepted': accepted,
                        'applied_effect': a['effect'] if accepted else {}})
    case = {'caps': CAPS.copy(), 'grants': authoritative_grants, 'actions': actions}
    return {'case': name, 'oracle_input': case,
            'effect_view_supplied_to_candidates': supplied_effects,
            'candidate_local_grants': [c.grants for c in candidates],
            'history': history, 'failures': check_history(case, history)}


def main():
    destination = HERE / 'run-02'
    destination.mkdir(exist_ok=False)
    one = action('left', {'alice': 6})
    two = action('right', {'alice': 6})
    distributed = evaluate('independent-full-budget-copies', [one, two],
                           [Candidate('C', CAPS, GRANTS), Candidate('C', CAPS, GRANTS)],
                           [one['effect'], two['effect']], copy.deepcopy(GRANTS))
    hidden = action('hidden', {'alice': 2}, effect={'alice': 2, 'bob': 5})
    false_scope = evaluate('incorrect-effect-view', [hidden], [Candidate('C', CAPS, GRANTS)],
                           [{'alice': 2}], copy.deepcopy(GRANTS))
    stale = action('stale', {'alice': 2})
    current = copy.deepcopy(GRANTS)
    current['alice'] = {'epoch': 3, 'active': False}
    stale_grant = evaluate('revoked-elsewhere-but-local-view-stale', [stale],
                           [Candidate('C', CAPS, GRANTS)], [stale['effect']], current)
    cases = [distributed, false_scope, stale_grant]
    assert all(r['failures'] for r in cases)
    assert all(all(x['accepted'] for x in r['history']) for r in cases)
    record = {'status': 'counterexamples-reproduced', 'candidate': 'C unchanged from run-01',
              'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': cases,
              'meaning': 'The local algorithm does not establish shared serialization, true effects, or current remote authority.'}
    (destination / 'boundary-cases.json').write_bytes(
        (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'status': record['status'], 'cases': [r['case'] for r in cases],
                      'failure_count_by_case': [len(r['failures']) for r in cases]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
