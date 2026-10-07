# SPDX-License-Identifier: AGPL-3.0-only
"""Reference planning controls only; no scientific or feature acceptance decision."""
import json

BRANCHES = frozenset({'router', 'schema', 'hooks', 'export', 'catalogue', 'lifecycle'})
TASKS = {'router':'T003','schema':'T004','hooks':'T007','export':'T002','catalogue':'T005','lifecycle':'T006'}


def prerequisites(selected, *, learned_router=False, learned_catalogue=False):
    if not isinstance(selected, frozenset) or not selected <= BRANCHES:
        raise ValueError('invalid selection')
    tasks = {'T001'} | {TASKS[item] for item in selected}
    upstream = {'SPEC-028/T008'} if selected else set()
    if selected & {'export','lifecycle'} or ('router' in selected and learned_router) or ('catalogue' in selected and learned_catalogue):
        upstream.add('SPEC-030/T008')
    if 'catalogue' in selected:
        upstream.add('SPEC-029/T009')
    return {'tasks':sorted(tasks),'upstream':sorted(upstream)}


def check():
    # Expected closures are declared independently from these branch rules.
    cases = [
        ('schema-only',frozenset({'schema'}),['T001','T004'],['SPEC-028/T008']),
        ('hooks-only',frozenset({'hooks'}),['T001','T007'],['SPEC-028/T008']),
        ('deferred-export-reference-lifecycle',frozenset({'lifecycle'}),['T001','T006'],['SPEC-028/T008','SPEC-030/T008']),
        ('all-deferred',frozenset(),['T001'],[]),
        ('selected-deterministic-cut',frozenset({'router','schema','hooks'}),['T001','T003','T004','T007'],['SPEC-028/T008']),
        ('catalogue-without-router',frozenset({'catalogue'}),['T001','T005'],['SPEC-028/T008','SPEC-029/T009']),
    ]
    results = []
    for name,selection,tasks,upstream in cases:
        actual = prerequisites(selection)
        assert actual == {'tasks':tasks,'upstream':upstream}, name
        results.append({'case':name,'selected':sorted(selection),'required':actual,'outcome':'passed'})
    assert prerequisites(frozenset({'router'}),learned_router=True)['upstream'] == ['SPEC-028/T008','SPEC-030/T008']
    assert prerequisites(frozenset({'catalogue'}),learned_catalogue=True)['upstream'] == ['SPEC-028/T008','SPEC-029/T009','SPEC-030/T008']
    return {'format':'selected-product-planning-controls-v1','cases':results,
            'extraControls':['learned-router requires model gate','learned-catalogue requires data and model gates'],
            'limits':'Reference dependency closures transcribed from SPEC-032 tasks; no accepted implementation, trained model, empirical evidence, human acceptance or promotion inferred. Reference lifecycle may omit export/router but still requires its served model gate.',
            'executionAuthorization':False,'humanReview':'pending'}


if __name__ == '__main__':
    print(json.dumps(check(),indent=2,sort_keys=True))
