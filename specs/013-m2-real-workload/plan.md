# Implementation plan

1. Register the real corpus only after two or three independently authored,
   reviewed workstream commits share a pinned `develop` base. Preserve their PR
   URLs, exact commits and effect declarations; do not manufacture sibling
   commits to obtain a positive result.
2. Validate the manifest with `scripts/validate_real_workload_manifest.py`.
   This read-only preflight establishes Git identity and ancestry, not review
   approval or execution permission. Its negative tests cover stale and
   ambiguous inputs.
3. Obtain separate founder acceptance of the exact corpus, base, image digest
   and dependency set under accepted ADR 0015 before adding the test-command
   execution stage. Reuse the pinned T013 Docker base, then materialize candidate and
   serial private trees in separate containers.
   Admit only the fixed `python -m unittest discover -s tests` command under
   the reviewed resource, network and filesystem policy.
4. Record Git and test outcomes for both lanes, failures, negative controls and
   serial/path-overlap baselines. Freeze a candidate, run PR validation and a
   clean-room reproduction. Request scoped human review; leave M2 open.
