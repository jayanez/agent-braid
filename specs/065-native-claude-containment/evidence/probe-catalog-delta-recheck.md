# SPEC-065: mini delta re-check of the pre-T009 fixes (#979), before T009

**This re-check is not a qualification.** It issues no record, qualifies no effect, authorizes no native
session, probe or account setup, and changes no code. `executionAuthorization` stays `false`. A GO below
means *engineering readiness* of the code for the T009 live attempt; it does not replace the founder's own
go for T009, and it says nothing about whether the sandbox profile enforces anything (that is decided only
by the T009 observation and the T010 human issuance). Nothing native ran in this re-check.

## Record

| Item | Value |
|---|---|
| Date | 2026-11-02 |
| Task | SPEC-065 mini delta re-check required by `probe-catalog-delta-review.md` ("a delta check restricted to the touched lines should be enough") |
| Reviewed commit | `1429f6e645ed74b8936282329592bc2d0b6caea4` (#979, squash; `origin/develop` head when this re-check started) |
| Scope | `git show 1429f6e6` limited to the touched lines of `agent_braid/harness_containment_macos.py`, `agent_braid/harness_qualification_probes.py`, the comment in `agent_braid/harness_host_claude.py`, `quickstart.md` and ADR 0035; plus `evidence/pre-t009-fixes.json` and `evidence/founder-decisions-20261102c.json` |
| Reviewer | A derived docs-and-closer track session (Claude Sonnet 5.5), the same kind of session as the delta reviewer, in a fresh context. Independent in context, **not** a human review and not a different model family |
| Tests run | `python -m unittest tests.test_harness_containment_macos tests.test_harness_qualification_probes tests.test_harness_transport_claude tests.test_harness_host_claude`: 356 tests, OK, 3 skipped (opt-in live controls). Plus a throwaway check of `credential_values` on synthetic values (residual b) |

SHA-256 of the reviewed files at `1429f6e6` (they match `pre-t009-fixes.json`):

| File | SHA-256 |
|---|---|
| `agent_braid/harness_containment_macos.py` | `a9bc7f890cf91c7a3bdef8344279ec41ffaa334316507dd8161e80cad06bd91a` |
| `agent_braid/harness_qualification_probes.py` | `aaa55342feb916f24911cd8e287edefcca4b269612ff26915a7e5bb1dc389428` |
| `agent_braid/harness_host_claude.py` | `e409512d7b4d20bc5c38a28a2ee1cc31344832718f76ee2f067d25d610d1b9e1` |
| `agent_braid/harness_transport_claude.py` | `e98c4db0e279b0a07a90a94d7c2f9a519e29dbdc0ca23c9b123dc3dc043fa19e` |
| `agent_braid/harness_quota.py` | `7fc5a4b710e1b0627f4535194aff1a922f6d6e1545e92237b64d8a1f253808bb` |
| `specs/065-native-claude-containment/quickstart.md` | `cca2a952c31eba0c4e88bd75620258e48a7da4233be9fc7962051fc444b4e93f` |
| `docs/adr/0035-native-claude-laboratory-containment.md` | `9db60ef1544e5218eb7fa7ba34315f48b33e464b761e07359fc5bfcd9bfaf0c5` |
| `evidence/probe-catalog-delta-review.md` | `fc54257d65215b944d430b886e6b07463f0bc2bcef1a583d32b7f2542c5e905a` |
| `evidence/pre-t009-fixes.json` | `6dc9fa49e8e7c2e953db04e13f55ecd195572eb01bc74c5e206e1b0a67d90337` |
| `evidence/founder-decisions-20261102c.json` | `8d0b25f77575c7a29582ad91c614a4772f5e483a7704ca99200526568c8b4ed6` |

`P:` = `agent_braid/harness_qualification_probes.py`, `B:` = `agent_braid/harness_containment_macos.py`,
`T:` = `tests/test_harness_qualification_probes.py`, `TB:` = `tests/test_harness_containment_macos.py`.

## Verdicts per item

| Item | Verdict | Evidence | Broader than the founder decisions? |
|---|---|---|---|
| DRV-01 (blocking) session egress includes pre-session tunnels | **fixed** | `P:1254` `egress = getattr(run, "egress", None)` replaces the two counter taps; it is kept only if `egress_counters_ok` (string names, non-negative non-bool ints), else `None`. The backend computes `run.egress` as a delta whose start is read inside `_supervise`, after the pre-session check (`B:1250`, `B:1330`, `B:1346`). `counter_delta`, `_read_counters` and the `egress_counters` parameter are removed. Empty delta gives `inconclusive` through `_egress_verdict` (`P:1067` unchanged: `not targets`). The route-unverified kill path returns a bare `HostRun` with no `egress` (`harness_transport_claude.py:_finish`), so it reads `None`, `inconclusive`: fail closed. Tests: `T:998` (pre-session tunnels are not CLI traffic), `T:1008` (malformed delta), `T:2200` (factory path uses the run delta, not the backend total) | No. Reviewer's own proposed fix, implemented as proposed |
| DRV-02 (blocking) default entry point has no real-path evidence | **fixed** | `P:2589-2590` `home = home_directory()` when `real_home` is None, and `real-home-unavailable` unless `type(home) is str and os.path.isabs(home)` (an empty string is refused). Defence in depth in the runner: `P:2176-2178` demotes a denied `real-launch-agent` or `hardlink-own-tree` (`REAL_HOME_ATTEMPTS`, `P:94`) to `inconclusive` for any non-control row without `real_home`. The row records `independent.realHome` (`P:2217`), false for the control. Tests: `T:2212`, `T:2361`, `T:2373` | No |
| DRV-05 (blocking) transport and quota outside the environment hash | **fixed** | `B:365` `_COMPONENT_FILES`, `B:374` reads both by path next to the backend (no import; the transport imports the backend). Test `TB:1086`. The recorded reference hash moved (`pre-t009-fixes.json`), so every earlier input hash is stale, as the record states | No (the delta review itself noted it is a hardening beyond the decisions) |
| DRV-12 (blocking, documentation) runbook, ADR, stale comment | **fixed** | Quickstart "Operator preparation for T009" now says: the account must read the code, interpreter and `claude`; install root-owned and not writable by it; no read access to the operator's home; `interpreter_root` a minimal prefix; the account check cannot see sudoers-by-name, ACLs or `_developer`; run inside the account's own login session, not `sudo -u`; run only as the dedicated account; review the bundle for local identifiers. ADR 0035 now carries the RV-17 route and its bounds, the RV-19 values (2 GiB = 2 x 1024^3, 100,000 entries, polled-threshold overshoot, xattr payload uncounted), the shared-`config_dir` interim measure, the install requirement, the hash-to-exec window, the DRV-10 reading with a link to the founder record, and that probe controls have never run. `harness_host_claude.py` comment no longer says "until T008 observes". Statements checked against the code (`B:1031` `os.getuid() == uid`; `B:365-374`; `B:1251`) and are accurate | No. Documentation only; the hash of `harness_host_claude.py` moved by the comment edit (recorded) |
| DRV-03 (recommended) credential scan unwired | **fixed**, with residual (b) | `P:2601` `read_credentials or (lambda: credential_values(config_dir))`; the docstring is corrected. Tests `T:2225`, `T:2352` | Mild. The skip filter is new design, not a founder decision; see residual (b) and MDRV-01 |
| DRV-14 (recommended) real `apiKeySource` thrown away | **fixed** | `P:1035` `_key_source_label`: the label survives when it matches `[A-Za-z0-9._-]{1,32}` and is not `_looks_secret`, else `other`; `None` when none was seen. Used at `P:2338` in `independent` only; `classify_session` still decides on `SUBSCRIPTION_KEY_SOURCES` (`P:1072-1090`), so no verdict changed. 32 is stricter than the 40 suggested. Test `T:2265` | No |
| DRV-16 (recommended) interim `config_dir` before/after measure | **fixed** | `P:1144` `config_dir_listing` (names and SHA-256 digests, at most 500 entries, symlinks recorded by target digest and not followed, `os.walk(followlinks=False)`), `P:1181` `_file_digest` (lstat regular-file check, `O_NOFOLLOW|O_NONBLOCK`, fstat re-check, so a FIFO or device is `special` and never blocks; `unreadable` on error), `P:1198` `config_dir_changes` (counts, added/removed/modified names, digests of added and modified; a cut listing gives counts only; `None` unless both listings were read). Components with unusual characters or over 38 characters become `#<digest>` so they cannot trip the secret scan. The driver reads both listings (`P:1236-1257`), the row carries `independent.configDir` (`P:2340`), and the factory wires it by default (`P:2594`). Contents are never recorded. Tests `T:1013`, `T:1022`, `T:2233`, `T:2282`, `T:2297-2338` | Mild: implemented as the reviewer suggested, not a founder decision. No contents leave the directory |
| DRV-06 (founder decision: include `config_dir` in the bound) | **fixed, as decided** | `B:1251` `_DiskGuard((candidate, tmpdir, policy.config_dir))`; `LIMITS` unchanged (2 GiB, 100,000, `B:89-91`); `_DiskGuard` is generic over its roots (`B:886-925`), each inode once, symlinks not followed, a missing root is skipped, an unlistable one counts as over. Docstrings and comments updated. Tests `TB:1026`, `TB:1034`, `TB:1043`, `TB:1528`, `TB:1540` (opt-in live 100,000-entry control ran once locally per the record, not re-run here) | No. It is what `founder-decisions-20261102c.json` says, including "no baseline is subtracted" and "polled threshold" |
| DRV-10 (founder acknowledgement) | **accepted, recorded** | `founder-decisions-20261102c.json` and ADR 0035 residual text; quickstart forbids `launch_profile=False` and `runner_options` that weaken the pre-session check. The code path of `make_f4_probe_runner` is untouched by #979 | n/a |

Nothing in the diff touches the SBPL profile text: the three profile hashes are unchanged
(`pre-t009-fixes.json`), so the accepted `launch-probe` profile and the policy surface are the same as in
the delta review.

## The four reported residuals

**(a) The `config_dir` disk measure has no baseline.** It is fail closed and acceptable; it does not block
T009 in practice. The mechanism: from the first poll, `_DiskGuard` counts everything already in
`config_dir` against the same 2 GiB / 100,000 bound (`B:1251`), so a `config_dir` that has grown makes the
next run refuse with `disk-limit-exceeded` (`B:1336`) instead of passing. Why it does not block: T009 is
three short single-turn sessions (`PROBE_PROMPT`, `max_turns=1`) plus pre-session probes; a Claude
configuration directory holds credentials, settings, a session transcript and small caches, orders of
magnitude below 100,000 entries or 2 GiB. A hostile child that fills `config_dir` is stopped by the very
bound (the intended effect), and the operator then clears the directory. Two cautions, neither a code
defect: (1) a `disk-limit-exceeded` refusal caused by an old or oversized `config_dir` reads like a probe
finding but is an environment problem, so the operator must know the difference (MDRV-03); (2) if the
operator points `config_dir` at a directory that is large for unrelated reasons (a home directory, a
shared cache), every run, including the pre-session subset, refuses. Both are covered by one sentence in
the T009 operator checklist, not by code.

**(b) `credential_values` now skips paths, URLs, hosts, e-mails and sentences.** A real secret *can* be
skipped from the literal list, but not one of the credential formats the account actually holds, and the
shape scan still covers those. I ran the filter on synthetic values: scanned: `sk-ant-oat01-...`
(OAuth-style), JWT-like `eyJ...`, hex, UUID, plain alphanumeric; skipped: standard base64 containing `/`
or `+...==` with a slash, a value containing `:`, `~` or `@`, an all-lowercase letters/dot/hyphen string
(`_PLAIN_NAME`), anything with whitespace. Of the skipped ones none was caught by the independent shape
scan either (`_SECRET_SHAPES` and `_LONG_RUN` need `sk-ant-`, `eyJ`, `-----BEGIN`, `gh?_`, `AKIA`, or a
40-character run of `[A-Za-z0-9+_=-]`), so for those the literal scan is the only defence. The Claude
credential files carry `sk-ant-` shaped tokens and JWT-like values, both still scanned literally and by
shape, so the practical gap is a future or unusual field, and it is a depth defence on a bundle that holds
no session content in any case (helpers emit outcome and errno only; session stdout is never persisted).
Residual, recorded as MDRV-01 with a narrower-skip option.

**(c) Running as a non-dedicated account plants decoys in that home.** The arena resolves
`home_directory()` of whoever runs the factory and, for non-control rows, creates `Library`,
`Library/LaunchAgents` and a `.braid-own-<nonce>` file there (`P:1432-1437`), removed by `arena.close()`.
Two things limit the damage: the backend itself refuses every contained run unless `os.getuid()` is the
dedicated account (`B:1031`, `B:1381`), so the contained attempt that could have written a plist into that
`LaunchAgents` never runs off-account; and the uncontained control uses the arena home, not the real one
(`P:2147`). What remains is leftover empty directories or a stray file if the process is killed between
planting and `close()`, in an operator home. The quickstart now says "run it only as the dedicated
account". Low, residual (MDRV-02): the factory could compare `home` with the policy account's passwd home
and refuse otherwise, and `realHome: true` in a row currently means "an absolute home was supplied", not
"the dedicated account's home". Not needed for T009 provided the runbook is followed, because the T010
issuer can read the environment document and the account facts.

**(d) `MacOSContainment.egress_counters` left without a caller.** Harmless. `agent_braid/` no longer references it
(`grep` finds the definition at `B:979` only). It is a read-only copy of integer counters; leaving it
adds no capability and removing it would move the backend hash again for no security gain. Keep, or remove
in the same change as any later backend edit. Not a finding.

## New findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| MDRV-01 | Low | `credential_values` skip filter (`P:2436`, `P:2440-2464`) drops any credential literal that is not one token of `[A-Za-z0-9_+=.-]` or that is all lowercase letters, dots and hyphens. Standard base64 with `/`, and values with `:`, `~`, `@`, are skipped and not covered by `_SECRET_SHAPES`. Option if wanted: skip only values that start with `/`, contain `://`, contain whitespace, or look like a host or e-mail, and keep everything else | residual (depth defence; the account's real formats are covered) |
| MDRV-02 | Low | The factory does not tie `real_home` to the policy account: `realHome: true` means a valid absolute path was given. Off-account runs are stopped by `B:1031`, so no false pass, only leftover decoys on a crash | residual (follow the runbook; optional hardening: compare with `pwd.getpwnam(policy.account).pw_dir`) |
| MDRV-03 | Low | No operator pre-flight for `config_dir`: because the bound has no baseline, a pre-existing large `config_dir`, or one that is a whole home directory, makes every run refuse with `disk-limit-exceeded`, which is an environment problem, not a probe finding. Also `config_dir_listing` hashes up to 500 files with no per-file size cap, so a very large file in `config_dir` slows the before/after listing (outside the session wall clock) | residual; add one line to the T009 operator checklist at preparation time: `config_dir` is a dedicated, empty or small directory, never a home directory, and a `disk-limit-exceeded` refusal is investigated before the next attempt |
| MDRV-04 | Info | The environment hash still omits `harness_manifest.py`, `harness_context.py`, `harness_observation.py` and `system_one.py`, which the hashed modules import. The only policy-like value among them (`NATIVE_BUILD`) is cross-checked against the backend's pinned `CLAUDE_VERSION` in the transport (`harness_transport_claude.py:170`), so editing it alone cannot silently change the build; the rest parse or shape data rather than enforce | residual, for the T010 issuer to know; no change needed |

No new finding is fix-before-T009, and none needs a founder decision. The change introduced nothing
broader than the founder decisions in the enforcement path: the only additions beyond the decisions are the
reviewer-recommended items (DRV-03 filter, DRV-14 label, DRV-16 listing), all of which add evidence and
refusals and none of which can turn a refusal into a pass. The one place where #979 loosens a previous
behavior is the credential-literal skip filter (MDRV-01), which narrows the literal scan to avoid refusing
every bundle.

## Checks

| Question | Answer |
|---|---|
| All four blocking items closed? | Yes: DRV-01, DRV-02, DRV-05 fixed in code with tests; DRV-12 fixed in documentation, and the statements match the code |
| Recommended items closed? | Yes: DRV-03, DRV-14, DRV-16 fixed; DRV-03 with a recorded residual |
| Founder decisions implemented as decided? | DRV-06 yes, exactly (no baseline, polled threshold); DRV-10 recorded and consistent with the code |
| Fail-closed defaults in `make_qualification_runner` | Now: sessions, quota, catalog binding, LAN, allowed IP, mach names, `real_home` (refused if unresolved), credential scan and `config_dir` listing (wired by default) |
| Any new way to a pass without an observation | None found. The `egress` of a session can only be the run's own delta or `None`; real-path attempts cannot pass without a real home; the new row fields are evidence only |
| Any secret leakage path added | The `config_dir` listing records names (hashed when unusual or long) and SHA-256 digests only; the rows are inside the existing secret scan |
| Tests | 356 pass, 3 opt-in live controls skipped |
| Native execution | None |

## Recommendation for T009

**GO for T009 engineering readiness.** The code, tests, runbook and ADR at `1429f6e6` close every blocking
item of the delta review and introduce no blocker. This is not a qualification and not an authorization:
T009 still needs its own founder go, the dedicated account, the root-owned install, the pinned `claude`
binary and `interpreter_root`, the operator-supplied inputs (`read_quota`, the allowed IP resolution if
any) and a `config_dir` that is a dedicated small directory. Any edit to the backend, the probes module,
the transport or the quota module after this point moves the environment hash and the catalog hash again
and needs a new re-check of the touched lines.

Carry into the T009 bundle summary and the T010 decision: the residuals DRV-04, 07, 08, 09, 11, 13, 15 of
the delta review, plus MDRV-01 to MDRV-04 above. Plan for `inconclusive` rows from failed probe controls
(DRV-09) and `not-enforced` on `iokit-service` or `sysctl-hw` (DRV-08); neither would be a reason to widen
the profile.
