# SPEC-065: Quickstart

Implementation in progress: T003 to T008 are done at unit level, the pre-T009 fixes (#979) and the mini delta
re-check (GO for engineering readiness, #985) are merged, and T009 awaits the founder go. The structural
checks and the unit tests below apply now; the T009 preparation is a checklist, not an authorization.

```sh
python3 -m scripts.validate_spec_kit
python3 -m scripts.validate_change --base develop --profile quick
```

Expected: both pass in a clone without unreachable objects. In a shared-object
worktree the first fails with `public repository contains unreachable objects`;
use a fresh clone as described in `docs/development/SPEC_KIT.md`.

Unit level (deterministic; nothing native runs):

```sh
.venv-speckit/bin/python -m unittest tests.test_harness_manifest tests.test_harness_quota \
  tests.test_harness_transport_claude tests.test_harness_containment_macos \
  tests.test_harness_qualification_probes -v
```

Expected: all deterministic refusal tests pass; the opt-in live controls
(`BRAID_T007_LIVE_CONTROLS=1`, never set in CI) are skipped.

Operator preparation for T009 (a checklist, not an authorization; it needs the founder go):

- **Install location.** The supervisor runs as the dedicated account, so that account
  must be able to read the repository code, the pinned interpreter and the pinned
  `claude`. The code location cannot be unreadable to it. Install them where the account
  can read but not write (root-owned, outside any operator-private directory), and give
  the account no read access to the operator's home. Dedicated-user-owned ancestors pass
  the executable check but leave a hash-to-exec window (a root-owned install is stronger).
- **`interpreter_root`.** It is readable and map-executable inside the sandbox, so use a
  minimal prefix that holds only the interpreter and its standard library, never a
  repository or a home directory.
- **Account hygiene the code cannot see.** The account check refuses admin/wheel, the
  console user and a loose home. It does not see sudoers rules by name, ACL grants or
  groups such as `_developer`; the operator verifies those.
- **`config_dir`.** Use a dedicated, empty or small directory, never a home directory or a shared
  cache, and check its entry count and size before every attempt. The disk bound counts what is
  already in it (no baseline), so a large or pre-used `config_dir` makes every run refuse with
  `disk-limit-exceeded`, including the pre-session subset. Investigate that refusal as an
  environment problem before the next attempt; it is not a probe finding. The before/after
  listing hashes up to 500 files with no per-file size cap, so a very large file slows it (MDRV-03).
- **Session.** Run the supervisor inside the dedicated user's own login session, not
  through `sudo -u` from the operator's session, and expect failed probe controls to be
  recorded as findings.
- **Entry point.** Use `make_qualification_runner`: `real_home` is the account's home
  (a runner without one is refused), the credential scan reads `config_dir`, and each
  probe session records a before/after listing of `config_dir` (names and digests).
  Do not pass `runner_options` that replace the executors or weaken the pre-session check, and
  do not use `launch_profile=False` in `make_f4_probe_runner`. Run it only as the dedicated
  account: the arena plants decoys in the home it resolves.
- **Bundle.** Review it for local identifiers before committing it.

Qualification attempt (T009, only after founder decisions and ADR acceptance):
run the probe runner for the decided configuration, inspect
`evidence/qualification/<attempt>/summary.json`, and hand the bundle to the
issuer. Expected: either every effect `enforced` and HOST-01 complete, or a
retained not-qualified bundle. Neither outcome is a failure of the procedure.
