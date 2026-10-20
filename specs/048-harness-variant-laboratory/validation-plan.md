# Prospective validation

No feature acceptance checks have run. Implementation tests named below are planned, not existing files.

## procedure_req_001

Trace: REQ-001 / SC-001.

Given a candidate changes global instructions, grants, validators, host settings, tools, hooks, executable scripts or an out-of-scope path, exercise: the importer validates the candidate. Required observation: it refuses before materialization or execution and preserves the base; symlinks, traversal, oversized files and undeclared effects refuse.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_002

Trace: REQ-002 / SC-002.

Given a base, candidate, task source, host/model selection, tool inventory, policy, context or environment changes, exercise: any admission, cache or resume consumer validates its immutable manifest. Required observation: it detects the mismatch and refuses reuse; unknown provider build identity stays explicit and cannot masquerade as a pinned build.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_003

Trace: REQ-003 / SC-003.

Given a proposed candidate exists without fresh matching laboratory admission, exercise: a probe requests execution. Required observation: it refuses without effects; only an independently enforced, operator-adopted envelope can admit dynamically generated candidate hashes and no existing runtime grant is widened.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_004

Trace: REQ-004 / SC-004.

Given a probe attempts undeclared filesystem, credential, process or network access, exercise: the qualified laboratory launches or supervises it. Required observation: it denies the effect or stops and marks the attempt interrupted; unavailable containment refuses native launch; a worktree or model instruction alone never qualifies containment.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_005

Trace: REQ-005 / SC-005.

Given general and task-specific variants yield valid, invalid, tied or missing observations, exercise: one configured propose-probe-compose round completes. Required observation: it records contrasts and composition, then returns candidate, keep-base, inconclusive or refused under a frozen selection policy; generating output alone never demonstrates improvement.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_006

Trace: REQ-006 / SC-006.

Given a process stops after a durable start or checkpoint and inputs may drift, exercise: recovery inspects the owned run. Required observation: it reconciles the exact attempt, preserves completed work, and refuses unsafe redispatch or mismatched state; recovery does not renew permissions.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_007

Trace: REQ-007 / SC-007.

Given proposal, probing, selection, reflection, retry or cleanup approaches a frozen limit, exercise: the supervisor admits the next step or observes exhaustion. Required observation: it reserves conservatively and refuses or stops further work; counts, wall time, process/resource usage and unknown costs remain visible; additional cash spend is capped at EUR 0.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_008

Trace: REQ-008 / SC-008.

Given a synthetic or native run finishes or fails, exercise: the CLI or an eventual separately versioned read-only adapter presents its result. Required observation: it exposes identities, decisions, losses, effects, limits and obtained evidence without grants, source promotion, success fabrication or scientific acceptance.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## Candidate checks

Run `python3 scripts/validate_change.py --base develop --profile quick` after implementation increments and `--profile pr` once stable, with the isolated configured interpreter. Feature-specific frozen-candidate evidence and human review remain separate.
