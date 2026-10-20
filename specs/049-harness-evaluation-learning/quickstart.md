# Planning and future implementation entry point

Read CONSTITUTION.md, AGENTS.md, docs/development/SPEC_KIT.md, the program, this spec/plan/tasks and the actual Git status. This package contains planning only; the proposed `harness_*` modules do not exist yet.

Validate source structure with `.venv-speckit/bin/python scripts/validate_spec_kit.py` and `.venv-speckit/bin/python scripts/sync_github_tracking.py source`. Select this feature for helper inspection with `SPECIFY_FEATURE=049-harness-evaluation-learning` and `SPECIFY_FEATURE_DIRECTORY` set to its absolute directory. Use the documented prerequisite helper before task work.

Do not launch native probes from this document. Start at T001 and satisfy dependencies. Synthetic fixture engineering may proceed within authorized implementation scope; it cannot qualify a native sandbox or imply useful model behavior. Native route/containment gaps remain explicit refusal conditions.
