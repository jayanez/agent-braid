# SPEC-065: security re-check of the lines PR #988 touched, before T009

**This re-check is not a qualification.** It issues no record, qualifies no effect, authorizes no native
session, probe or account setup, and changes no code. `executionAuthorization` stays `false`. A GO below
means engineering readiness of the touched lines for the T009 attempt; it does not replace the founder's
conditional go for T009 (`founder-decisions-20261103.json`) and says nothing about whether the sandbox
profile enforces anything (decided only by the T009 observation and the T010 human issuance).

## Record

| Item | Value |
|---|---|
| Date | 2026-11-03 |
| Pull request | #988, "refactor(har): consolidation review fixes for 065/067 modules" |
| Squash commit | `c01baa353ab054b273c8b03315012f4c2de51286` (`c01baa35`) |
| Source branch / head | `har/consolidation-review`, head `74ce9823` |
| Scope | Only the lines #988 touched in SPEC-065 runtime modules: `_egress_verdict`, `classify_session` and `make_qualification_runner` (and the runner `endpoints` option) in `agent_braid/harness_qualification_probes.py`; `_InitWatch._line` in `agent_braid/harness_transport_claude.py` |
| Reviewer | A read-only Sonnet reviewer, workflow `wf_7729baa6-546` (independent in context; not a human review and not a different model family) |
| Verdict | **GO**. Required fixes: none |
| Tests run | Python 3.12 venv: `test_harness_qualification_probes`, `test_harness_transport_claude`, `test_harness_assurance`, `_receipts`, `_render`, `_risk`: 409 tests OK, 1 skipped. No credential or disk bound was touched |

## Items

- **`_egress_verdict`.** The `endpoints` default of `None` keeps the static `ALLOWED_ENDPOINTS` check. A tunnel
  to a host outside the list, or any `unexpectedDirect`, still yields `allowed` (a violation). The
  inconclusive and denied logic is unchanged; no refusal was weakened.
- **`make_qualification_runner`.** It passes `policy.endpoints` (`ALLOWED_ENDPOINTS` plus the validated
  `refresh_endpoints`). `EgressProxy` is built from the same `policy.endpoints`, so the verdict allow-list and
  the enforcement allow-list are identical. This matches founder decision NC-1 and does not widen egress. The
  runner stores `endpoints` as a tuple copy.
- **`classify_session`.** It only forwards `endpoints` to the NET-05-CLI verdict. CRED-05 and HOST-01 are
  untouched. A refused session or a missing key source is still `inconclusive`. Classification still decides on
  `SUBSCRIPTION_KEY_SOURCES` (DRV-14).
- **`_InitWatch._line`.** The new `type(source) is str` guard routes an unhashable `apiKeySource` (list or
  dict) to `_reject('route')` instead of raising `TypeError` on the `frozenset` lookup. Stricter and fail
  closed. `none` and `oauth` still pass.

## Consequences for T009

The touched lines are re-checked, so the precondition of `tasks.md` T009 for #988 is met. Any later edit to the
backend, probes, transport or quota module moves the environment and catalog hash and needs a new re-check of
the touched lines before the attempt. The earlier re-check `probe-catalog-delta-recheck.md` (#985) and its
residuals (DRV-04, 07, 08, 09, 11, 13, 15 and MDRV-01 to MDRV-04) are unchanged by this one.
