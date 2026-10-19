# Planned commands after implementation

These commands are prospective; no runtime tests or repository profiles ran in the drafting chat. Use the existing repository environment. No installs/downloads are authorized. Execute only after owned test modules exist and dependencies pass. DDP-T01/T08 are document-review tasks and DDP-T09 remains blocked; no meaningless mirror tests are required.

DDP-T02: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_ir -v`

DDP-T03: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_acquisition -v`

DDP-T04: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_registry -v`

DDP-T05: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_decision -v`

DDP-T06: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_consumer tests.test_system_one_verified_stdio -v`

DDP-T07: `.venv-speckit/bin/python -m unittest tests.test_system_one_verified_compatibility -v`

Coordinator during implementation: `.venv-speckit/bin/python scripts/validate_change.py --base develop --profile quick`; once on stable candidate: `.venv-speckit/bin/python scripts/validate_change.py --base develop --profile pr`. Follow classifier escalation and retain raw command/environment/candidate/input hashes, outcomes/skips and limits. Do not claim cached earlier checks cover changed bytes. No experiment/study command is included.

For final documentary import use canonical Spec Kit checks in the authorized context, without regeneration/snapshot/freeze helpers that rewrite existing records. A validation conflict is a finding for coordinator, not permission to alter historical assurance.
