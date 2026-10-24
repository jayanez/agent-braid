# Quickstart — SPEC-052 (planning and validation commands)

Status: draft planning. No workflow, builder change or recipe exists yet, so the commands below fall into two groups: those that can run today against the planning packet, and those that become runnable as tasks land. Nothing here authorizes a commit, push, remote write, publication, concurrent agent or release. Every command runs from the repository root in the isolated environment (`.venv-speckit/bin/python`).

## Read first

[spec](spec.md) and its clarifications, [plan](plan.md), [research](research.md), [tasks](tasks.md), [contracts](contracts/README.md), [validation plan](validation-plan.md), [program](program.md) and [ADR proposal](adr-proposal.md).

## Runnable now (planning packet)

```sh
# Structural Spec Kit checks, then the current authority snapshot of this feature
.venv-speckit/bin/python -m scripts.validate_spec_kit snapshot specs/052-claude-workflow-gate
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

Expected: both succeed; `human_review` stays `pending`; `obtained_evidence` stays empty. A changed authority hash is reported, not hidden.

```sh
# Draft contracts are valid JSON Schema draft 2020-12 (planning aid, not evidence)
.venv-speckit/bin/python - <<'PY'
import json, jsonschema
for name in ("braid-gate-args", "braid-gate-result"):
    schema = json.load(open(f"specs/052-claude-workflow-gate/contracts/{name}.schema.json"))
    jsonschema.Draft202012Validator.check_schema(schema)
    print(name, "ok")
PY
```

```sh
# Task lines parse as the tracking synchronizer expects
.venv-speckit/bin/python scripts/sync_github_tracking.py source
```

Expected: succeeds only when every spec directory has a parseable `tasks.md`.

## Becomes runnable as PR2 tasks land

| After | Command | Expected |
| --- | --- | --- |
| T004, T008 | `.venv-speckit/bin/python -m unittest tests.test_claude_workflow_gate -v` | Static checks pass; the mutation controls (parallel wrapper, isolation option, fifth agent) fail the check as designed |
| T005 | same module, fixture classes | Corpus builds deterministically; Git version recorded; a Git without `merge-tree --write-tree` reports unavailable |
| T006, T009–T014 | same module, argument and degradation classes | Every invalid input ends `refused` with zero agent calls; a runtime-enabled registration with a planted grant ends `refused` (`runtime-enabled-workspace`); a sentinel hook, fsmonitor, merge driver or filter never runs; busy, unregistered, limit and timeout map to their statuses without retry; the equal-to-base case is refused |
| T047 | same module, host-restart and untrusted-text classes (after the PR #672 rebase) | A duplicated phase result and a busy refusal after a completed attempt end schema-valid and `inconclusive` where attributable to the gate's own attempt; `prepare` is requested at most once; no script retry; later prompts embed only resolved 40-hex identifiers |
| T007, T013 | same module, schema classes | Samples of every status validate; extra fields, `executionAuthorization` other than false and a missing canonical limit are rejected |
| T015, T016 | `.venv-speckit/bin/python -m unittest tests.test_plugin_package -v` | The default build excludes `workflows/` and the explicit pre-adoption opt-in build includes `workflows/braid-gate.js` (engineering-only); two builds are byte-identical; a tampered, missing or extra workflow file fails verification; existing skills and the portable manifest are byte-identical; no hooks, mods, agents or monitors |
| T017, T018 | `.venv-speckit/bin/python -m unittest tests.test_validation_profiles -v` | The workflow path classifies under the new named domain, sensitive, no unknown path |
| Any increment | `.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick` | Escalates to sensitive on `specs/**`, `integrations/**` and `scripts/build_native_plugin.py` |
| Stable PR2 candidate | `.venv-speckit/bin/python -m scripts.validate_change --base develop --profile pr` | Passes once; it is not host verification, review or approval |

If the optional JavaScript runtime layer is used, record its version in the evidence; when it is absent the suite reports an unavailable observation for those cases and still runs the structural checks.

## Host verification and release (founder-driven, later)

These steps need the founder's Claude Code host at EUR 0 additional spend and are not runnable by the planning packet.

1. Build a candidate outside the checkout from a clean commit (T023, T039):
   `.venv-speckit/bin/python scripts/build_native_plugin.py --output <new-dir-outside-checkout> --cache <cache-dir>` plus, until the ADR amendment is adopted (T036), the explicit opt-in that includes `workflows/` (flag name fixed by T016; the artifact is engineering-only). An `--allow-dirty` artifact is likewise engineering-only and never a releasable identity.
2. Install the package with the native manager on the chosen host and register a fixture workspace through the setup skill (operator action). Register it analysis-only: the gate refuses any registration set in which a workspace has runtime enabled or a grant store (REQ-016). Configure the host permission allowlist of REQ-016 and record it with HV-1/HV-5.
3. Run the probes HV-1 to HV-5 and save transcripts and outcomes under `specs/052-claude-workflow-gate/evidence/` with the Claude Code version (T024–T028); record the disposition (T029).
4. Run the gate over the fixture matrix (T030): 2, 4 and 5 operations; independent edits; conflicting edits; a deletion; the equal-to-base case. Compare the envelope with direct `git merge-tree --write-tree --merge-base=<base> <a> <b>` and with the bundled CLI `analyze-git` output for the same commits.
5. Operator side, outside the workflow: any grant is issued with the existing grant policy command and execution goes through the owned runtime or manual integration. The gate returns `executionAuthorization: false` and no command in this quickstart issues a grant.

## Reading a result

`ok-certified` means: no conflicting or unknown pair, clean baseline, replay evidence with a certificate for 2 to 4 operations and a prepared batch. It does not mean the merge is safe, order independent, faster or semantically correct. `hazards-found`, `inconclusive`, `busy` and `refused` are valid outcomes. A skipped replay or an absent baseline is never a pass. A moved or deleted reference ends `inconclusive` with `staleRefs`. `advisoryOrder` is `null` (the gate declares no dependencies) and the order used for `prepare` is the input order, not a recommendation. Every result carries the `assurance` block (class `0-heuristic`, `notAGuarantee`) and the limits.
