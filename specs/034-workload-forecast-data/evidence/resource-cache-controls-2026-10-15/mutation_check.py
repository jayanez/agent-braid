# SPDX-License-Identifier: AGPL-3.0-only
"""Fixed synthetic guard checks, mutating module source in child memory only.

Run with the isolated development Python from the repository root. JSON goes to
stdout; this script neither edits source nor provisions/runs a model or daemon.
Only the fixed tests below can run. A surviving mutation fails the procedure.
"""
import hashlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
R = 'tests.test_forecast_resource_catalogue.ResourceCatalogueTests.'
C = 'tests.test_forecast_cache.CacheConformanceTests.'
HEALTHY = R + 'test_registered_synthetic_profile_is_bound_copied_and_never_authority'
CACHE_HEALTHY = C + 'test_each_causal_identity_misses_and_cached_uncached_numerics_match'
# module, unique checkpoint, condition/expression, negative-control test, healthy test
GUARDS = [
 ('resources', 'catalogue = parse_record', 'digest(catalogue) == expected_digest', 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _profile(', "resource['hostId'] == self._host_id", 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _profile(', "metadata['availabilityReceipt']['clockId'] == self._clock_id", 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _profile(', "metadata['runtimeRevision'] == self._runtime", 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _profile(', "metadata['isolation']['revision'] == self._isolation", 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _profile(', "metadata['inventoryRevision'] == self._inventory", 'test_configured_pin_host_and_all_revisions_cannot_be_self_asserted', HEALTHY),
 ('resources', 'def _registered_profile(', "resource['profileRevision'] == digest(metadata)", 'test_missing_isolation_receipt_and_forged_metadata_are_rejected', HEALTHY),
 ('resources', 'def _registered_profile(', "receipt['observationsDigest'] == digest(observations)", 'test_availability_receipt_cannot_change_identity_clock_or_observations', HEALTHY),
 ('resources', 'def validate_resource(', "profile['observedNs'] <= now_ns < profile['expiresNs']", 'test_unknown_stale_future_modes_and_each_budget_refuse', HEALTHY),
 ('resources', 'def _registered_profile(', 'all(isolation[name] for name in _CONTROLS[:3])', 'test_missing_isolation_receipt_and_forged_metadata_are_rejected', HEALTHY),
 ('resources', 'def _profile(', "all(metadata['isolation'][name] for name in self._required_controls)", 'test_unsupported_configured_enforcement_refuses_without_invented_caps', HEALTHY),
 ('resources', 'def validate_resource(', 'type(authority_verifier) is ResourceCatalogue', 'test_v2_permissioned_callback_cannot_substitute_for_pinned_full_profile', R + 'test_permissioned_requires_external_review_on_every_use_and_passes_a_copy'),
 ('resources', 'def _admit(', "'parallel' in resource['allowedModes']", 'test_permissioned_parallel_cannot_remove_minimum_enforcement', R + 'test_permissioned_requires_external_review_on_every_use_and_passes_a_copy'),
 ('resources', 'def resolve(', "workers <= operations and (workers == 1 if mode == 'serial' else workers >= 2)", 'test_unknown_stale_future_modes_and_each_budget_refuse', HEALTHY),
 ('advice', 'key=self.cache.key(', 'cancellation is not None and cancellation.is_set()', 'test_cancellation_during_cache_read_precedes_consuming_its_payload', CACHE_HEALTHY),
 ('advice', 'key=self.cache.key(', 'deadline is not None and time.monotonic()>=deadline', 'test_cancel_or_deadline_during_a_miss_never_invokes_the_backend', CACHE_HEALTHY),
 ('advice', 'else:result=predict_baseline(', 'cancellation is not None and cancellation.is_set()', 'test_cancellation_after_backend_does_not_commit_an_incomplete_result', CACHE_HEALTHY),
 ('advice', "if result['status']=='forecast':self.cache.put", 'cancellation is not None and cancellation.is_set()', 'test_cancel_or_deadline_during_cache_commit_removes_only_its_entry', CACHE_HEALTHY),
 ('advice', "if result['status']=='forecast':self.cache.put", 'deadline is not None and time.monotonic()>=deadline', 'test_cancel_or_deadline_during_cache_commit_removes_only_its_entry', CACHE_HEALTHY),
 ('advice', 'if cached is not None:', "cached['modelDigest']==model_digest", 'test_a_cached_model_identity_cannot_be_relabelled_as_the_current_artifact', CACHE_HEALTHY),
]


def child(index, value):
    module, checkpoint, expression, negative, healthy = GUARDS[index]
    name = 'agent_braid.forecast_' + module
    loaded = importlib.import_module(name)
    source = Path(loaded.__file__).read_text()
    assert source.count(checkpoint) == 1, checkpoint
    at = source.index(expression, source.index(checkpoint))
    changed = source[:at] + value + source[at + len(expression):]
    exec(compile(changed, loaded.__file__, 'exec'), loaded.__dict__)
    target = (R if module == 'resources' else C) + negative if value == 'True' else healthy
    # For if-conditions in _admit/cancellation/deadline, False disables the guard;
    # require() predicates use True to disable. The call-site kind is explicit.
    conditional = expression.startswith(('cancellation ', 'deadline ', "'parallel'"))
    if conditional:
        target = (R if module == 'resources' else C) + negative if value == 'False' else healthy
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(unittest.defaultTestLoader.loadTestsFromName(target))
    return {'test': target, 'killed': not result.wasSuccessful(), 'failures': len(result.failures),
            'errors': len(result.errors), 'diagnostic': stream.getvalue()[-1800:]}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == 'child':
        index = int(sys.argv[2]); value = sys.argv[3]
        assert 0 <= index < len(GUARDS) and value in ('True', 'False')
        print(json.dumps(child(index, value))); return 0
    assert len(sys.argv) == 1
    rows = []
    for index, (module, checkpoint, expression, _, _) in enumerate(GUARDS):
        for value in ('True', 'False'):
            process = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'child', str(index), value],
                                     cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
            result = json.loads(process.stdout)
            rows.append(dict(module='agent_braid/forecast_' + module + '.py', checkpoint=checkpoint,
                             expression=expression, replacement=value, **result))
    inputs = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        ROOT / 'agent_braid/forecast_resources.py', ROOT / 'agent_braid/forecast_advice.py',
        ROOT / 'agent_braid/forecast_cache.py', ROOT / 'tests/forecast_resource_helpers.py',
        ROOT / 'tests/test_forecast_resource_catalogue.py', ROOT / 'tests/test_forecast_cache.py',
        ROOT / 'specs/034-workload-forecast-data/fixtures/synthetic-resource-catalogue.json',
        Path(__file__).resolve())}
    print(json.dumps({'version': 'agent-braid-synthetic-mutation-controls-v1', 'domain': 'synthetic in-memory guards',
                      'inputHashes': inputs, 'mutations': rows, 'survivors': sum(not row['killed'] for row in rows),
                      'sourceFilesModified': False, 'modelOrVmExecution': False}, indent=2))
    return int(any(not row['killed'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
