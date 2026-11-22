# Implementation plan: SPEC-085 harness promotion pointers

## Approach

- **Model.** A pure, offline module replays an append-only, hash-chained pointer
  journal (`braid-harness-pointers/v0.1`, OD-1 (a)) into the state of three labels.
  It reads the T003 registration, the T013 registry and the SPEC-083 verdict records
  that a move cites. It reads no clock, host, model or network; the caller supplies
  ticks, as in T013.
- **Moves.** One function applies a move or a rollback after checking the label,
  the actor (REQ-003), the chain (REQ-004) and the evidence gate of the target label
  (REQ-005 to REQ-007). It returns a new journal value; saving is atomic under an
  exclusive lock and refuses a journal that does not extend the stored one (T013
  pattern).
- **Write path.** Per OD-3 (a), an owner-run one-command script wraps the move. Per
  OD-2 (a), the resulting journal change lands through an owner-merged pull request.
- **Read path.** `harness registry-status` gains an optional pointer-journal argument
  and reports labels, last records, history length and divergence from the T013
  active profile. The SPEC-080 skill shows that view and nothing else.
- **This PR.** spec, plan, tasks, validation plan and assurance record. No code.

## Constitutional check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence; negative results valid | Design expectation stated as such; closing as no-go is valid |
| 5 | Effects are explicit | A move writes only the pointer journal (REQ-009); the views write nothing (REQ-008) |
| 12 | Concurrency control, not prompts | Hash chain and extend-only save refuse lost updates (REQ-004) |
| 13, 14 | Evidence, not verdicts | Each move cites hashed evidence; views show records, not a score |
| 19 | Real, measurable problem | Promotion and rollback today are not single auditable operations (benchmark section 3) |
| 20 | Analysis and execution separate | No label grants execution; `executionAuthorization` false |
| 23, 24 | Semantics before production | Format and gates are reviewed before code (T001, T002) |

No MUST conflict found.

## Affected files for the later code phase (named, not edited)

- New: `agent_braid/harness_pointers.py`, `tests/test_harness_pointers.py`.
- New (OD-3 (a)): `scripts/har_pointer_move.py` and its test
  `tests/test_har_pointer_move.py`.
- Changed: `agent_braid/harness_cli.py` (`registry-status` read view),
  `tests/test_harness_cli.py`.
- Changed: the SPEC-080 skill (planned `integrations/agent-braid/plugin/harness/SKILL.md`),
  only after SPEC-080 is approved.
- Changed at release: `docs/tooling/HARNESSING.md`.
- Unchanged: `agent_braid/harness_promotion.py`, `agent_braid/harness_auto_promotion.py`
  and their tests (OD-1 (a)).

## Phases

1. P0 review: owner decisions OD-1 to OD-7 (T001) and the Codex review (T002).
2. P1 format and module: journal format, replay, gates, refusals and tests.
3. P2 surfaces: CLI read view, owner script, skill text.
4. P3 rehearsal: a synthetic move, rollback and forged-record run on fixtures.
5. P4 release record: release under OD-7, or a recorded no-release outcome.

## Validation profile

- This PR: documentation and an assurance record. Assurance records are sensitive
  paths, so `quick` escalates per `docs/development/VALIDATION_PROFILES.md`; the CI
  `validate` aggregate on the PR head is the `pr` evidence.
- Code phase: targeted `tests/test_harness_pointers.py` and
  `python3 -m scripts.validate_spec_kit` while iterating, `quick` after each coherent
  group, CI `pr` on the PR head.

## Rollback

- Documentation: revert the PR.
- Code: reinstall the previous plugin release; the pointer journal is a separate file
  and can be ignored or removed without touching T013 records.
- A bad label move is undone by a rollback record (REQ-007), never by editing history.
