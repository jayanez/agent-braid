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
it to a local ref. Require zero unreachable objects, one public root and a
passing preflight. If any check still fails, stop there and report the actual
failure. The old object store remains available for a separate history and
worktree audit.

## Equivalent journey

| Phase | Codex | Claude Code |
|---|---|---|
| Specify | `$speckit-specify` | `/speckit-specify` |
| Clarify | `$speckit-clarify` | `/speckit-clarify` |
| Plan | `$speckit-plan` | `/speckit-plan` |
| Tasks | `$speckit-tasks` | `/speckit-tasks` |
| Analyze | `$speckit-analyze` | `/speckit-analyze` |
| Implement | `$speckit-implement` | `/speckit-implement` |
| Converge | `$speckit-converge` | `/speckit-converge` |
| Amendment proposal | `$speckit-constitution` | `/speckit-constitution` |

Checklist and taskstoissues use the same prefixes. Issue drafts do not authorize
remote writes. Handoffs do not authorize concurrent agents, commits, pushes or
autonomous delivery. Review each stage before proceeding. The
[pilot quickstart](../../specs/001-certificate-verifier-pilot/quickstart.md)
provides an equivalent exercise without recreating the feature.

After a spec or task change is merged, use the
[GitHub tracking reconciliation](GITHUB_TRACKING.md) to audit stable IDs and
review issue, milestone and Project updates. This tracking step remains separate
from feature assurance and approval.

## Assurance record

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
