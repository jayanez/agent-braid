# Offline laboratory candidate: reproduce and inspect

Read CONSTITUTION.md, AGENTS.md, docs/development/SPEC_KIT.md, the program, this spec/plan/tasks and the actual Git status; use the documented prerequisite helper before task work. The offline `agent_braid/harness_*.py` modules (12) and `tests/test_harness*.py` (14) now exist; the candidate packet is [evidence/engineering/t010-candidate-packet.md](evidence/engineering/t010-candidate-packet.md) with machine record [evidence/t010.json](evidence/t010.json).

**A software packet neither adopts the ADR nor activates the capability.** ADR 0027 adopts only the offline T002–T004 foundations. Every result in the packet uses deterministic doubles, fixture children and `SimulatedContainment`; none is native, host, model, provider or utility evidence.

## Reproduce

```bash
# Python 3.12 or newer (the packet was collected with Homebrew python3.13)
python3 -m venv .venv-speckit
.venv-speckit/bin/pip install -r requirements-speckit.txt -r requirements-dev.txt
.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness*.py" -v
.venv-speckit/bin/python scripts/validate_change.py --base origin/develop --profile quick
.venv-speckit/bin/python scripts/validate_spec_kit.py
.venv-speckit/bin/python scripts/sync_github_tracking.py source
```

Select this feature for helper inspection with `SPECIFY_FEATURE=048-harness-variant-laboratory` and `SPECIFY_FEATURE_DIRECTORY` set to its absolute directory. Run `quick`, `pr` and `validate_spec_kit.py` in a full independent clone after `scripts/restore_public_spec_history.py`: a worktree sharing an object store fails the publication gate ("unreachable objects"). Run the `pr` profile alone (concurrent full runs share `/tmp` globs and flake).

## Inspect without effects

The experimental `harness` command (`inspect`, `validate`, `prepare`, `status`, `recover-inspect`, `compare`) shows candidate/base diffs, evidence losses and profile limits. Only `prepare` has an effect (one private candidate directory). It performs no admission, dispatch or reconciliation.

## Explicit native gaps

Do not launch native probes from this document. These stay refusal conditions, not warnings:

- **SPEC-048 T008** native host/route/containment qualification (Codex and Claude separately): not obtained. Host adapters refuse native transports through in-process checks, not OS containment, and the manifest host profile stays offline-only. Manifest child/network limits are declared, not enforced by the simulated backend.
- **SPEC-049 T004** native corpus admission: not obtained.
- Founder/scientific/economic decisions, ordinary-use activation and utility claims: none.
- **T010 stays unchecked**: a separate model review found one open should-fix (F1: the lab runner can label a run `native` under an offline manifest); no human review exists. See the packet.
