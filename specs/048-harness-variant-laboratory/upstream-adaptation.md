# Braid Harness: upstream adaptation map

Status: authorized implementation direction, not code already integrated.
Upstream revision: `1cfe254e8d25b15f37048c3730134686abe60335`.
Use [source hashes](research-evidence/source-identity.json) and the
[audit](../../research/harness2-source-audit.md) when inspecting candidate portions.

The owner explicitly wants useful upstream code, architectures, scaffolding and
key elements adapted to Agent Braid. Reuse should be selective and traceable,
with original English reference prose and no copied upstream logos/infographics.
This is not a requirement to reproduce the implementation from scratch, import
the entire project, or preserve execution assumptions that conflict with our
admitted contracts.

| Upstream source and symbols | Proposed Agent Braid target / task | Reuse and required adaptation |
|---|---|---|
| `core/spec.py`: `ChannelSpec`, `RunView`, `BenchmarkAdapter`; `substrate/base.py`: `Install`, `RunRequest`, `Substrate` | `harness_manifest.py`, `harness_host_codex.py`, `harness_host_claude.py`; 048/T002/T013/T014/T008 | Adapt typed seams separating method, host and task. Replace benchmark-specific installation/model defaults with explicit immutable host/route and task-source bindings. Keep outcome verification independent. |
| `core/tree.py`: `SurfaceSpec`, `normalize_rel`, `read_tree`, `validate` | `harness_surface.py`; 048/T003 | Adapt the surface description, import and validation scaffold. Add owned-root/resolved-path containment, symlink/special-file/size rejection and protected-layer enforcement. Keep the initial editable domain narrow; syntax checks cannot claim runtime isolation. |
| `core/context.py`: `ContextTree`, `build`, `copy_source`, `_write_pool` | `harness_context.py`, `harness_observation.py`; 048/T011/T012 | Adapt evidence-file inventories and short mission pointers. Use positive source inventories, trust labels and bounded selected retrieval rather than blindly copying an entire library. Preserve observation losses and exclude hidden grading material. |
| `core/recursion.py`: `Stage`, `ModeResult`, `_run_stage`, `run_parallel`, `run_sequential` | `harness_refinement.py`; 048/T006 | Adapt the propose/probe/compose state machine, validation feedback and fallback structure. Start with one round; add keep-base/inconclusive outcomes and independent effect/budget admission. Upstream thread-pool width does not authorize native concurrency. Later depth/width scaling must earn its complete-cost result. |
| `core/selection.py`: `assign_ids`, `selection_pool`, `_render_pool`, `reflect_adoption` | Refinement decisions and promotion boundary; 048/T006, 049/T006/T008 | Reuse anonymization and observable-artifact comparison mechanisms. Include the unchanged base, prohibit adoption-by-output-presence, and separate experimental selection, quarantined lessons and ordinary-use promotion. |
| `core/library.py`: `Library.add`, `retain`, `context_dir`, `rebuild_index` | `harness_experience.py`; 049/T006 | Adapt scoped chronological reuse and cue/lesson/evidence structure. Add proposed/quarantined/validated/active/revoked states, version/applicability filters, retention bounds and explicit approval transitions. Store contrary results as well as selected improvements. |
| `core/runmark.py`: `fingerprint`, `mark_complete`, `is_complete`; `core/schedule.py`: `_write_summary`, `_resume` | `harness_manifest.py`, `harness_journal.py`; 048/T002/T007 | Adapt completion markers, atomic summary updates and artifact drift checks. Use full manifest SHA-256 bindings and existing Agent Braid durable-attempt semantics. Do not retain shortened base identities or infer permission renewal from completion. |
| `core/ledger.py`: `Entry`, `Ledger`, `expected_rollouts`, `expected_sessions` | `harness_admission.py`, `harness_evaluation.py`; 048/T004, 049/T003 | Adapt unique-stage accounting and recursion identity checks. Extend to independent pre-dispatch reservations, all attempts/stages and explicit unknown cost dimensions; include selection, reflection, human review and cleanup. |
| `core/judge.py`, `core/report.py`: scoring/result separation and grouped summaries | `harness_verification.py`, `harness_evaluation.py`, `harness_costs.py`; 049/T011/T003/T012/T005 | Reuse delayed independent outcome evaluation and grouped reporting. Keep synthetic/native strata and both objectives explicit, retain all attempted denominators and do not turn ungraded results into success or zero-cost observations. |
| `cli/run_sweep.py`: argument/identity scaffold and `_check_identity` | `harness_cli.py`, `harness_records.py`; 048/T015/T010, 049/T009 | Adapt configuration identity checks, explicit options and deterministic inspect/dry-run behavior. Expose opt-in Agent Braid contracts and owned evidence; do not reproduce upstream cloud defaults or automatically install benchmark stacks. |

## Portions to keep outside the initial integration

The upstream Codex sandbox/approval/hook-trust bypass argv is not an admissible
launcher template for this plan. Benchmark dataset download/judging stacks,
cloud/provider bridges, mutable global configuration and third-party runner
patches are not initial dependencies. Their exclusion does not reject code reuse
elsewhere; it follows the selected owned-repository workload and execution domain.

The eight-component harness taxonomy is useful for inventory and future impact
analysis. The initial editable subset remains task-local guidance/context
packaging. New scripts, tools, hooks or plugins need their own measured need,
effect contract and review before entering that subset. Reuse the substrate seam
without assuming every upstream editable component is already appropriate here.

## Provenance and integration procedure

Before adapting a portion, 048/T001 records exact file/revision/hash, applicable
file-level license, retained copyright/notice obligations and the proposed target.
The main upstream license is Apache-2.0; bundled third-party assets have independent
terms and are not covered by that label automatically. Follow Agent Braid's
LICENSE and third-party convention rather than silently relabeling derived code.
Implementation records required license text/notices and modifications in the
appropriate `LICENSES`, `NOTICE` and `docs/development/THIRD_PARTY.md` paths after
their impact review. No third-party software is imported by this planning packet.

Port a small coherent slice, preserve/adapt useful tests and add the distinct
Agent Braid negative controls. Compare the adapted behavior against the pinned
mechanism and the unchanged native baseline. Record deltas and rejects so that
reviewers can distinguish upstream behavior from our changes. New architecture
or authority files require their normal inventory/review procedure; source reuse
does not waive that process or grant execution permission.

## Advanced adaptation ownership

The initial profile excludes executable components; it does not omit them from the program. [SPEC-050](../050-braid-harness-adaptation/spec.md) owns task-local component schemas and compatibility (T002), skills/autotrigger/loading (T003), qualified helpers/tool guidance (T004), host hooks/plugins (T005), delegated-role scaffolds (T006), deeper sequential/parallel recursion (T007), scoped curation (T008), automatic-policy software (T009) and product lifecycle integration (T010–T012). Adapt the corresponding `core/tree.py`, `core/prompts.py`, `core/recursion.py`, `core/library.py` and substrate surface/installation seams; preserve host differences and source licenses. Upstream bypass launch flags and uncontrolled global installation remain excluded.

The [coverage matrix](capability-coverage.md) is the program inventory, including explicit exclusions and reopen conditions. Upstream names identify source provenance; the resulting Agent Braid capability is **Braid Harness**.
