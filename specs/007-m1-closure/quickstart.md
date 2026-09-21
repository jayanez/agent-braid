# M1 clean-room reproduction

Use a Python 3.12 or newer interpreter to run the committed protocol against the
exact frozen candidate:

```sh
python3.12 scripts/run_m1_clean_room.py <full-candidate-commit> \
  --python /path/to/python3.12 \
  --output specs/007-m1-closure/reproduction.json
python3.12 scripts/validate_m1_closure.py readiness
```

The runner creates a new local clone and a new virtual environment, disables the
pip cache and bytecode writes, executes the complete bounded suite and records
commands, outputs, return codes, input hashes and repository cleanliness. It may
download the pinned development and Spec Kit dependencies and writes only the
requested evidence artifact outside its temporary clone. The bounded suite
checks pinned Spec Kit rendering plus Codex-only, Claude-only and dual
regeneration in temporary full-history clones. These are structural integration
checks; they do not execute either agent or replace interactive human review.
The suite also requires an explicitly approved M1 milestone-radar review. That
review assesses the committed radar snapshot and does not imply freshness,
scientific consensus or external validation.

The sanitized environment is applied before commit resolution and remains in
force for clone, checkout, virtual-environment creation and all checks. The
whitespace observation inspects the candidate commit rather than an empty clean
worktree diff. Closure protects the complete candidate tree, including normative
authorities, and permits only the enumerated post-freeze assurance, reproduction,
review and status records to change. Any other correction requires a new
candidate and review.

This protocol is executed by Codex under explicit founder authorization and
supervision. It is an internal clean-room reproduction, not independent external
validation. Do not repair a failing candidate during a run; create and freeze a
new candidate instead.
