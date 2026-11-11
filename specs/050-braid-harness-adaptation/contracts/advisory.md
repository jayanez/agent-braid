# Braid Harness advisory contract v0.1 (product-facing, read-only)

Status: **implemented offline, advisory only**, SPEC-050/T010. Wire identity
`braid-harness-advisory/v0.1`. It extends no existing public schema
(`agent-braid-plugin/v0.1`, AIM, runtime grants, the fixed-patch operation language, the
laboratory `harness` command) and grants no permission. It is the C11 view promised by
[interface.md](interface.md) section 5: a read-only view over `ComponentProfile`
(`braid-harness-profile/v0.1`) and the SPEC-049 registry, with no record of its own.

## 1. Surface and adoption

- Opt-in CLI only: `python -m agent_braid.harness_advisory <command>`, implemented in
  `agent_braid/harness_advisory.py`. The laboratory `harness` command and the top-level
  `agent-braid` command are unchanged: the top-level help is pinned by the laboratory CLI
  tests, so a top-level `agent-braid harness-advisory` alias needs its own reviewed change.
- The plugin, the MCP tool surface, tool descriptions, skills and manifests are **unchanged**.
  The analysis-only plugin/MCP contracts do not silently gain these views. Exposing them
  there needs its own versioned plugin/MCP contract and review after the in-flight plugin
  milestone, recorded as a separate artifact.
- Any execution surface (running a profile, installing, migrating, enabling, native
  dispatch) needs separate explicit adoption: a new contract, a qualified effect profile
  and fresh operator authority. Nothing here reopens a blocked class in interface.md
  section 8.

## 2. Commands

All commands require `--workspace DIR` (an existing directory) and accept
`--contract-version` (default and only value `v0.1`).

| Command | Reads | Output (`result`) |
|---|---|---|
| `capabilities` | nothing | contract versions, classes C1 to C8 with derived admission and blocker, host rows, provider limitations |
| `profile-inventory` | one profile (`--profile`, optional trusted `--sha256`) | identity, files, admission, host support, `authenticity` |
| `profile-diff` | two profiles (`--base`, `--candidate`; `authenticity` is always `unverified`) | added, removed, modified files and changed metadata fields |
| `status` | one SPEC-049 registry (`--registry`) | active, pending, previous, decisions, journal summary |
| `evidence` | one spec directory (`--spec-dir`) | evidence file inventory against tasks, with anomalies |

## 3. Envelope

Success: `{"contract":"braid-harness-advisory/v0.1","status":"ok","advisory":true,
"executionAuthorization":false,"workspace":{"bound":true,"id":<sha256 of resolved path>},
"result":{...}}`, exit 0.

Refusal: `{"contract","status":"refused","reason":<code>,"advisory":true,
"executionAuthorization":false}`, exit 2. The code matches `[a-z][a-z-]{0,47}`; anything
else collapses to `refused`. Errors never echo paths, file contents or exception text.
Any other exception is an internal bug, not a refusal. Argument-usage errors exit 2 with usage on stderr and nothing on stdout.

## 4. Binding and bounds

- Workspace binding is explicit and mandatory. Every input is resolved (links followed) and
  must lie inside the resolved workspace, else `outside-workspace`. Inputs are bounded
  regular files (`MAX_RECORD_BYTES`); links are resolved first and the resolved target must lie inside the workspace; the evidence walk
  keeps the laboratory bounds (256 files, 1024 entries, depth 4).
- Residual limits: a hard link inside the workspace to an outside file is read (hash and size are reported); success output names files and the spec directory and `workspace.id` is an unsalted identifier, not a secret; `status` echoes registry content up to `MAX_RECORD_BYTES`. A path check and the later open are not atomic; a hostile same-UID
  process can swap a directory between them, so the binding is best-effort against a quiescent workspace. This is the same-UID threat that
  interface.md section 7 assigns to qualification, not to this CLI.
- The D2 quota and time caps are unchanged and not consumed: the CLI starts no model,
  child process or network connection and spends nothing. Native effects are refused by
  construction (effect class E0 to E2 reads only).

## 5. Versioning, compatibility and migration

- v0.1 is the only version, so migration is currently a refusal path (`unsupported-version`), not a conversion.
- A reader supports exactly the listed versions. An unlisted or newer `--contract-version`
  (including a later minor) refuses `unsupported-version`; there is no negotiation.
- A profile whose `format` is not `braid-harness-profile/v0.1` refuses
  `unsupported-version`. The CLI never rewrites or upgrades a profile.
- Migration policy: a patch revision changes no field. A minor revision may only add
  optional `result` fields and a new command; old readers keep working and new commands are
  absent for them. Removing or retyping a field, or relaxing the envelope, needs `v0.2`
  with a change log below and a documented migration. The previous version stays supported
  for at least one released alpha after its successor. Lifecycle migration of profiles
  (T011) is separate and not implemented here.

## 6. Provider limitations

- Claude Code build 2.1.292 is observed; adapter and native wiring are tested with doubles
  only, so no class is qualified. Codex CLI is not installed and is refused.
- Hook, plugin and delegated-role schemas per host build are not inventoried; C6 to C8 stay
  blocked. A feature on one host implies nothing for the other.
- A matched `--sha256` binds bytes, not authenticity, rights or containment. Advice is not
  qualification, activation or product acceptance; human and native decisions need their
  own records.
- Profiles that select a model, effort or route need the approved list and its trusted
  hash; this CLI does not accept it and refuses such profiles under `--sha256`.

## 7. Change log

| Version | Date | Change |
|---|---|---|
| v0.1 | 2026-11-11 | First read-only advisory contract (T010). |
