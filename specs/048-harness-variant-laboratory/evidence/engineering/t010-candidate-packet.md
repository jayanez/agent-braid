# SPEC-048 T010 laboratory candidate packet

Status: engineering packet for the **offline** laboratory candidate. It neither adopts the ADR nor activates the capability, and it contains **no native, host, model, provider or utility evidence**. Results use deterministic doubles, fixture children and `SimulatedContainment`.

## Exact candidate

- Code candidate: `origin/develop` at `fc1bf9b5996120c82d9c0213bd9385dbd030dcf2` (includes #777 Codex adapter, #778 Claude adapter, #779). This packet's commit adds docs/evidence only; `agent_braid/*.py` and `tests/*` are byte-identical to that commit.
- Collected 2026-10-28 in a worktree reset to that commit (clean status); venv `/opt/homebrew/bin/python3.13`.
- Hashes are sha256 of working-tree bytes, not signatures.

### Inventory

sha256 of all 12 `agent_braid/harness_*.py` modules and 14 `tests/test_harness*.py` files are recorded once, in `inputs` of [../t010.json](../t010.json), and were verified against the files by an independent reviewer. Tests per file: admission 24, cli 22, context 20, foundations 3, host_claude 36, host_codex 64, integration 29, journal 27, lab 26, manifest 13, observation 28, records 19, refinement 30, surface 29 (sum 370).

## Commands actually run

| Command | Exit | Result |
|---|---|---|
| `.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness*.py" -v` | 0 | Ran 370 tests, OK, 0 skips |
| `.venv-speckit/bin/python scripts/validate_change.py --base origin/develop --profile quick` in this worktree | 1 | Fails at the `publication` gate: "public repository contains unreachable objects" (shared object store of the worktree; environmental, repeats on the pre-change tree for `validate_spec_kit.py`). Earlier gates (repository, contracts, release-records) passed. |

Pending (not executed here, results are recorded in the pull request): `quick` and `pr` profiles in a full independent clone via the documented `scripts/restore_public_spec_history.py` flow. A passing worktree-only quick run on a clean tree (exit 0) validated an empty change set and is not counted.

## Independent review (separate reviewer)

A fresh, read-only model reviewer (no shared context, given the code not conclusions) reviewed the candidate at `fc1bf9b5`, ran the 370 tests and reported **no real host/native dispatch path**, with one should-fix and non-blockers. This is a **model review, not a human review**.

| Id | Finding | Disposition |
|---|---|---|
| F1 | `harness_lab.py:315-324` `_check_backend` accepts a `kind=="native"` backend with a self-hashed `Qualification` without checking manifest host kind or `maxNativeSessions` (0); a "native"/`source=host` result is then journalled. Test `tests/test_harness_lab.py:251-256` asserts it. | **Open, not fixed here** (`agent_braid/*` and `tests/*` are outside this packet's scope). In-process callers only; no CLI path; no process is started. Needs a follow-up code change: refuse "native" unless manifest host kind matches and `maxNativeSessions > 0`; invert the test. |
| N1 | `HarnessManifest` built by `dataclasses.replace` is not re-checked against its hash; `run_claude` accepts a forged host kind (`tests/test_harness_host_claude.py:223-241`). | Open limit. Only manifests from `parse_manifest` carry the offline guarantee. |
| N2 | The two tests above lock F1/N1 in as intended. | Treat as label-plumbing tests, not qualification. |
| N3 | Manifest `maxChildProcesses=0` / `maxNetworkConnections=0` are declared, not enforced by `SimulatedContainment` (no RLIMIT_NPROC, network block or jail). | Open limit; already disclosed in `t009-controls.md`. |
| N4 | `tasks.md` T013 says "obtained: none" though `evidence/t013.json` exists. | Out of this task's scope (only the T010 line is editable); flagged to the orchestrator. |

Reviewer did **not** check: line-level logic of refinement/records/context/observation, rest of admission, CLI exit semantics, full test bodies, evidence-hash recomputation, concurrency under real contention, Linux. Those remain unreviewed.

## Native blockers (preserved, not obtained)

- **SPEC-048 T008**: native host/route/containment qualification for Codex and Claude, each separately. Not obtained. No real `codex`/`claude` binary, process, credential, network or model was run. Event shapes and CLI flags are unverified assumptions. Native refusal is an in-process exact-type check plus a constant, not OS containment; same-UID code could bypass it. The Claude adapter runs a native-kind transport when given a caller-built qualification and a `dataclasses.replace` manifest (review N1), so refusal there rests on callers supplying genuine qualifications.
- **SPEC-049 T004**: native corpus admission. Not obtained (depends on T008).
- Founder/scientific/economic decisions, ordinary-use activation, utility and cost claims: none.

## Limits

Offline single-host engineering. Native/model/child/network/retry/cash limits are required to be zero in every parsed manifest (declared; the simulated backend does not enforce child-process or network limits, review N3) and every record carries `executionAuthorization: false`. `SimulatedContainment` bounds and settles the fixture child but confines nothing. Deterministic success is not native qualification. Hosted CI and clean-room reproduction beyond the `pr` profile are not claimed.

## T010 disposition

**Not checked off.** Acceptance asks for a separate review; a model review was obtained, but it left F1 open and no human review exists. T010 stays `[ ]` until F1 is resolved (or explicitly dispositioned by the owner) and the reviewer disposition is accepted.
