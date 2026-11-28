# Spec Kit contribution workflow

## Authority

[CONSTITUTION.md](../../CONSTITUTION.md) remains the sole normative authority,
including clause zero and all 25 articles. The memory copy is byte-exact.
[Governance](../../GOVERNANCE.md) defines approvals. Applicable ADRs record
subordinate decisions; [semantics](../theory/OPERATIONAL_SEMANTICS.md) define
meaning, versioned schemas define structure, and
[claim discipline](../theory/CLAIM_DISCIPLINE.md) limits evidence interpretation.
Feature specs cannot override these sources. Conflicts require review, not an
invented precedence rule that silently waives an obligation.

MUST conflicts block work; technical rationale cannot authorize them. SHOULD
deviations need reasoning and review; MAY choices stay optional. The constitution
skill only drafts proposals. Actual amendments require a dedicated ADR and pull
request, specific review and founder approval before explicit replica generation.

## Isolated, pinned setup

Use Python 3.12 or newer and Git. Do not install globally or automatically upgrade:

```sh
python3 -m venv .venv-speckit
.venv-speckit/bin/python -m pip install -r requirements-speckit.txt
.venv-speckit/bin/python -m pip install -r requirements-dev.txt
.venv-speckit/bin/python scripts/spec_kit.py check
python3 scripts/validate_spec_kit.py
```

Ensure `python3 --version` meets the prerequisite before creating the environment;
on macOS the system Python may be older, so use your installed Python 3.12
interpreter explicitly. Windows uses `.venv-speckit/Scripts/python.exe` (Windows
interactive discovery and byte-for-byte regeneration have not been exercised).
The lock pins runtime tooling
dependencies and Spec Kit 1.0.7 at immutable upstream commit
`fe1d00e3ccaf495880aaf90fb0e17679e82f065b`; this is not a hermetic binary build.
Both integrations are committed: install/authenticate only the agent you use.
Codex discovers `.agents/skills/`; Claude discovers `.claude/skills/`. Context7
guidance remains in `AGENTS.md`; if unavailable, report the limitation and use
primary documentation without pretending the Context7 check ran. No executable
correctness gate depends on an agent-exclusive tool.

### Shared Git object-store recovery

The portable-root gate rejects unreachable Git objects. Worktrees share one
object store, so commits left by deleted or squash-merged branches can make a
local worktree fail the preflight even when its tracked files are clean. Record
the failure and inspect `git worktree list --porcelain` and
`git fsck --unreachable --no-reflogs` before changing anything. Do not prune,
rewrite history, disable the check, or regenerate skills to hide the failure.

For this specific failure, start a new workflow in a full, independent clone
of the current public `develop` branch. A new worktree or copy of the old
`.git` retains the same object-store problem. After setting up the isolated
Python 3.12+ environment above, run in the new clone:

```sh
.venv-speckit/bin/python scripts/restore_public_spec_history.py
git fsck --unreachable --no-reflogs
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

The restoration tool fetches the exact reviewed SPEC-012 candidate and anchors
it to a local ref. It also restores the already-public annotated reviewed tags
for SPEC-016, SPEC-018 and SPEC-020. Their tag object identities and peeled
candidates are pinned; each candidate must match its frozen assurance record
and descend from the existing public root. Conflicting local or public tag
identities fail without overwriting refs. This also supports clones created
without automatic tag fetching. Restoration does not create reviewer approval
or change the historical records. Unrelated unreachable objects still fail the
portable-root gate. Require zero unreachable objects, one public root and a
passing preflight. If any check still fails, stop there and report the actual
failure. The old object store remains available for a separate history and
worktree audit.

## Equivalent journey

| Phase | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Specify | `$speckit-specify` | `/speckit-specify` | skill `speckit-specify` |
| Clarify | `$speckit-clarify` | `/speckit-clarify` | skill `speckit-clarify` |
| Plan | `$speckit-plan` | `/speckit-plan` | skill `speckit-plan` |
| Tasks | `$speckit-tasks` | `/speckit-tasks` | skill `speckit-tasks` |
| Analyze | `$speckit-analyze` | `/speckit-analyze` | skill `speckit-analyze` |
| Implement | `$speckit-implement` | `/speckit-implement` | skill `speckit-implement` |
| Converge | `$speckit-converge` | `/speckit-converge` | skill `speckit-converge` |
| Amendment proposal | `$speckit-constitution` | `/speckit-constitution` | skill `speckit-constitution` |

Checklist and taskstoissues use the same prefixes. OpenCode has no committed Spec
Kit integration: OpenCode was observed discovering skills from `.agents/skills/` and
`.claude/skills/` (2.1.4, macOS arm64, simple marker skills; discovery of the
`speckit-*` skills themselves is unobserved), so ask the agent to use the named skill. How OpenCode lists and invokes skills in a live session, for
example whether a slash form exists, is unobserved; nothing in this repository
depends on OpenCode. Issue drafts do not authorize
remote writes. Handoffs do not authorize concurrent agents, commits, pushes or
autonomous delivery. Review each stage before proceeding. The
[pilot quickstart](../../specs/001-certificate-verifier-pilot/quickstart.md)
provides an equivalent exercise without recreating the feature.

After a spec or task change is merged, use the
[GitHub tracking reconciliation](GITHUB_TRACKING.md) to audit stable IDs and
review issue, milestone and Project updates. This tracking step remains separate
from feature assurance and approval.

For empirical protocols, the shared templates and commands prompt authors to
register source permission and yield before fitting, distinguish human proxy
labels from observed outcomes, predefine reviewer adjudication and annotation
of the complete holdout independently of method rankings, and specify missing
labels, class/group coverage, calibration and total cost. These are review
questions and planning obligations. Rendering and structural validation do
not verify consent, label quality, statistical validity or a positive result.

## Specification conventions

Every new `spec.md` carries the sections below, in addition to the template's
purpose, authorities, requirements and scientific boundaries. A refined existing
spec keeps its current headings and adds each section it lacks. Where an
equivalent section exists under another name, such as "Owner decisions (open)"
for open questions, keep that heading and add one line that starts with the
section name from the table, for example "Open questions: OD-1, OD-2".

| Section | Content | Rule when nothing applies |
|---|---|---|
| Non-functional requirements | Operational and quality constraints, each with its REQ ID. | Record an open question for the owner; do not invent a constraint. |
| Security and privacy | Each obligation about secrets, credentials or personal data as its own REQ with MUST or MUST NOT. | Write "No security or privacy obligation applies:" and the reason. |
| Terminology | Terms the feature introduces and the allowed values of each enumeration. Shared terms follow the root `TERMINOLOGY.md`. | Write "No feature-specific terms." |
| Risks and assumptions | One entry per line, starting with "Risk:" or "Assumption:", naming the REQ affected, or the task once tasks exist. | Record an open question for the owner. |
| Exit criteria | The evidence required to consider verification complete. | Record an open question for the owner. |
| Open questions | Each unresolved decision as a question with its owner. | Write "No unresolved questions." |

Rules:

- Every MUST or MUST NOT obligation has its own `REQ-###` ID, including
  exclusions. A new REQ needs scenarios in `assurance.json` like any other
  requirement. Refining an existing spec appends new REQ numbers and never
  renumbers existing ones.
- Plans and tasks name each dependency by ID in the text: "depends on T002",
  "requires REQ-001". The task line format does not change:
  `- [ ] T001: text`, optionally `- [ ] T001 (tags): text`, as parsed by
  `scripts/sync_github_tracking.py`.
- Content comes from the spec, plan and tasks. When a section has no source,
  record an open question for the owner. Never write filler.

The owner adopted these conventions on 2026-11-25. SpecTorque, an external
heuristic checker, was used as an aid: it detects practices by text patterns, so
its score shows that a section exists, not that its content is correct. The
score does not decide a convention. A SpecTorque practice that conflicts with a
convention in this document goes to owner review, and this section changes only
by owner decision. Do not edit a spec to silence a finding that is an engine
false positive.

### Reference check and review sequence

Proposed 2026-11-28 after the SPEC-090 and SPEC-091 drafting, where five full
review rounds each found regressions introduced by the previous fixes. It takes
effect when the owner merges this section.

Mechanical questions are answered by a script, not by a reviewer:

```bash
python3 -m scripts.check_spec_references specs/NNN-your-feature [specs/MMM-other ...]
```

The script reads `assurance.json` (REQ and SC), `tasks.md` (tasks) and `spec.md`
(owner decisions written `**OD-n`). It reports as errors: an ID cited and not
defined, including `SPEC-NNN <id>` citations into another feature; a requirement
without a scenario; a requirement or scenario no task traces; a task dependency
cycle, within and across the named features; a T001 decision range that stops
short of the highest decision; and a planned test file in `validation-plan.md`
that the task named as its owner does not list. It reports as warnings a task
that names no requirement and a decision never cited. It does not read meaning:
it cannot tell whether a citation points at the right rule, only that the rule
exists. Specs written before this section are not required to pass it.

The script is interim. Reference integrity belongs in SpecTorque, which already
counts traceability links; this script exists because SpecTorque does not yet
report these errors for this repository's ID conventions. It is run by hand and
is not part of CI or the validation profiles. Retire the script, its tests and
this paragraph when a SpecTorque release covers the same errors; the review
sequence below stays.

Review sequence for a new or substantially rewritten spec:

1. Run the reference check and fix every error before any review.
2. Before the first pull request, run one adversarial review (contradictions,
   ambiguous normative sentences, recomputed numbers, protocol order) and one
   counterfactual review (walk the text through past failures, plausible futures
   and each offered decision option).
3. Apply the findings in one pass. Rerun the reference check.
4. Verify the fixes on the difference only: review the commits since the
   reviewed one, plus the sentences they cite. Repeat a full review only when a
   fix changes a gate rule, an estimand, the set of owner decisions or the task
   order.
5. Record the SpecTorque score with the highest score its rubric can give, so a
   score at that ceiling is not read as unfinished work.

## Assurance record

SPEC-045's draft assurance retains the historical synthetic software snapshot.
After PR #508's linear-history integration, restore its exact already-public
annotated draft tag `spec-045-software-candidate-bb2e032` with the same
`restore_public_spec_history.py` command. The tool pins the tag object and peeled
candidate; portable validation requires pending draft metadata, exact assurance
bytes and both historical snapshots in that candidate's ancestry. This restores
validation without changing the record or granting feature/model/source approval.

Each `specs/<feature>/spec.md` requires a sibling `assurance.json`. Use the pilot's
shape, never copy its claims as evidence. The required fields are:

- `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested`
  or `approved`. Approval requires a repo `review_record`; the checker verifies
  existence, not reviewer identity or authorization.
- Nonempty `scope`, `assumptions`, `domain`, `observation_contract`,
  `execution_contract`, `scientific_limits`, `compatibility`, `hypotheses`.
- `articles`: applicable integers 0–25; `references`: existing repo-relative paths.
- `requirements`: unique `REQ-001` IDs and text; each has `scenarios` with unique
  `SC-001` IDs, `given`, `when`, `then`, `test_file`, `test_name`,
  `planned_evidence`, and `obtained_evidence` arrays.
- Each obtained item has `path`, `sha256`, actual `command`, `outcome`, `limits`.
  Preserve raw results and environment/provenance. Drafts may have empty evidence;
  validated scenarios may not. Negative/inconclusive findings can complete a
  research protocol without supporting its hypothesis.
- `authority_snapshot`: explicit authority mode, commit and hashes. Draft work
  uses `current` mode and must match the complete working-tree inventory. A
  reviewed candidate uses `historical` mode bound to a full Git commit whose
  authority bytes are verified from repository history. Later additions do not
  rewrite a closed decision; they remain outside its historical claim.
- `evidence_snapshot`: independent `current` or `historical` binding for obtained
  evidence and every input hash embedded in it. This permits a review to bind an
  earlier authority candidate while a later commit packages the review record,
  without comparing historical evidence to mutable working-tree bytes.

After drafting the record, run explicitly:

```sh
python3 scripts/validate_spec_kit.py snapshot specs/your-feature
python3 scripts/validate_spec_kit.py
```

SPEC-019's squashed synthetic software draft is retained in the exact public
annotated tag `spec-019-software-candidate-c30e8bc`. The restoration tool pins
both its tag object and peeled candidate; it checks the exact clean public root
before fetching or changing refs, and rejects any additional reachable root.
Git replacement objects and legacy graft files are ignored in authority, evidence
and ancestry checks. This separate draft route requires
the allowlisted record path, unchanged `draft/pending` bytes matching the tagged
candidate, one clean public root, and both historical snapshots in that
candidate's ancestry. It then runs ordinary strict authority/evidence validation;
errors propagate. It never supplies approval or substitutes for the existing
reviewed-tag route. A changed record does not inherit this exception. Neither the
immutable export manifest nor the historical assurance is rewritten.
The reviewed-tag route also requires the exact already-public tag object and
candidate from its literal catalog. A locally created review record and annotated
tag cannot promote a preserved draft or impersonate a published reviewed tag.
For those already-public reviewed candidates, the assurance and review metadata
must also match the literal SHA256 commitments of their published bytes in merged
`develop` commit `c51c91ee270c84d6786355c20a49ee86cf38648e`. These are retention
checks, not a new approval. Metadata changes require a separately reviewed update;
they cannot silently inherit the retained historical review.
Changed retained approval metadata is rejected before ancestry checks or portable
fallback; availability of another validation route cannot waive its byte binding.

Snapshot includes selected canonical root authorities and all ADRs, theory,
architecture and schema files. Additions, deletions and changes invalidate every
`current` record. Snapshot always resets human review to pending. Once a clean
candidate commit exists, run `python3 scripts/validate_spec_kit.py freeze
specs/your-feature`; approval is valid only against that frozen commit. Historical
records are verified from Git and never claim coverage of later authorities.
Report changes and seek fresh review; do not refresh to hide drift. CI requires
full Git history for this check. Additional references are checked for existence;
bind their bytes as evidence when they matter to a claim.

## Regeneration and maintenance

Edit only `.specify/templates/overrides/` for command/template policies.
`guardrails.md` is injected before every command's actions. Full replacements avoid
contradictory upstream instructions. Rendering uses the pinned official adapters.

```sh
.venv-speckit/bin/python scripts/spec_kit.py generate
.venv-speckit/bin/python scripts/spec_kit.py check
python3 scripts/constitution_replica.py check
python3 scripts/validate_spec_kit.py
```

The generator reads installed/default integration state, stages official `init`,
`integration install` and `integration use` in temporary directories, refreshes
each integration and restores selection before supplying project overrides to
each adapter. It copies scoped scaffolding only, never the live Constitution,
replica or bundled automated delivery workflow, and never starts an agent.

If deliberately running upstream `specify integration use claude` or `codex`,
immediately regenerate and check. Raw upstream operations can restore default
commands and are not a safe final state. The hash gate catches stale artifacts
in either integration. constitution-sync, presets, extensions and workflows are
incompatible with this reviewed setup. Upgrades require reviewing source, pins,
notices and both outputs and rerunning the full test matrix.

## Checks and limits

Use the [validation profiles](VALIDATION_PROFILES.md). Structural Spec Kit validation
and pinned render checks remain part of every stable PR candidate. Run the expensive
temporary-repository matrix only when changing templates, generation scripts,
generated Codex/Claude skills, the pinned version or integration requirements; the
classifier fails closed for unknown paths. Upgrades still require the full matrix.
Offline validation checks committed inventories; CI re-renders independently from
pinned source so changing a checksum does not substitute for proper generation.
Temporary-repository tests cover Codex-only, Claude-only and both, without agent accounts.
Checks validate bytes, references, evidence presence and freshness, not all
constitutional semantics, scientific truth or signatures. Interactive agent
exercises and human review remain separate and are reported in the pilot.

The generic local skill-creator validator rejects the official adapter's
`compatibility` frontmatter field because its allowlist is narrower. We retain
the official format: integration tests parse native YAML metadata and check
required names/descriptions and effective bodies. This is not claimed as a passing
generic-validator run or a live-agent discovery test.
