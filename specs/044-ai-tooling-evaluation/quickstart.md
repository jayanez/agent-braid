# SPEC-044: Planning quickstart

The current experimental implementation candidate includes `agent-braid tooling` commands and offline evaluation primitives. This planning quickstart describes the remaining prospective gates; paired candidate evidence, host observations and acceptance remain pending.

1. Read spec.md, plan.md, tasks.md, assurance.json and the SPEC-039 program.
2. Resolve the consumed contract review: Protocol review before capture; stable SPEC-040–043 candidate; exact owner-approved source rights and numeric provider/time/resource budget; v3 technical-capture phase with approved human-evaluation deferral record and two abstract independent reviewer roles. Keep humanReviewers empty. Earlier M4 approval is not inherited. See [the deferral decision](human-evaluation-deferral-clarification.md) and the prospective [frozen outcome rubric](../../docs/tooling/OUTCOME_RUBRIC.md).
3. Select the feature explicitly; run prerequisites:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/044-ai-tooling-evaluation python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
python3 -m scripts.validate_spec_kit
python3 scripts/sync_github_tracking.py source
```

4. Implement the approved slice and pair every task with its prospective validation procedure. Use an isolated dependency environment.
5. Obtain actual receipts, run proportional validation, freeze a clean candidate and record review. Actual host capture uses the separately approved v3 SPEC-044 technical registration; the owner’s deferral decision alone does not authorize capture. Preserve all 108 slots and the frozen rubric. Human ratings/adjudication remain pending, human cost remains unknown, and technical readiness cannot mark T007 fully complete, T010 accepted or M4.5 closed.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

## Current installation and telemetry

The original preparation steps above are historical planning context. For the implemented local candidate use [installation](../../docs/tooling/INSTALL.md), [telemetry consent and commands](../../docs/tooling/TELEMETRY.md) and [current alignment](../../docs/tooling/M45_ALIGNMENT.md). Product aggregates do not replace identity-bound receipts, actual native discovery/loading/use, registered attempts or economic accounting. Previously approved SPEC-044/T004 closure stays bound to 482fbcc. T017/T018 remain pending; validated SPEC-047 precedes a future admitted candidate pilot without depending on native evaluation.
