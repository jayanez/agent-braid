# Linux experiment execution

Agent Braid uses a hybrid route with no additional infrastructure purchase:
standard hosted Linux x64 for **public owned fixtures**, and existing local
Linux environments for private preparation. This runbook registers no persistent
runner, changes no private repository workflow and makes no model API calls.

## Public hosted jobs

| Workflow | Observation |
| --- | --- |
| `m35-synthetic-reproduction.yml` | Synthetic capture/audit costs and journal, recovery, pair-enumeration, filtered-lab and aggregate-seal controls. Zero real admitted pairs. |
| `m4-reproduction.yml` | Fresh-process bounded serial private-result fixture tests. |
| `m4-alpha-reproduction.yml` | Core/policy/scheduler/stdio-peer fixture tests plus the reusable M3.5 synthetic job. Optional descriptive M4 cost profiling and comparison. |

These manual workflows require a full lowercase 40-character public candidate
SHA, verify a clean checkout at that SHA and assert Linux `x86_64`. They pin
Ubuntu 24.04, Python 3.12 and official actions by full SHA. Python patch, Git,
architecture and runner image versions are recorded rather than assumed.
Checkout uses `persist-credentials: false`; no secrets are passed into the
experiments or the reusable job. Dependency installation still runs, with
`--no-cache-dir`, and the complete ordinary PR/post-merge `validate` gate remains
mandatory. Its existing dependency caches are unchanged.

Standard public repository runner minutes are free. Larger runners are charged
even for public repositories. Logs and job summaries do not count toward artifact
storage, so these experiment jobs upload no artifacts or caches. See
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Public logs contain only public fixtures, their test output, hashes and limits.
Never send private source content, journals, permission records, registration
payloads, participant identities, keys or model-host transcripts to these jobs.

The M3.5 workflow supports both manual dispatch and `workflow_call`.
`m4-alpha-reproduction.yml` invokes its local workflow path, which resolves at
the caller workflow's commit. An already registered manual workflow can therefore
exercise a published candidate branch before merge. The workflow branch and
`candidate_commit` are separate identities; preserve both in the run record.

From a clean independent checkout, after the publication/dispatch action is
authorized, substitute the actual published branch:

```sh
BRAID_CANDIDATE=$(git rev-parse HEAD)
test -z "$(git status --porcelain)"
gh workflow run m4-alpha-reproduction.yml --repo jayanez/agent-braid \
  --ref '<published candidate branch>' \
  --raw-field candidate_commit="$BRAID_CANDIDATE"
```

Cost profiling is opt-in (`profile_cost: false` by default). To compare two frozen
public commits on the same Linux host, add these fields to that dispatch:

```sh
  --field profile_cost=true \
  --raw-field baseline_commit='<full public baseline SHA>'
```

The baseline is cloned from the already fetched public checkout into
`RUNNER_TEMP` with `--no-local`; no hardlinks or credentials are copied, and no
private repository is fetched. It requires the exact baseline SHA and a clean
tree, with no floating-ref fallback. The candidate's cost profiler runs in a
separate interpreter for each checkout and compares only compatible frozen
measurement inputs. See the [M4 measurement protocol](../../specs/021-m4-alpha-runtime/measurement-protocol.md);
the optional sidecar records diagnostic phases separately.
An improvement remains descriptive; a null or slower outcome is retained and
does not alter the historical G4 NO-GO.

Inspect the actual run and job, then retain the public log outside the checkout:

```sh
gh run view '<run ID>' --repo jayanez/agent-braid
gh run view '<run ID>' --repo jayanez/agent-braid --log > /owned/evidence/linux-run.log
```

Every record appears between `BEGIN_PUBLIC_EXPERIMENT_JSON` and
`END_PUBLIC_EXPERIMENT_JSON`, with its SHA-256. Available raw test logs are also
printed with their bound digest. Workflow commands are disabled while displaying
record-controlled text. Short job summaries expose the candidate, result,
platform, counts and limits. Preserve the run ID/attempt, caller workflow SHA,
candidate SHA and downloaded raw log. This temporary transport is not a permanent
evidence archive or independent external validation.

## Current e66 core and protocol reproduction

The completed [e66 Linux reproduction](https://github.com/jayanez/agent-braid/actions/runs/37778187088)
ran 68 core, policy, scheduler and deterministic stdio-protocol tests in a fresh
process on Linux x86_64, Python 3.12.14 and Git 2.55.0. All tests passed, with no
skips or timeout. The public record binds 80 candidate inputs and the run's public
test transcript. A separate read-only check matched those 80 hashes to candidate
objects without rerunning tests. See the [e66 Linux evidence record](../../specs/021-m4-alpha-runtime/evidence/current-linux-core-protocol-e66f9a1.md)
for provenance and limits.

This run covers the Linux core/protocol slice only. It does not exercise Codex or
Claude host adapters, measure utility or cost, or close the SPEC-021 portability
row. Current Codex Darwin host and core-suite evidence are recorded separately;
current Claude host evidence remains pending.

## Existing local Linux environment

Use an independent full clone with the reviewed public history restored and a
passing [Spec Kit preflight](SPEC_KIT.md#shared-git-object-store-recovery).
The existing `agent-braid-t013:py312-git247-v1` image is **Linux ARM64**, not hosted
x64 parity. Verify its image ID and architecture before recording observations:

```sh
docker image inspect agent-braid-t013:py312-git247-v1 \
  --format 'image={{.Id}} platform={{.Os}}/{{.Architecture}}'
```

The existing resource-limited wrapper runs local repository checks or the bounded
T013 fixture without network access:

```sh
scripts/docker/t013/run-validation.sh quick
scripts/docker/t013/run-validation.sh t013 /owned/evidence/t013-linux-arm64
```

To reproduce M3.5 synthetic preparation in the same existing image, with a
read-only checkout and evidence outside it:

```sh
BRAID_CHECKOUT=$(git rev-parse --show-toplevel)
BRAID_EVIDENCE=$(mktemp -d /tmp/braid-m35-evidence.XXXXXX)
docker run --rm --network=none --read-only \
  --memory=2g --cpus=2 --pids-limit=512 \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
  --mount "type=bind,src=$BRAID_CHECKOUT,dst=/workspace,readonly" \
  --mount "type=bind,src=$BRAID_EVIDENCE,dst=/evidence" \
  --workdir /workspace \
  --env GIT_CONFIG_COUNT=1 --env GIT_CONFIG_KEY_0=safe.directory \
  --env GIT_CONFIG_VALUE_0=/workspace --env GIT_CONFIG_GLOBAL=/dev/null \
  --env GIT_CONFIG_NOSYSTEM=1 --env GIT_OPTIONAL_LOCKS=0 \
  --env PYTHONDONTWRITEBYTECODE=1 \
  agent-braid-t013:py312-git247-v1 \
  python -m scripts.reproduce_m35_synthetic --output /evidence/reproduction.json
```

No image build, package upgrade or runner registration is implied by these
commands. If the image is absent, report that prerequisite rather than installing
a new execution service. Measurements describe the architecture and resource
profile actually used.

## Private sources and remaining gates

Kinetiq and SmartNotes keep their application CI and data private. Linux validation
of their reviewed decision snapshots can use local isolated tooling; results and
logs stay outside every public Git checkout. With a clean **private** source
checkout at a reviewed branch SHA, an already approved branch allowlist can be
checked without publishing a lab branch:

```sh
python -m scripts.m35_lab_export /private/source-checkout \
  /private/reviewed-lab-export-allowlist.json develop \
  /private/new-filtered-snapshot --expected-repo '<owner/source-repository>'
```

This checks the allowlisted blob pins and ordinary text files and writes only a
new local filtered snapshot. It does not scan for every secret, establish rights,
review changed blobs, mirror application code or publish anything. A pin mismatch
stops export until the changed content is reviewed. Keep production and
experimental refs separate; use the existing [lab sync runbook](../../specs/019-native-predictor/lab-sync-cli-runbook.md)
for any separately authorized remote synchronization.

For an actual prospective M3.5 window, [ADR 0018](../adr/0018-private-source-sidecar-and-disposable-labs.md)
still requires source-owner/participant-rights/privacy review and successful
remote registration at least **24 hours before** the unaltered 14-day UTC window.
The registration must run on the private audit repository with an actual runner
and executed steps, separately for each family. A runnerless or billing-blocked
job is **not executed**; local Docker, a public synthetic run and filtered lab
snapshots cannot satisfy that registration gate. Neither candidate family alone
nor their combination meets the five-family evaluation threshold. Follow the
[prospective pilot](../../specs/019-native-predictor/prospective-pilot.md) before
any real capture, labeling, fitting or evaluation.

Passing these software checks supplies bounded tooling evidence. Human protocol
approval, source completeness, predictor utility, real host portability,
independent external validation and founder milestone acceptance keep their
separate records and decisions.
