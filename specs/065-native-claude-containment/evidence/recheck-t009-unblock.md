# SPEC-065: security re-check of the T009 unblock edits (NC-3 and RV-16)

**This re-check is not a qualification.** It issues no record, qualifies no effect, authorizes no native
session, probe or account setup. `executionAuthorization` stays `false`. A GO below means engineering
readiness of the touched lines for the T009 attempt; it does not replace the founder's conditional go
(`founder-decisions-20261103.json`) and says nothing about whether the sandbox profile enforces anything
(decided only by the T009 observation and the T010 human issuance).

## Record

| Item | Value |
|---|---|
| Date | 2026-11-03 |
| Decisions implemented | `founder-decisions-20261103b.json`: NC-3 amended (whole 27.x series), RV-16 rule change |
| Branch | `har/065-t009-unblock`, base `origin/develop` (includes #998, `b1e8a7bf`) |
| Scope | `agent_braid/harness_containment_macos.py`: `_OS_SERIES`, `_MIN_HUMAN_UID`, `_account_facts` (the `_console_uid` helper is removed), the `operator_account` constructor input, the operator lookup in `_check_mechanism`. `scripts/har_t009_attempt.py`: the `user-is-not-operator-account` check, the `--operator-account` input, the removed console check |
| Reviewer | The implementing agent, as a self re-check. It is not independent: the pre-PR review of the track and the orchestrator's re-check are still required before the founder starts the runbook |
| Verdict | **GO** for both changes, with the residuals below. Required fixes: none |
| Tests run | Python 3.13 venv: `test_harness_containment_macos`, `test_har_t009_attempt`, `test_harness_qualification_probes`, `test_harness_transport_claude`, `test_harness_quota`, `test_harness_manifest`: 446 tests OK, 3 skipped (opt-in or platform-gated tests). Nothing native ran |

## Change 1: NC-3, the whole 27.x series

Verdict: **GO**.

- **Edit.** `_OS_SERIES` is `27\.\d{1,3}(?:\.\d{1,3})?\Z`, used with `fullmatch`. It accepts `27.0`, `27.0.1`,
  `27.2`, `27.10.3`; it refuses `26.x`, `28.0`, `27`, `27.`, `270`, `2.7`, a fourth component, a component of
  four digits and trailing text. The build pattern is unchanged.
- **What it guarantees.** The widening changes only which builds are allowed to be *qualified*, not which are
  *trusted*. The product version and the build are inside the environment hash (`HostFacts`), and the backend
  requires the hash to equal the one in both qualification records. A build without its own T009 bundle and T010
  records therefore still refuses with `environment-drift` (tested for 27.0, 27.0.2, 27.2, 27.10.3 and a
  maximal value). The NC-11 probe subset still runs before every session. The founder's decision text
  ("self-check re-run per build stays") holds.
- **Residuals.** (1) Behavior of `sandbox-exec` on a 27.x minor that was never observed is not known in
  advance; the T009 bundle on the founder's 27.2 build is the first observation, and every later build needs its
  own bundle. (2) `\d` in a Python `str` pattern also matches non-ASCII decimal digits. The value comes from
  `sysctl` decoded as ASCII with replacement, so a non-ASCII digit cannot reach it; this was already true of the
  old pattern and is unchanged.

## Change 2: RV-16, the account rule

Verdict: **GO**.

- **Edit.** `_account_facts(account, entry, uid, operator_uid)` no longer reads `/dev/console` (the helper
  `_console_uid` and the driver's `console_uid` are removed, and a test asserts the console is never `stat`ed).
  It refuses with `dedicated-user-unsafe` when: a privileged gid (0 or 80, primary or supplementary) is present
  (unchanged); `uid < 500` (new, `_MIN_HUMAN_UID`); `uid == operator_uid` (new); or the home is not an owned,
  private directory (unchanged). Groups or home that cannot be read still refuse.
- **Where the operator comes from (design).** A required keyword-only constructor input of
  `MacOSContainment`, `operator_account`, validated at construction (`_ACCOUNT` pattern, not the lab account;
  otherwise `invalid-policy`) and resolved with `pwd.getpwnam` on every run in `_check_mechanism`. The
  driver passes a required `--operator-account`. It is not a `ContainmentPolicy` field: the policy describes the
  environment that the hash binds and the profile renders, and the operator account is a refusal input of the
  backend, not an environment fact, so the policy schema, the profile and the environment hash do not change
  because of it. There is no default.
- **Fail closed.** A missing input is a `TypeError`; a non-string, empty, malformed or lab-equal name is
  `invalid-policy`; a name that does not resolve, or resolves to a uid below 500 (root, `_`-accounts), is
  `operator-account-unresolved`; an operator with the lab account's uid (the same account under another
  name, or the lab account run as the founder) is `dedicated-user-unsafe`. The driver mirrors each case in its
  check `user-is-not-operator-account` and skips the environment-hash step when the check fails, so the dry run
  cannot print a hash for an account the backend would refuse. It also adds the operator's home to the homes
  that `founder-home-unreadable` must find closed, so that check no longer depends on the account listing.
- **What the rule guarantees.** The lab never runs as the account named as the founder's, never as a system
  account, never in admin or wheel, and never with a loose home, on every run. The console owner is not a
  security input any more: the sandbox (deny-default profile, no `mach-lookup`) does not depend on who owns the
  console, and the property that matters, that the lab cannot read the founder's home, is checked
  independently by `founder-home-unreadable` and by the profile.
- **Residuals.** (1) The operator account is a caller-supplied value. A wrong but valid account name
  (another user instead of the founder) would defeat the "not the founder's own account" intent. It is
  mitigated by the required flag, by the dry-run output that names the account, by the orchestrator's check of
  it, and by `founder-home-unreadable`, which proves the lab cannot traverse the named home. (2) The operator
  account is not recorded in `run_evidence` or the bundle, and is not part of the environment hash; a run
  that named a different operator is not distinguishable afterwards. (3) Under fast user switching the
  founder's own session and processes stay alive while the lab account is in front; a non-root lab account
  cannot signal or read them, and this is the same exposure as any second local user. (4) The runbook still
  asks the operator to check what the code cannot see (sudoers rules, ACLs, groups such as `_developer`).

## Driver edits that are not security rules

The quota prompts now say claude.ai Usage or the phone (NC-6 wording only); the freshness, malformed-input and
`harness_quota` rules are untouched. The in-memory attempt records are unchanged (not issuance, NC-9).

## Consequences for T009

No fix is required. Before the founder starts step 1 of the runbook: the track's pre-PR review and the
orchestrator's independent re-check of these lines, the merge, and a fresh export of the code at the merged
commit (step 5), because the environment hash binds the backend source.
