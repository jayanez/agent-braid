# SPEC-065 T011: hand-off packet for SPEC-048/T008 (Claude profile only)

Date: 2026-11-06. Base: `origin/develop` `e332ff18` (T010 issuance, #1136). Docs only: nothing native ran for this
packet, no account changed, and no byte under `specs/048-*/` or `specs/049-*/` changed (procedure_011, section 9).

**What this packet is.** The inputs SPEC-065 supplies to SPEC-048/T008 for the **Claude profile only**. It does not
complete T008, does not admit any SPEC-049/T004 pilot, does not change any SPEC-048 or SPEC-049 checkbox, and says
nothing about Codex (REQ-011). `executionAuthorization` stays `false` everywhere: the issued records make the native
Claude profile *verifiable* by the runtime; they authorize nothing.

Every hash below was recomputed from the files at the base commit (`shasum -a 256`, or the canonical-JSON rule the
code uses, as stated per line).

## 1. Issued records

| Item | Value |
| --- | --- |
| Issuance record | `specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-06.json`, file sha256 `26030d57a021d28ce3b836582ba6196c6636f7401d386a71f7d5a2b9791723ac` (equals `issuanceRecordSha256` in `evidence/t010.json`) |
| Issuer | the founder (NC-9: founder only), 2026-11-06, answers recorded verbatim in `review` |
| Disposition | `issued`; effects credential, filesystem, network, process all `enforced`; `host01` `completed` |
| Containment record | `records.containment`: format `braid-harness-containment-qualification/v0.1`, backend `macos-dedicated-user-sandbox-exec`, kind `native` |
| Containment trusted hash | `b7641c8a48b9c4a2ef6213fa42fa429ae56b279df86c5da33db07e67ff83f834` |
| Claude host record | `records.host`: format `braid-harness-host-qualification/v0.1`, host `claude` |
| Host trusted hash | `8c1a38fe054a09a44a29b53f9aad757500991e1d74aaa655ec4584bcd886178d` |
| Both records | `environmentSha256` `e91007d8626998d49ccb574bc241752bccc5134616598dd76b8f63630f9d818a`, `evidenceSha256` `45eee4d81bda711f6a1a73ae6a54e373e693208967b29bce352d7f428ef5d1ce`, `expiresAt` `1796580464` |
| `issuedAt` / `expiresAt` | `1793988464` = 2026-11-06T18:07:44Z / `1796580464` = 2026-12-06T18:07:44Z (exactly 30 days) |
| `executionAuthorization` | `false` |

The two trusted hashes are of the **canonical** record (`agent_braid/system_one.py` `canonical`: sorted keys,
`(",", ":")` separators, UTF-8, no NaN). Recomputed here from `records.containment` and `records.host`: both match
`trustedHashes`. A consumer must pass the canonical bytes, not the pretty-printed JSON of the issuance file, to
`verify_qualification` / `verify_host_qualification`.

**Verification** (`evidence/t010.json`, sha256 `e18edf60e1043c0f6f3f976f23bd4990f4954f4ef7ca3a5d3319c836ae15e224`):
`verify_qualification` and `verify_host_qualification` accept both records; `evidenceSha256` and `environmentSha256`
equal the bundle's; the bundle pass rule holds; the runner wrote no record; `expiresAt` is 30 days. Negative
controls refuse: edited containment record and edited host record (`qualification-drift`), wrong environment hash
(`qualification-drift`), runner-produced record with an untrusted hash (`qualification-drift`), other host
(`host-mismatch`), partial effects (`invalid-qualification`). Run-time `environment-drift` and
`qualification-expired` are covered by the backend unit tests (213 tests OK). Nothing native ran for T010.

**Bundle** `specs/065-native-claude-containment/evidence/qualification/t009-20261106a/` (attempt 5, commit
`320b00c4`, `startedAt` `1793983494` = 2026-11-06T16:44:54Z):

- `bundleSha256` `45eee4d81bda711f6a1a73ae6a54e373e693208967b29bce352d7f428ef5d1ce`, recomputed with the rule of
  `verify_bundle` (`agent_braid/harness_qualification_probes.py`: sha256 of the sorted `name:sha256` lines of
  `catalog.json`, `environment.json`, `quota.json`, `results.jsonl`); `summary.json` `files` matches.
- `shasum -a 256 -c SHA256SUMS`: all seven entries OK (`catalog.json` `78c39353…e868245`, `environment.json`
  `20ebde15…dd08a03`, `quota.json` `4080cccd…c5a148`, `results.jsonl` `01f2cb29…e77`, `summary.json` `86e37353…64d1`,
  `operator/t009-run-t009-20261106a.txt` `50c2b1d6…ec07`, `operator/t009-self-check.json` `b4f9bf54…c79`).
- `summary.json`: `passRuleSatisfied` true, `hostFunctional` true, `notEnforced`, `inconclusive`, `missingProbes`
  empty, `qualificationRecordWritten` false, `executionAuthorization` false; 32 of 32 probes passed; three sessions
  (CRED-05, NET-05-CLI, HOST-01), quota delta 0; CRED-05 `apiKeySource` `none`, inside `SUBSCRIPTION_KEY_SOURCES`
  `{none, oauth}` (`agent_braid/harness_host_claude.py`).
- Result: `evidence/t009-attempt5-result.md` (sha256 `bd1607dc709208347304e98de6115e126b15dbbd451afb2404c67301eea480a1`).

**Attempt history** (all kept; none is a qualification):

| Attempt | Result document (sha256) | Bundle `bundleSha256` | Outcome |
| --- | --- | --- | --- |
| 1, `t009-20261104` (2026-11-03) | `evidence/t009-attempt1-diagnosis.md` (`d95f5eb9…8f22`) | none written (`secret-in-artifact`) | not qualified; one session counted, refused by the pre-session check before any `claude` launch |
| 2, `t009-20261104b` | `evidence/t009-attempt2-result.md` (`55c0b10a…ba6b`) | `4a512d3139c81c3316515ce52cc3537f41021dd14469d11f4aaa4f82cedaa159` | not qualified; sessions exit before `init` (Keychain unreachable, led to NC-5 token file) |
| 3, `t009-20261104c` | `evidence/t009-attempt3-result.md` (`9e6ae84c…a060`) | `ccd227a9119b74439c59ae4d19946ee3e441270e4e3378fff3e858b3236397da` | not qualified; `hostFunctional` false |
| 4, `t009-20261105a` | `evidence/t009-attempt4-result.md` (`21c9d0ab…7a41c2`) | `890b5eae1430f576607904227db85e7b2f5d9fed47255bca41a8d5b6a55a455a` | not qualified; 31 of 32, process `not-enforced` by PROC-03 only |
| 5, `t009-20261106a` | `evidence/t009-attempt5-result.md` (`bd1607dc…80a1`) | `45eee4d8…d1ce` | pass rule satisfied; issued by T010 |

## 2. Environment the records are bound to

From `evidence/qualification/t009-20261106a/environment.json` (the published allow-list document):

| Field | Value |
| --- | --- |
| `backend` | `macos-dedicated-user-sandbox-exec` |
| `osProduct` / `osBuild` | `27.2` / `26B123` |
| `arch` | `arm64` |
| `claudeVersion` / `claudeSha256` | `2.1.292` / `97a01e5bc74a199e67189435d0331ea3a24eac2e07db4b76d9148c5b0386138f` |
| `sandboxExecSha256` | `10cf4a46a575e4747d2419cf343800db0d11ae6e6e9b8415998d3d8f336b2a92` |
| `profileSha256` | `08e3ff93c76b17ac89aa9806bf31a705e9807e8af7b01bdd5c0fb88aeaf65294` |
| `probeCatalogSha256` | `5ecbd7eba61f4bc87322cce79153f5b5812d186aebb9eff43d3098e30134e929` (`CATALOG_SHA256`, a digest of the catalog document; not the `catalog.json` file hash) |
| `environmentSha256` | `e91007d8626998d49ccb574bc241752bccc5134616598dd76b8f63630f9d818a` |

`environmentSha256` is not recomputable offline from `environment.json` alone: `environment_sha256` in
`agent_braid/harness_containment_macos.py` hashes the canonical form of a larger document (OS facts, mechanism and
account facts, the three entry profiles, `claude` path/hash/version, helpers, pinned interpreter, supervisor hash,
credential method `dedicated-user-token-file`, token file and variable names, config dir, run root, network endpoints
and proxy port, component hashes of the backend, `harness_lab.py`, `harness_host_claude.py`,
`harness_transport_claude.py` and `harness_quota.py`, `LIMITS`, and the catalog hash). It is recomputed in the lab
account before every native session (NC-11); a mismatch refuses `environment-drift`.

**What the hash omits (MDRV-04).** `harness_manifest.py`, `harness_context.py`, `harness_observation.py` and
`system_one.py` are imported by hashed modules but are not hashed (`evidence/probe-catalog-delta-recheck.md`).
Founder answer at issuance: "Acepto con revisión PR" (`T010-MDRV-04`): accepted for this issuance; any change to those
four files during validity is reviewed by the founder before native use. Checked for this packet:
`git diff --stat 320b00c4 origin/develop -- agent_braid/ scripts/` is empty, so no runtime code (hashed or not)
changed between the qualified commit and the base of this packet.

## 3. Limits, endpoints, credential, budget and pre-session check

**NC-8 limits** (`LIMITS` in `agent_braid/harness_containment_macos.py`, decided 2026-10-31,
`evidence/founder-decisions-20261031.json` sha256 `9aa51097…692e`): wall 1800 s, CPU 1800 s, memory 4 GiB
(4,294,967,296 bytes, physical footprint of the child's tree), file size 64 MiB, 256 open files, 16 descendants,
plus disk 2 GiB and 100,000 files over the candidate directory and per-run `TMPDIR` (RV-19). Memory, disk and wall
are watchdogs polled by the supervisor, not kernel quotas (DRV-07). Executables: the pinned Claude binary plus the
helpers observed by probe; anything else is denied by the exec allow-list (COMPILE_PROBE `/usr/bin/false` must be
denied).

**NC-1 endpoints**: `ALLOWED_ENDPOINTS = ("api.anthropic.com:443",)` plus OAuth refresh hosts observed by probe
(`refresh_endpoints`, empty in the qualified policy: NET-05-CLI saw 3 connections, all to `api.anthropic.com:443`
through the proxy). Enforced by a loopback CONNECT proxy that checks the CONNECT host/SNI; telemetry, error-reporting
and update endpoints are denied; DNS, raw sockets, UDP, IPv6 and local services are denied by the profile.

**NC-5 credential method** (amended 2026-11-04, `evidence/founder-decisions-20261104d.json` sha256
`36d71bfb…d739`): `dedicated-user-token-file`. The `braidlab` account's own long-lived token from
`claude setup-token`, stored only in `CLAUDE_CONFIG_DIR/oauth-token` (mode `0600`, owned by the account, one link,
at most 4096 bytes, one ASCII token, no symlink); the supervisor sets it as `CLAUDE_CODE_OAUTH_TOKEN` in the child
environment of the `launch` entry only; no Keychain access (`mach-lookup` fully denied); nothing of the founder is
copied.

**NC-10 live-probe budget**: at most 3 minimal `claude -p` sessions per qualification attempt (Haiku, low effort),
each at most 2 % of the 5-hour window (`PROBE_MAX_SESSIONS = 3`, `PROBE_MAX_FIVE_HOUR = 2` in
`agent_braid/harness_quota.py`), separate from the D2 cohort caps. The session counter survives a crash in the
attempt's output directory. NC-6: the operator types the usage readings (claude.ai Usage or phone), at most 5 minutes
fresh; a session starts only below 90 % of the 5-hour window.

**NC-11 pre-session check** (before **every** native session, including every SPEC-048/T008 unit): recompute the
environment hash, verify both records against the trusted hashes, and run the contained subset `F4_PROBES`: FS-01,
NET-01, CRED-01, PROC-01 denied and NET-06 allowed. Any refusal stops the session.

## 4. Residual risks accepted for issuance

Accepted by the founder for the 30-day validity (`T010-RESIDUALS`, "Acepto para emisión", citing
`evidence/founder-decisions-20261104c.json` sha256 `2fd30e1f…b0d` and `evidence/founder-decisions-20261106.json`
sha256 `aafb3f5d…71d0`):

- **PROC-ESC-1**: a descendant that calls `setsid` and is reparented before the backend sees it may read as
  unrelated. Narrowed by PROC-04: the backend attributes it through the inherited run tag.
- **PROC-03 (compressed memory)**, accepted 2026-11-06: the limit is the physical footprint; compressed pages count at
  their compressed size, so well-compressing memory can exceed 4 GiB; a burst that exceeds the limit and exits between
  two samples (10 to 50 ms) is not stopped; no kernel limit backs the watchdog.
- **NET-02**: `tcp-ipv6-literal` is excluded when the machine has no IPv6 route; IPv6 egress is then untested.
- **PROC-04**: a descendant that also scrubs its environment before the backend first sees it is not attempted.
- **PROC-07**: `ptrace-sibling` is excluded when the kernel refuses it even uncontained.
- **MDRV-04**: accepted with PR review (section 2).

Not-applicable exclusions in the bundle, each by a tested catalog rule: CRED-02 `mach-secd`, FS-07 `mach-spotlight`,
NET-02 `tcp-ipv6-literal`, PROC-07 `ptrace-sibling`.

Engineering review residuals carried from the catalog reviews (low or info; not separately named in the issuance
record): MDRV-01 (credential-literal skip filter), MDRV-02 (`real_home` not tied to the policy account), MDRV-03 (no
`config_dir` pre-flight; follow the quickstart line), DRV-04, 07, 08, 09, 11, 13, 15
(`evidence/probe-catalog-delta-review.md`, `evidence/probe-catalog-delta-recheck.md`). The kernel-limit question of
attempt 3 stays open.

Scientific limit: the records describe one machine, one OS build, one CLI version and one catalog version until
`expiresAt`. They are not a general isolation proof and say nothing about Codex.

## 5. Expiry, re-qualification triggers and cost

- **Expiry**: 2026-12-06T18:07:44Z (`expiresAt` `1796580464`). At or after it the backend refuses
  `qualification-expired`, and `harness_hosts._verify_containment` refuses `containment-expired` for any unit whose
  deadline is not strictly before `expiresAt`: the last T008 unit must **end** before that instant.
- **Early re-qualification (NC-9)** on any change of: macOS build (27.2 `26B123`), Claude Code version or hash
  (2.1.292, `97a01e5b…138f`), profile bytes, probe catalog, proxy, or credential method. Most of these move the
  environment hash and refuse `environment-drift` at the NC-11 check; MDRV-04 files do not, so they need the founder's
  PR review instead.
- **Revocation**: a reviewed change that withdraws the trusted hashes (issuance record `notes`).
- **What re-qualification costs.** One self-check plus one attempt, then a new T010 issuance by the founder:
  1. if code or pins change (for example a new Claude version: `CLAUDE_VERSION = "2.1.292"` is pinned in
     `harness_containment_macos.py`, NC-4), a code PR and a re-check of the touched lines first (T009 precondition);
  2. `scripts/har_t009_setup.py --commit <C>` in the founder's session (sudo, steps 0 to 8: pinned copies under
     `/usr/local/libexec/braid/`, handoff directory `/Users/Shared/braid-t009/`); with the lab already set up a re-run
     stops at the step-7 empty `config_dir` check, so changed pins or a new code copy are installed with the manual
     step-5 commands and a hand-written summary (quickstart, "Operator setup for T009");
  3. `scripts/har_t009_lab.py` in the `braidlab` login session (login skippable, token kept unless `--renew-token`,
     driver `--dry-run`, `--self-check --founder-go` with its `auth` and no-model `startup` stages: **no session
     spent**), with `scripts/har_t009_verify.py` run by the orchestrator between stages;
  4. the real attempt (`scripts/har_t009_attempt.py --founder-go` through the lab script): the full catalog, **at most
     3 Haiku sessions**, each at most 2 % of the 5-hour window (NC-10); attempt 5 used a quota delta of 0 at 1-point
     granularity;
  5. the bundle copied into `evidence/qualification/<attempt>/`, a result document, and a founder T010 issuance with
     new trusted hashes (a reviewed PR).

## 6. SPEC-048/T008 acceptance items still open

Sources: `specs/048-harness-variant-laboratory/tasks.md` T008 (file sha256 `061054d0…726a`), its evidence
`specs/048-harness-variant-laboratory/evidence/t008.json` (sha256 `d5df3a90…7564`, disposition **Open**),
`agent_braid/harness_hosts.py` (sha256 `c6248002…6104`, equal to the hash bound in 048 `t008.json` inputs).

| T008 acceptance item | What this packet supplies | What 048 T008 must still decide or record itself |
| --- | --- | --- |
| Reuse an existing trusted admission seam only where its contract matches | `harness_hosts.HostQualificationRun.admit_unit(containment=..., containment_sha256=...)` already calls `harness_host_claude.verify_host_qualification`; the issued host record (canonical bytes) and its trusted hash `8c1a38fe…178d` are that input; environment `e91007d8…818a` | Check the seam still matches the issued record format, bind the canonical host-record bytes and hash in its own evidence, and decide how the trusted hashes reach the trusted caller (no record authored by T008 itself) |
| Same environment at every unit | The qualified policy inputs: `scripts/har_t009_attempt.py` `_build_policy` (account, run root, config dir, `claude` path and hash, interpreter path, hash and root, `sandbox-exec` hash, proxy port; `refresh_endpoints` empty) all enter `environmentSha256` | Build the native unit's `ContainmentPolicy` from exactly those inputs in the `braidlab` session; any difference refuses `environment-drift` at the NC-11 check |
| `nativeFeasibility` (048 `t008.json`: no native transport, no non-offline manifest profile, no enforced-effect backend, no issued qualification) | SPEC-065 T003 native manifest profile, T005 macOS backend, T006 `ClaudeTransport`, T010 issued records | Re-assess feasibility against the current code and record it; no module wires `HostQualificationRun` to the native transport and backend today (only `harness_hosts.py` names it), so the native unit path is T008's own work |
| Independent Claude profile decision | Nothing: the founder record `founder-review-20261031.json` (sha256 `38bedbba…ddc`) says only `qualification-authorized` for Claude | A new founder profile decision record for Claude (qualified, not qualified, or still pending), citing these records, with its own hash bound in `harness_hosts` parsing |
| Actual controls | SPEC-065 containment evidence (effects enforced, F4 subset, T010 negative controls) | The controls T008 observes in its own native units under `HostQualificationRun` (pre-unit NC-11 check passing, settlement, stop latch) |
| Route/quota observations | NC-6 typed-reading convention; attempt-5 quota readings (5-hour 1 %, weekly 75 %, delta 0) are probe-budget readings, not T008 units | Before/after readings per unit under the D2 caps (`d2-caps-founder-decision-20261031.json` sha256 `b1851e1c…2d88`: 30 min per unit, session at most 10 % of 5-hour, cohort at most 15 % of weekly, at most 16 units, weekly stop above 80 %, EUR 0, subscription route only) |
| Compatibility and limitations | Section 2 environment, section 4 residuals, scientific limit | Record them as T008 profile limits, including the expiry and the one-machine scope |
| Unsupported profiles stay refused; partial qualification never implies both hosts | Claude only | Codex stays `not-qualified: not installed` (founder record) and must be reviewed again before HAR.1 closes |
| Evidence | This packet | `specs/048-harness-variant-laboratory/evidence/t008.json` updated by T008 with exact candidate, input hashes, commands, exits and limits |

**SPEC-048 snapshots.** `specs/048-harness-variant-laboratory/assurance.json` has its `authority_snapshot` and
`evidence_snapshot` frozen `historical` at `530a5f395b19f1bb9519b4846186e201cf4a02aa` (since the SPEC-065 T003 PR).
Updating 048 T008 evidence or tasks means 048 decides how to refresh or unfreeze those snapshots in its own change;
this packet does not touch them.

**Order of unblocking.** SPEC-049/T004 is unblocked **only after** SPEC-048/T008 records its own Claude profile
decision, and then still needs its own current source, route and quota approval (049 `tasks.md` T004). Nothing in
SPEC-065 admits a SPEC-049 pilot. `executionAuthorization` stays `false` in every SPEC-065 record and in this packet.

## 7. Lab state the founder keeps while the qualification is used

The NC-11 check recomputes the environment hash in the lab account, so native use needs the qualified lab exactly as
it was (any change is a re-qualification trigger):

- the dedicated account `braidlab` (its own login session, `CLAUDE_CONFIG_DIR` under its home);
- the root-owned pinned copies under `/usr/local/libexec/braid/`: `claude-2.1.292`, the `python312` interpreter prefix,
  the `repo-<short>` code copy;
- the token file `CLAUDE_CONFIG_DIR/oauth-token` (mode `0600`, owned by `braidlab`) and the matching token in the
  Claude account settings;
- the handoff directory `/Users/Shared/braid-t009/` (`to-lab/`, `from-lab/`) and the `/Users/Shared/t009-*` copies
  and helper scripts the founder used for the attempts.

**Teardown is a founder decision**, not part of T011 and not implied by expiry. When the founder decides it, the
quickstart "Teardown" section applies: remove the `/Users/Shared` copies and `braid-t009`, revoke the long-lived token
in the Claude account settings and delete `oauth-token`, log out and revoke the `braidlab` Claude session, delete the
account (`sysadminctl -deleteUser`), remove `/usr/local/libexec/braid`, restore the home mode noted in step 6. After
teardown the issued records can no longer pass NC-11; a later use needs a new setup and a new qualification.

## 8. What the founder decides for 048 T008

1. The Claude profile decision record for SPEC-048/T008 (qualified, not qualified, or pending), once T008 has its own
   native units and observations.
2. Whether the T008 units run within the current validity (before 2026-12-06T18:07:44Z) or after a re-qualification.
3. How SPEC-048 refreshes or unfreezes its `historical` snapshots at `530a5f39` for the T008 change.
4. When to tear down the lab.

## 9. procedure_011

Command, run on branch `har/t011-handoff` with this packet committed:

```text
$ git diff --stat origin/develop -- specs/048-* specs/049-*
(empty output)
```

No SPEC-048/049 byte is changed by this feature's T011 change. The packet claims neither T008 nor T004 completion.
