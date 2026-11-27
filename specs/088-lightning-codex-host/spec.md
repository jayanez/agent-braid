# SPEC-088: Codex as a Braid Lightning host

**Milestone:** Host parity (owner decision of 2026-11-27, phase F7 of the cleanup plan).
Second specification of the umbrella; it registers Codex through the host registry of
[SPEC-087](../087-host-registry/spec.md) and unblocks the measurement skeleton
[SPEC-089](../089-analyze-work-validity-codex-opencode/spec.md).

**Status:** draft, documentation only. Nothing is implemented, installed, run or
published by this specification's first PR. Code waits for owner approval of the spec
and plan (T001) and for SPEC-087's registry code (its T003 to T007).

## Purpose and scope

The Braid Lightning runner can run rollouts only in `claude-code` and `opencode`:
`lightning_config.HOSTS`, `lightning_schema.HOSTS`, the export terms check, and the
runner's credential, fake-binary and binary tables all list those two hosts and no
other. Codex has the pieces around it (the SPEC-069 native-run driver launches it; the
parser, tool classes and a fake host for the driver exist), but the Lightning runner
refuses it at configuration time. [Issue #1700](https://github.com/jayanez/agent-braid/issues/1700)
(Deferred) names this as the hard prerequisite of measuring `analyze-work` validity on
Codex.

This is engineering, not a research protocol. It adds `codex` as a Lightning **rollout
host**: the host runs the rollouts of a prompt set in a disposable profile, and the
report shows its rates with Wilson intervals like any host. It adds no measurement
claim; the first real Codex rollout is an owner-gated task (T011), and it ends as a
declared limit when the route stays unverified.

Facts verified on `develop` at 65f101ba by an AST scan of `agent_braid/` and `scripts/`
for every string constant `claude-code`, `claude`, `codex` or `opencode` in a module that
mentions Lightning (the collection scan of SPEC-087 sees only collections of two or more
hosts, so it misses single-host comparisons; the complete inventory is in the
[plan](plan.md#lightning-host-sites-verified-2026-11-27)):

- `agent_braid/lightning_config.py:25` `HOSTS = ('claude-code', 'opencode')` feeds both
  `rollout.hosts` (default `list(HOSTS)`, line 40) and `optimizer.host` (line 54), and
  `lightning_cli.py:70` (`--optimizer-host choices`). Adding `codex` to that one tuple
  would make Codex a **default** rollout host and a configurable optimizer host.
- `agent_braid/lightning_runner.py:142` refuses every optimizer host except
  `claude-code` (`route-unverified`); `:268-271` accepts a credential source only for
  `claude-code` (`apiKeySource` in `{oauth, none}`) and `opencode` (`oauth`); `:703-706`
  turns an OpenCode `route-unverified` into a declared limit and lets the run continue.
- `agent_braid/lightning_hosts.py:40` and `:383` already key `META_TOOLS` and `PARSERS`
  by `claude-code`, `codex`, `opencode`; its `parse_codex` docstring says it is
  unverified against a live model, and it sets no `key_source`.
- `agent_braid/lightning_evaluation.py:34` `REQUIRED_HOSTS = ("claude-code",)`
  (Amendment 1, 2026-11-13); `h1_outcome` reads only the required hosts, and
  `runner.report` summarizes every host it finds.
- `agent_braid/tooling_host_events.py` parses `codex exec --json` (Codex CLI 0.162.0 or
  newer, `docs/tooling/HOST_EVENTS.md`); `agent_braid/tooling_subscription.py:23` and
  the Codex observer treat the Codex route as the native ChatGPT account.
  `docs/tooling/LIGHTNING.md:73` documents OpenCode as `route-unverified`.
- `scripts/spec069_native_runs.py` already supports `codex` (`HOSTS`, `KEY_SPECS`,
  `AUTH_*`, `prompt_argv`, `install_plugin`); the Lightning runner calls it and this
  specification consumes it unchanged.

In scope: `codex` in the `lightning-run` capability (SPEC-087 registry); the
`lightning-optimizer-config` and `lightning-default-rollout` capabilities that keep the optimizer enum and the default rollout hosts exactly as today; the Codex
entries of the feature-owned runner tables; additive schema and export-terms acceptance
of `codex`; the declared-limit path for an unverified Codex route; verification of
`parse_codex` and of the Codex tool-name prefix against recorded Codex streams; a fake
Codex host for `--fake-hosts`; differential proof that `claude-code` and `opencode`
behavior and bytes do not change; documentation.

Owner decisions (2026-11-27, binding): `claude-code` is the canonical Claude identifier
and no claim is made for an unmeasured host (orchestrator decisions); OD-1 to OD-4
below, answered in the author session.

Exclusions (each is stated as a requirement with its REQ ID below):

- Changing `REQUIRED_HOSTS` or making Codex count in H1 or in a promotion decision
  (REQ-011).
- Letting Codex serve optimizer calls (REQ-004).
- Changing the default `rollout.hosts` or any output, record, digest or refusal outcome
  for runs that do not name `codex` (REQ-005).
- Reading a credential file, writing a credential, or accepting a paid route (REQ-007).
- Opening the dataset-export terms gate or saying any provider permits training
  (REQ-013).
- Running Codex rollouts on a frozen, spent or test held-out set, or authorizing any
  real run (REQ-014, REQ-015).
- Editing a closed specification, SPEC-087, SPEC-089, the SPEC-069 drivers or recorded
  evidence (REQ-016).
- Any claim that Codex meets D4, or about the validity of `analyze-work` on Codex
  (REQ-017).

## Authorities

[CONSTITUTION.md](../../CONSTITUTION.md) clause zero and Articles 0, 5, 13, 14, 19, 20;
[GOVERNANCE.md](../../GOVERNANCE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
subscription route). Read, not edited: SPEC-087 (registry), SPEC-069 (driver and
held-out evidence), SPEC-070 (foundations), SPEC-071 (rollouts and refusal codes),
SPEC-072 (Amendment 1), SPEC-073 (promotion), SPEC-074 (consent), SPEC-075 (export
terms gate), SPEC-078 and SPEC-079 (held-out splits). No authority conflict found.
Document hashes are kept in `assurance.json`.

## Requirements and acceptance scenarios

**REQ-001 Owner review before code.** The spec and plan are reviewed before any code.

- **SC-001:** Given this spec and plan, when the owner reviews them, then each open
  question is decided or deferred in a dated record and the spec is approved, amended or
  rejected.

**REQ-002 Codex joins `lightning-run` through the registry.** `codex` is added to the
`lightning-run` capability of the SPEC-087 registry (its REQ-002, REQ-006), appended
after the current members so the order is `claude-code`, `opencode`, `codex`. Each
Lightning site that today lists the two hosts reads that capability, and no module
outside the registry and SPEC-087's exception files declares a new literal collection
of host identifiers (SPEC-087 REQ-010). The capability name may be renamed by SPEC-087
T001; this specification follows the name merged there.

- **SC-002:** Given the registry after this change, when `hosts_with("lightning-run")`
  is evaluated, then it returns `claude-code`, `opencode`, `codex` in that order; and
  given the SPEC-087 guard test, when it runs, then it passes with no new exception
  file.

**REQ-003 Feature-owned tables gain Codex.** The runner's credential, fake-binary and
binary tables, the schema, config and export-terms host checks, and the declared-limit
table of REQ-008 each cover exactly the `lightning-run` members, and a key-set test
pins each to the capability (SPEC-087 REQ-009). `META_TOOLS` and `PARSERS`
(`lightning-tool-classes`) keep their three keys. Per-host credential variable names,
binary names, parsers and tool prefixes stay in `agent_braid/lightning_*.py`, never in
the registry (SPEC-087 REQ-009).

- **SC-003:** Given each table the plan lists, when the key-set test runs, then each key
  set equals its capability query; and when `codex` is removed from one table, then the
  test fails.

**REQ-004 Optimizer path unchanged.** The registry gains a capability
`lightning-optimizer-config` whose members are today's optimizer enum, `claude-code` and
`opencode`, in that order; `optimizer.host` and the CLI `--optimizer-host` accept only its
members. `codex` is not a member, so `optimizer.host: codex` ends in the existing
configuration refusal (`config-enum`) before any run. `SandboxedHost` stays the only
later gate and keeps refusing every host but `claude-code`, so `optimizer.host: opencode`
behaves exactly as today. Codex MUST NOT serve optimizer calls (OD-2).

- **SC-004:** Given a configuration with `optimizer.host` set to `codex`, when it is
  validated, then it is refused with `config-enum` and nothing is launched; given
  `opencode`, then it passes configuration and is refused at launch as today; and given
  `claude-code`, then it is accepted as before.

**REQ-005 Existing hosts and defaults unchanged.** The default `rollout.hosts` is the
registry capability `lightning-default-rollout`, whose members are `claude-code` and
`opencode`, in that order; it is no longer derived from the whole `lightning-run` tuple,
and Codex is opt-in by naming it. The wizard prompt text of `lightning_cli.py:26` is
unchanged. For every configuration, preview, run, plan,
record, report and refusal that does not name `codex`, the output bytes, digests and
refusal codes are identical to those before the change. The one exemption is refusal
and usage text that lists the accepted hosts, which may additionally list `codex`.

- **SC-005:** Given recorded fixtures for `lightning init` preview, `run --dry-run`,
  `run --fake-hosts`, `status`, `report` and the config and schema refusals, recorded on
  `develop` at 65f101ba, when each runs after the change on the same input without
  `codex`, then the bytes are identical, except accepted-host lists in refusal text.

**REQ-006 Additive schema acceptance.** `codex` is accepted additively in the `host`
fields of the rollout, model-identity and `attempt_start` records. Schema version
strings (`v0.1`) do not change, no stored record is rewritten, and a Codex record read
by a reader that predates this change is refused (fail closed) (OD-4).

- **SC-006:** Given every committed Lightning record and fixture, when read after the
  change, then each is accepted and unchanged; and given a record with host `codex`,
  then the new reader accepts it and its schema version string is the old one.

**REQ-007 Subscription route, same bar as the other hosts.** A Codex rollout runs only
on the subscription route: the existing pre-launch gate refuses any provider key or
route variable (`paid-route-refused`, including `CODEX_API_KEY` and `OPENAI_API_KEY`),
the runner reads no credential file and writes no credential, and any credential value
is held in the environment of the child only and registered with the secret scanner
(SPEC-071 REQ-004, REQ-005). After launch the runner accepts a Codex credential source
only from a field the host itself reports or from an observation that T003 records and
the owner reviews; it does not infer the route from the profile or from the absence of
a key (OD-3). Until that evidence exists the key-source verdict for `codex` is
`route-unverified`.

- **SC-007:** Given a Codex rollout (fake host) with a provider key in the environment,
  when it is planned, then it is refused with `paid-route-refused` before launch; given
  a Codex transcript that reports no credential source, then the verdict is
  `route-unverified`; and given the source observed by T003, then only that value is
  accepted and any other value ends as `route-unverified`.

**REQ-008 Unverified Codex route is a declared limit.** When Codex ends as
`route-unverified`, the run records `hosts.codex.status = declared-limit` with the
reason text, does not set a run-level refusal, and continues with the remaining hosts,
as it does for `opencode` today. The set of hosts that end this way is a feature-owned
table keyed by the `lightning-run` members, not a literal comparison.

- **SC-008:** Given a run of `claude-code` and `codex` where Codex reports no source,
  when it ends, then `claude-code` has its normal records, `codex` is a declared limit,
  and the run status carries no refusal; and given a `claude-code` `route-unverified`,
  then the run still stops as today.

**REQ-009 Codex transcripts are parsed from observation, not assumption.** Before any
real Codex rollout, `parse_codex`, the Codex tool-name prefix (`agent-braid__`) and the
tool-class decision are checked against recorded Codex streams, and the model-identity
source of a Codex rollout is recorded; an unknown model is recorded as unobserved, never
guessed. The verification is written as obtained evidence and states the Codex build it
covers.

- **SC-009:** Given recorded Codex `exec --json` streams, when `parse_codex` and
  `tool_class` run on them, then the tool calls, failure flags and classes equal the
  recorded expectation, and a stream with a denied tool is classed `denied`; and given a
  stream with no model field, then the rollout records the model as unobserved.

**REQ-010 Fake Codex host for the pipeline.** `--fake-hosts` can run Codex through a
fixture `tests/fixtures/lightning-fake-hosts/codex`, labelled `pipeline-only` like the
existing fixtures, so CI exercises the Codex path without a Codex install, a model or
quota. Because `parse_codex` reports no credential source, a fake Codex rollout
completes only through a key-source value that exists solely in the fake-host path (set
by the fixture, accepted only when `fake_hosts` is true, recorded with the
`pipeline-only` label) and never in a real run; the production verdict of REQ-007 is not
weakened, and a test runs the real verdict on the same stream to show it ends as
`route-unverified`.

- **SC-010:** Given the fixture, when `lightning run --fake-hosts` names `codex`, then
  the pipeline completes through the fake-only source, every record is labelled
  `pipeline-only`, no network or provider access occurs; and given the same stream with
  `fake_hosts` false, then the verdict is `route-unverified`.

**REQ-011 Required hosts unchanged.** `REQUIRED_HOSTS` MUST NOT change from
`("claude-code",)` (OD-1). Codex rows appear in `report` (rates and Wilson intervals) as
a non-binding host: the H1 outcome, the SPEC-049 registration and the inputs of the
SPEC-073 promotion decision are byte-identical with and without Codex rows. Only a
later amendment, backed by Codex measurements, can make Codex binding.

- **SC-011:** Given a fake-host report (REQ-010) that contains `claude-code` and `codex`
  rows, and a second report in which Codex is a declared limit, when
  `h1_outcome` and the SPEC-049 pair are computed, then they equal those computed from
  the `claude-code` rows alone, and `requiredHosts` is `["claude-code"]`.

**REQ-012 Consent and traces unchanged.** A Codex host run needs the same setup consent
as any host run (`consent-required` otherwise). No consent kind, bypass or default is
added, and Codex transcripts enter traces only through the SPEC-074 opt-in sources.

- **SC-012:** Given a real-host (not `--fake-hosts`, which skips the gate at
  `lightning_cli.py:299-300`) Codex run invocation without setup consent, when it is
  invoked, then it is refused with `consent-required`; and given consent for the laboratory only, then no
  content-bearing trace of Codex is written.

**REQ-013 Export terms gate stays closed.** The export terms-record check accepts
`codex` as a host value (it follows `lightning-run`), and nothing more. The gate stays
closed (SPEC-075 OD-1 is open): Codex model output MUST NOT export without a recorded
owner decision, no real terms record is committed, and no text says that any provider
permits training.

- **SC-013:** Given a Codex rollout and no terms record, when export runs, then it
  refuses with `terms-gate-missing`; and given a synthetic terms record naming host
  `codex` in a temporary directory, then the record shape validates and no real provider
  is named.

**REQ-014 Codex runs on the development set only.** The runner allows a `codex` host
only for the prompt set `development` and refuses it before launch for every other
prompt set: the SPEC-069 `held-out` set (spent), the SPEC-078 and SPEC-079 splits
(`v2-feedback`, `v2-validation`, `v2-test`, `v3-test`, `v4-test` and their freezes) and any set added later. This is an allow-list, so a new set is refused by default. A fresh
preregistered split is SPEC-089's. The refusal reuses an existing code or adds one to the
closed vocabulary of SPEC-071's refusal contract in the code phase.

- **SC-014:** Given a plan or run that names `codex` for each of `held-out`, `v2-feedback`,
  `v2-validation`, `v2-test`, `v3-test` and `v4-test`, when it is invoked, then each is
  refused before launch; and given `development`, then it is planned.

**REQ-015 No execution authorization.** This specification grants no authority to run
Codex. `executionAuthorization` stays `false` in every plan output, and the first real
Codex rollout needs the owner's explicit yes at T011.

- **SC-015:** Given `lightning run --dry-run` naming `codex`, when it prints the plan,
  then `executionAuthorization` is `false` and nothing is launched.

**REQ-016 No other record edited.** This specification's change set MUST NOT edit
SPEC-087, SPEC-089, a closed specification, the SPEC-069 or SPEC-072 drivers and
scripts, recorded evidence, the Constitution or its replica. Amendments to SPEC-087 are
proposed in the plan, not made.

- **SC-016:** Given the change set, when its changed paths are listed, then none is
  under `specs/` other than `specs/088-lightning-codex-host/`, none is a `scripts/`
  driver of SPEC-069 to SPEC-073, none is recorded evidence, and none is
  `CONSTITUTION.md` or its replica.

**REQ-017 No claim for an unmeasured host.** Published text of this change MUST NOT state a
Codex result. It says that the host path exists, that the route is `route-unverified`
until evidence is recorded, and that nothing is measured.

- **SC-017:** Given the changed documentation and report text, when inspected, then no
  sentence claims a Codex result, and `docs/tooling/LIGHTNING.md` states the route status
  and the declared limit.

## Non-functional requirements

- Deterministic and additive: no existing record, digest or default changes (REQ-005,
  REQ-006).
- No new dependency: standard library and the existing runner (REQ-002, REQ-003).
- Cost: EUR 0 on the subscription route; no paid API route (REQ-007).
- Reviewable: the host-site inventory and the membership table are stated in the plan
  and compared by tests (REQ-002, REQ-003).
- Performance and size limits: no requirement applies beyond one more host entry in
  constant tables.

## Security and privacy

- No credential is read from a file, written, logged or placed in a record; a Codex
  credential value, if T003 shows one is needed, lives only in the child environment and
  the secret scanner (REQ-007).
- No provider key, paid route or `*_API_KEY` is accepted (REQ-007).
- The Codex profile is disposable and under the existing OS sandbox, probe and leak
  guard (REQ-007, REQ-010).
- No content-bearing trace is written without SPEC-074 consent (REQ-012).
- No dataset leaves the machine and the terms gate stays closed (REQ-013).
- A capability flag is not an authorization (SPEC-087 REQ-014; REQ-015).

## Terminology

- **Rollout host:** a host that runs the rollouts of a prompt set in a disposable
  profile. Registered through `lightning-run` (REQ-002).
- **Optimizer host:** the host that calls a model to rewrite guidance (APO, GEPA).
  Registered through `lightning-optimizer-config`, whose members stay `claude-code` and `opencode`; only `claude-code` passes `SandboxedHost` (REQ-004).
- **Declared limit:** a host that cannot run in this environment or whose route is not
  verified; reported, never replaced by a manual step (REQ-008).
- **Required host:** a host in `REQUIRED_HOSTS`, whose verdict decides H1 and
  promotion. Only `claude-code` (REQ-011).
- **Capability, capability query, canonical identifier, feature-owned table:** as in
  SPEC-087.
- **Route (subscription):** the credential path a host uses; `route-unverified` means
  no accepted evidence of a subscription credential source (REQ-007).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Engineering, not a research protocol; no hypothesis.

- **Domain:** the Lightning host path in `agent_braid/lightning_*.py` and the registry
  at the recorded commit; one Codex build, as observed by T003.
- **Observation contract:** the differential record of `claude-code` and `opencode`
  outputs taken from `develop` before the change (T002), and Codex stream observations
  recorded by T003; equality of bytes and sets after the change.
- **Execution contract:** none until T011. The change runs fake hosts only; any real
  Codex rollout is a separate, owner-authorized task.
- **Limits:** equality shows `claude-code` and `opencode` are unchanged at one commit.
  A working fake host or parser check shows the path exists, not that Codex follows the
  tool contract, meets D4 or is on a subscription route. `parse_codex` is verified only
  for the observed Codex build and event shapes.
- **Compatibility:** additive; defaults and stored data unchanged; a pre-change reader
  refuses Codex records. Rollback removes `codex` from the capability and tables and
  deletes the fixture; Codex records already written would stop being readable.

## Owner decisions

The owner answered OD-1 to OD-4 on 2026-11-27 through AskUserQuestion prompts in the
author session (Spanish, with options, examples, risks, how to undo and a
recommendation). The first prompt asked the schema question together with three others;
the owner asked for a clearer explanation of the others, which were re-asked with
examples, and the answers below are from the final answers. The owner's stated concern:
other hosts must not lose functionality or precision; REQ-005 and REQ-011 encode it.

- **OD-1 Required hosts (decided).** Codex is reported and non-binding;
  `REQUIRED_HOSTS` does not change (REQ-011). Rejected: make Codex binding now, which
  would change closed SPEC-072 and SPEC-073 criteria with no Codex measurement in
  Lightning. Undo: a later amendment with Codex evidence.
- **OD-2 Optimizer (decided).** Not for now; Codex runs rollouts only (REQ-004).
  Rejected: Codex as optimizer, which needs its own sandbox and route verification.
- **OD-3 Route evidence (decided).** Observe first: Codex is accepted only with
  host-reported or reviewed observed evidence of a subscription source; until then it
  ends as `route-unverified`, a declared limit, like OpenCode (REQ-007, REQ-008).
  Rejected: accept the profile's ChatGPT sign-in as proof, a looser bar than Claude's.
- **OD-4 Schema (decided).** Widen `v0.1` additively (REQ-006). Rejected: a new `v0.2`,
  which collides with the name SPEC-076 reserves for `local-vllm` and changes readers,
  store and export.
- **OD-5 Development-set allow-list (open, author proposal).** REQ-014 allows Codex
  only on `development` so that no spent or frozen set is consumed before SPEC-089's
  fresh split. The owner has not answered it. Options: refuse (proposed), or leave the
  runner permissive and rely on the owner's run authorization. Owner confirms in T001.
- **OD-6 Real Codex run (open, later).** The first real Codex rollout, its credential
  carrier and its Codex build are decided at T003 and T011 on observed evidence. The
  owner authorizes the run at T011.

Design choices that follow from behavior preservation, not owner decisions: (a) the
default rollout hosts stay `claude-code` and `opencode` (REQ-005); (b) the optimizer
enum keeps today's two members, so `lightning-optimizer-config` and
`lightning-default-rollout` are capabilities that name existing sets (REQ-004,
REQ-005); (c) `codex` is appended last in `lightning-run` so existing observed orders
keep their prefix (REQ-002). Each is checked by the T002 differential record. Decision
labels OD-1 to OD-6 are this specification's own and are not the "OD-2" prose of
`lightning_runner.py`, which is SPEC-071's.

## Risks and assumptions

- Risk: adding `codex` to one shared tuple makes it a default rollout host and an
  optimizer host (REQ-004, REQ-005; T004, T005).
- Risk: the Codex stream reports no credential source, so Codex stays a declared limit
  and no rollout runs (REQ-007, REQ-008; T003).
- Risk: `parse_codex` or the tool prefix is wrong for a Codex build and a valid run is
  scored as invalid or the reverse (REQ-009; T003, T007).
- Risk: a Codex model identity is not reported and the record names a guess (REQ-009;
  T003).
- Risk: SPEC-076 (deferred) also adds a host (`local-vllm`) to the schema host enums;
  if it lands first or later, T005 and its additive widening must be reconciled with it
  (REQ-006; T005).
- Risk: SPEC-087's code is not merged, so this change adds its own list (REQ-002;
  dependency in T002).
- Risk: widening the host enum changes accepted-host text that a test or document quotes
  (REQ-005; T005).
- Risk: the single-host comparisons of the inventory are missed by SPEC-087's collection
  scan (REQ-002; plan, proposed amendment).
- Assumption: the SPEC-069 driver (`HOSTS`, `KEY_SPECS`, `prompt_argv`, `install_plugin`,
  `build_host_env`) works for Codex unchanged (REQ-010; T003, T006).
- Assumption: the SPEC-071 consent gate is host-agnostic (REQ-012; T002).
- Assumption: Codex CLI 0.162.0 or newer is the supported stream shape
  (`docs/tooling/HOST_EVENTS.md`); the build used for T003 is recorded (REQ-009).

## Exit criteria

Verification is complete when the obtained evidence listed in
[the validation plan](validation-plan.md) exists for procedures 001 to 017, which map to
SC-001 to SC-017 and to the tasks in [tasks.md](tasks.md) that name them, with the
before and after differential records of T002 and T010 attached. Passing checks are not
approval, and nothing here measures Codex.

## Open questions

- OD-5: confirm the held-out guard (REQ-014) or drop it. Owner: the founder, at T001.
- OD-6: authorize, or decline, the first real Codex rollout, after T003 evidence.
  Owner: the founder, at T011.
- Proposed amendment to SPEC-087 (not made here): extend its T002 scan to single-host
  comparisons and to `host_name == 'opencode'`-style branches, and record the
  `lightning-optimizer-config` and `lightning-default-rollout` capabilities. Owner: the founder, at SPEC-087 T001.

## Dependencies

- Requires SPEC-087 code (registry module, capability queries, key-set and guard tests;
  its T003 to T007). Capability names follow the name merged there.
- Read, not edited: SPEC-069 (driver, held-out evidence), SPEC-070, SPEC-071 (refusal
  contract), SPEC-072 (Amendment 1), SPEC-073, SPEC-074, SPEC-075, SPEC-078, SPEC-079.
- Consumers: SPEC-089 (validity measurement on Codex and OpenCode) depends on this
  specification and on SPEC-079 T010 ([#1513](https://github.com/jayanez/agent-braid/issues/1513)).

## References

- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md).
- [Plan](plan.md), [tasks](tasks.md), [validation plan](validation-plan.md).
- [Lightning documentation](../../docs/tooling/LIGHTNING.md),
  [host events](../../docs/tooling/HOST_EVENTS.md),
  [native plugins](../../docs/tooling/NATIVE_PLUGINS.md).
- [SPEC-071 refusal contract](../071-lightning-rollouts-reward/contracts/refusals.md).
