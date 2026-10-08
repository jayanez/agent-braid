# SPEC-040: Planning quickstart

This packet defines future tooling; `agent-braid tooling` commands are not implemented by this PR.

1. Read spec.md, plan.md, tasks.md, assurance.json and the SPEC-039 program.
2. Resolve the consumed contract review: SPEC-039 architecture/interface review; ADRs 0019/0020 and existing RuntimeTools/grant/verifier contracts.
3. Select the feature explicitly; run prerequisites:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/040-portable-mcp-surface python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
python3 -m scripts.validate_spec_kit
python3 scripts/sync_github_tracking.py source
```

4. Implement the approved slice and pair every task with its prospective validation procedure. Use an isolated dependency environment.
5. Obtain actual receipts, run proportional validation, freeze a clean candidate and record review. Actual host capture uses the separately registered SPEC-044 protocol; do not assume provider cost/source authority.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.
