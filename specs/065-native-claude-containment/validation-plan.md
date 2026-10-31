# SPEC-065: Validation plan

Procedures are planned, not run. Unit procedures use fakes and doubles; they
prove refusal logic, not containment. Containment is shown only by the probe
bundle (procedure_009/010) and accepted only by the human records.

Commands use the isolated environment: `.venv-speckit/bin/python -m unittest …`.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_harness_manifest.py` | offline goldens identical (bytes, digest, view, refusals); native valid manifest parses | unknown field, limit above cap, route ≠ `subscription`, host ≠ `claude`, `executionAuthorization: true`, offline manifest with native keys, native manifest with offline host; offline multi-fault goldens keep their first refusal reason |
| procedure_002 | SC-002 | `tests/test_harness_transport_claude.py` | fake contained launcher run returns `HostRun`; observation source `host`; authorization false | no/expired/drifted/Codex qualification, `ANTHROPIC_API_KEY` present, non-subscription `apiKeySource` (group killed at `init`, no `result` accepted), host qualification without qualified backend, executable hash mismatch, `PATH` shadowing, any retry attempt |
| procedure_003 | SC-003 | `tests/test_harness_quota.py` | fresh reading within caps proceeds; post-reading and delta recorded | stale, missing, unparseable, weekly > 80 %, extra usage on, per-session check (NC-6) failing, cohort > 15 % weekly, units > 16, cohort state absent |
| procedure_004 | SC-004 | `tests/test_harness_containment_macos.py` | qualified backend → `native`; result carries the label; run evidence carries qualification hash and F4 check results | mechanism absent, binary hash changed, profile compile error, self-check failure, OS build outside window, fallback to simulated |
| procedure_005 | SC-005 | probe catalog FS-01…FS-07 | contained: all denied; independent scan shows no outside change | uncontained positive controls succeed |
| procedure_006 | SC-006 | probe catalog NET-01…NET-08 | contained: escapes denied; allowed endpoint reachable | uncontained positive controls succeed |
| procedure_007 | SC-007 | probe catalog CRED-01…CRED-07 | contained: all reads denied; `apiKeySource` in subscription set; secret scan clean | uncontained positive controls read planted dummy secrets in a disposable home |
| procedure_008 | SC-008 | probe catalog PROC-01…PROC-08 | contained: denied or terminated; no survivors | uncontained positive controls succeed |
| procedure_009 | SC-009 | `tests/test_harness_qualification_probes.py` + issuance record | human records verify with trusted hashes | runner-written record, failing/missing probe, edited record, other environment hash, expired record |
| procedure_010 | SC-010 | full catalog, both modes | every escape observed uncontained, denied contained | a probe with failed positive control is `inconclusive` and blocks |
| procedure_011 | SC-011 | `git diff` of SPEC-048/049 paths + hand-off packet | no SPEC-048/049 bytes changed by this feature; packet lists records and open T008 items | packet claiming T008 or T004 completion |

Positive controls use a disposable directory with dummy secrets created for the
probe, never the operator's real credentials.

Repository validation for every change: `quick` after an increment and `pr` on
the stable candidate, run through a clean clone while the shared object store
fails the portable-root check.
