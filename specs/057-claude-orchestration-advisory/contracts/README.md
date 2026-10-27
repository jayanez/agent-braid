# SPEC-057 contracts

Status: draft design, not adopted or implemented interfaces, edited 2026-10-24 for the founder decisions of that day. The pure module `agent_braid/ownership.py`, the four CLI subcommands (`expand-ownership`, `check-ownership`, `audit-isolation`, `report-recovery`) and the recipe document do not exist yet. These files fix the planned shapes so that tests can be written first (tasks T012 to T024). They change no existing contract, schema, MCP tool, grant or skill. The subcommand names are provisional until the plan's design is accepted.

| File | Purpose |
| --- | --- |
| [ownership-declaration.schema.json](ownership-declaration.schema.json) | One declaration of what each parallel unit reads, writes, creates and deletes. Bounded, content-free, vendor-neutral core. JSON Schema draft 2020-12. |
| [ownership-declaration.example.json](ownership-declaration.example.json) | A valid two-unit example. An example is not evidence. |
| [envelope-receipt.schema.json](envelope-receipt.schema.json) | The declared-versus-observed receipt at a committed or quiesced checkpoint. Class `1-syntactic`; `not-observed` is never clean. On a shared tree it attributes nothing to any unit, and a list over its bound is truncated and recorded (`truncations`), never refused. |
| [hazard-notice.schema.json](hazard-notice.schema.json) | Epoch-stamped, expiring, supersedable notice delivered as data (pull). Repository strings only in labelled, escaped, bounded data fields. |
| [orchestration-settings.schema.json](orchestration-settings.schema.json) | Notification strategy and guard mode per scope (most specific scope wins, with a `block` floor; operator-owned), the resolved form, and a versioned `extensions` member that SPEC-059 extends. Only the Mailbox (pull notice) is effective in SPEC-057. |
| [command-error.schema.json](command-error.schema.json) | The one representation of a refusal: a stable error code from a closed list and no result object. |
| [policy-profile.schema.json](policy-profile.schema.json) | Shared with SPEC-058: ownership compiled to one of three outputs, the modes ladder, the guard vocabulary (no `allow`), the coverage boundary and the enforcement attestation. |
| [policy-profile.example.json](policy-profile.example.json) | A valid `audit` profile with two outputs and Bash `not-covered`. An example is not evidence. |
| [policy-profile.example-off.json](policy-profile.example-off.json) | A valid minimal profile with the mode absent (meaning `off`). An example is not evidence. |
| [recovery-report.schema.json](recovery-report.schema.json) | Read-only recovery and orphan report; `actionsTaken` is always empty. |
| [surface-capability-matrix.json](surface-capability-matrix.json) | Surface by lifecycle matrix with class, owner, minimum host version, preview label and evidence status. Documentation readings until receipts exist. |
| [interop-inputs.md](interop-inputs.md) | Deferred design for optional imports from other coordination tools. |

All schemas reject unknown members (`additionalProperties: false` at every object). They were checked to be valid draft 2020-12 documents with the pinned `jsonschema` package in the repository's isolated environment, as a planning aid only, and the example validates against the declaration schema; the other schemas have no example yet and their samples must be written and validated by the tasks that own them. None of this is obtained evidence for any requirement.

## Conventions shared by every result

- `executionAuthorization` is the constant `false`. No member can carry, request or accept a grant, a launch, a message or a resume.
- Result envelopes carry the Article 13 and 14 block: compatibility class, property, evidence method, domain, assumptions, observation contract, execution contract and `notAGuarantee: true`. The class is a claim by the producer, not verified evidence or authorization (Article 13).
- One refusal rule. A refusal (busy lock, unstable snapshot, unobservable source, over-bound or malformed input, existing output path) is an error: a code from `command-error.schema.json`, a nonzero exit and no result object. It can never appear as a receipt, verdict or report and is never read as independent or clean. `unknown` and `not-observed` inside a produced result are Article 13 outcomes of the observation contract (for example a unit with no supplied source) and are also never clean. The receipt's `notObservedReason` therefore has only `no-source-supplied` and `not-a-descendant-of-base`.
- Repository-derived strings are paths or names only, bounded to 256 characters, and never placed in an instruction field. They contain no character of the text exclusion set: Cc and C1 controls, Cf format characters (including bidirectional controls, zero-width characters and the soft hyphen), U+2028 and U+2029, tag characters and a few invisible fillers (the exact ranges are in `$defs/repositoryText` of `hazard-notice.schema.json`, the single definition). The producer escapes such characters to visible text; the schemas reject a string that still contains one. Every schema that bounds repository text uses that pattern byte for byte, and a test compares them.
- Pattern anchors. The pinned Python validator uses `re.search`, where a bare `$` also matches before a final line feed. Every pattern therefore ends with `(?!\n)$`, which is also valid in other regular-expression engines. Seeded fixtures include a trailing line feed for each pattern.
- `validUntil` is a UTC time whose shape is enforced by a pattern, so no result depends on a `format` checker (the `jsonschema` package skips `date-time` unless an RFC 3339 validator is installed). Calendar validity is a reader rule.
- No file content, command text, prompt or transcript appears in any member of any schema.

## Declaration

- `units`: 2 to 32 entries. `reads`, `writes`, `creates`, `deletes`: at most 512 paths each. Directories and patterns are allowed in the declaration; the expansion step turns them into exact repository-relative paths against the pinned base, or into partial coverage when it cannot.
- `criticalReads` must be a subset of `reads` (validator rule, not a schema rule). A write by another unit to a critical read is a hazard.
- `dependsOn` is the only source of the analyzer class `ordered`.
- `complete: true` requires a top-level `base`; even then coverage is partial unless every entry expanded exactly.
- `surface` is drawn from the closed vocabulary of the whole family: `workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`. The same ids appear in the matrix, the policy-profile attestation and the SPEC-058 and SPEC-059 contracts; adding one is a versioned schema change. The core has no other vendor-specific member.
- `provenance` is `orchestrator-session`, `user-script`, `human` or `imported`; `importedFrom` (tool and version) is required exactly when it is `imported`.
- A unit id may not be `unattributed`, which the attributed-write export reserves. A base `ref` may not contain `..` or `//`. Duplicate unit ids and self-dependency are validator rules.
- `unattributedWriterExemptions` are explicit, declared rules. Orchestrator, human and shared-tree writers are `unknown` by default; only a path under a rule is excluded, and the receipt names the rule in `exemptedPaths`.

## Policy profile

- Outputs: `native-host-settings`, `companion-plugin-hooks`, `settings-snippet`. Hooks inside the main plugin are rejected and unrepresentable.
- `mode` absent means `off`; when enabled the default is `audit`. That default and the ladder are compiler and validator rules (SPEC-058 and `tests/test_policy_profile.py`), not schema guarantees; the schema does express that an enabled mode needs `protectedControlPaths` and `failureBehavior`.
- `failureBehavior` states fail-open-recorded for a guard internal error or timeout, and `ask` only for undecidable paths in `block` until probe GP-2.
- `guardVocabulary` is the constant list `no-opinion`, `ask`, `deny`, `additionalContext`.
- `enforcementObserved` defaults to false and may be true only with an attestation naming the host version, surface and receipt.
- `coverageBoundary.bash` may be `covered-where-verified` only when `outputs` is exactly `native-host-settings` and an attestation names the HV-8 receipt (expressed as a conditional rule in the schema); `unattributed` is always `not-covered`. `tools` is Write and Edit. `NotebookEdit` is not representable: it was proposed by SPEC-058, the founder decision names Write and Edit, and it would be added by a versioned schema change if the founder accepts it.

## Settings precedence and operator-owned locations

Decided 2026-10-24: the most specific scope wins (`conversation` over `repository` over `user`), but a `block` guard mode set at repository or user scope is a floor that a more specific scope cannot lower (the resolution records the floor and that lowering was refused). Settings are operator-owned: they are read only from the operator-owned locations below, and anything else is refused with `ERR-UNOBSERVABLE-SOURCE` (no result).

| Scope | Operator-owned location | Refused |
| --- | --- | --- |
| `user` | A file in the per-user Agent Braid configuration directory, outside every repository. | A symlink, a file writable by group or others, a file inside any working tree. |
| `repository` | A file outside every working tree of the repository (including linked worktrees), in the per-user configuration directory under a subdirectory named by the repository identity digest. Never a tracked or untracked file inside a working tree. | Any path inside a working tree, a symlink, a file writable by group or others. |
| `conversation` | A document the operator supplies at invocation, as an argument or on standard input. | Reading it from the repository, from a model-writable path or from a tool result. |

The block floor can only come from the `repository` and `user` locations, so an agent that edits a file inside its working tree cannot lower it, in any guard mode. The conversation scope is supplied at invocation (by the operator, or by the orchestrating session on the operator's behalf) and can raise the mode or leave it but never lower a floor. The locations are not protected against a writer that has the operator's own file permissions, including shell access: the floor is exactly as strong as those permissions and no stronger. The locations are fixed by the resolver (T022): the `user` file is `orchestration-settings.json` in the configuration directory the caller supplies, and the `repository` file is `repositories/<repository identity digest, 64 lowercase hex>/orchestration-settings.json` in that directory. The resolver refuses (`ERR-UNOBSERVABLE-SOURCE`) a symlink, a file that is not regular, a file writable by group or others, a file whose resolved path leaves the configuration directory, and a file inside any working tree of the repository the caller names (tracked or untracked, linked worktrees included). A missing file is an absent scope, not an error. A document read from a scope's location may carry only that scope's member (and `schemaVersion` and `extensions`); a floor offered anywhere else is refused as malformed (`ERR-MALFORMED-INPUT`). `resolvedFromScope` is the most specific present scope that sets at least one member, or `default`; the guard mode is the most specific scope's value unless a repository or user `block` floor holds it at `block`. The resolver does not check the permissions of the directories above the file: the floor is as strong as the file permissions and no stronger. It reports in `scopeSources` where each scope came from. A test supplies a tracked repository file and expects the refusal.

Mode and strategy are coherent: `push` requires `megaphone` or `doorbell`, those strategies require `push`, and `pull` allows only `mailbox-whisper`. The resolver returns the effective delivery (always the Mailbox pull notice in SPEC-057), the requested mode and strategy (`mailbox-whisper`, `megaphone`, `doorbell`), the push status (`reserved-for-SPEC-059` when a push strategy was requested), the Whisper status (a SPEC-058 companion output, not enabled here) and the scope it came from.

### Extension point

`extensions` (top level and per scope) is keyed by owner specification (`SPEC-059`), each entry carrying its own `extensionVersion` and a bounded `settings` object of scalars and short string lists. SPEC-057 stores an entry without interpreting it, reports it as `not-interpreted-by-SPEC-057` and never treats it as effective. SPEC-059 defines its push transports and kill switch under its own versioned schema and does not need a change here.

## Matrix

A cell is host-observed only with a `receipt` path. The surface ids are the closed four-id set (`surfaceIds` in the file). `minHostVersion` is the first changelog entry that names the capability (`versionBasis`), a documentation reading and not a support claim; SPEC-058's matrix may differ because it names a different capability. `covered-by-SPEC-052` no longer exists as a status: the integration cells say `reuse-of-SPEC-052-unverified`, a plan to reuse an unadopted, host-unverified gate that takes commit sources only. The checker rejects a host-observed cell without one, a cell without a class, a missing preview label for agent teams and agent view, and any wording that says a surface is enforced. `not-applicable` is the class of a deferred cell.

## Host-probe receipts

Receipts for HV-6 to HV-13, from probes launched by the orchestrating session after the founder authorized each one, live under `specs/057-claude-orchestration-advisory/evidence/` (not created by the specification). They contain counts and booleans, the Claude Code version, operating system, surface and date, the outcome (`pass`, `fail` or `unobserved`) and the hashes of the probe scripts that stay outside the repository. A receipt never contains content, paths from a user's repository, prompts or transcripts.
