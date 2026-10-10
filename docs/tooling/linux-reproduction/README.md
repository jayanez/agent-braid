# Linux x86_64 installed-package reproduction recipe

**State: standalone recipe with an explicit optional AMD64 emulation mode.** This procedure
is for the installed `agent-braid` wheel, its five packaged skills, and the
optional MCP 2.3.0 stdio surface. It does not exercise a native AI host, call a
provider, run full registration, or satisfy SPEC-044 T004. Keep any future Linux
receipt separate from macOS evidence.

## Frozen target

The target is CPython 3.13.11 on Linux x86_64. The official
`python:3.13.11-slim-bookworm` registry tag was inspected on 2026-10-10 with
`docker manifest inspect --verbose`; exactly one descriptor matched
`os=linux`, `architecture=amd64`:

```text
sha256:ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe
```

Use the platform-specific digest in any future Dockerfile:

```dockerfile
FROM --platform=linux/amd64 python:3.13.11-slim-bookworm@sha256:ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe
```

Do not substitute the moving tag, the multi-platform index digest, an ARM64
child, or a provenance-only descriptor. A later run should repeat a public,
read-only manifest inspection and stop if the exact tag no longer resolves to
one `linux/amd64` descriptor with this digest. Docker documents that
[`manifest inspect --verbose`](https://docs.docker.com/reference/cli/docker/manifest/inspect/)
includes the digest and platform.

## Inputs and fail-closed checks

The reproducibility lock is
[`mcp-2.3.0-cp313-linux-amd64.lock.txt`](../reproducibility/mcp-2.3.0-cp313-linux-amd64.lock.txt);
its JSON inventory is
[`mcp-2.3.0-cp313-linux-amd64.manifest.json`](../reproducibility/mcp-2.3.0-cp313-linux-amd64.manifest.json).
The companion Linux wheelhouse is supplied outside the checkout at
`five-task-delivery-v1/wheelhouses/linux-amd64/`. The frozen candidate wheel,
its SHA-256, and the verifier's own SHA-256 must be recorded in the run receipt
before any installation.

Before running the probe, require all of the following:

1. The candidate wheel is bound to an exact reviewed source commit in the
   bundle record. The Linux runner itself does not need a source checkout.
2. The default executing host reports `Linux` and `x86_64`. Under the owner-approved
   autonomous completion plan, standalone SPEC-042 controls may use an ARM64
   macOS/Linux launch host with **`--allow-amd64-emulation` explicitly supplied**.
   The pinned image and in-container verifier must still report Linux x86_64.
   The receipt records launch-host/daemon identity and emulation; this is not
   native hardware, performance, or registered SPEC-044/T004 evidence.
3. The candidate wheel hash matches the independently frozen expected SHA-256.
4. The lock manifest and every wheelhouse file match their recorded hashes and
   target metadata. Do not fetch a replacement or resolve dependencies online.
5. The verifier is the separately reviewed installed-package probe and its hash
   matches the frozen value. A missing or changed artifact is a hard stop.

The target lock covers the `tooling` extra and exact dependency closure with
hashes. Before transferring inputs to Linux, stage a standalone bundle with
this layout; no source checkout is mounted or imported by the probe:

```text
input-bundle/
├── agent_braid-0.1.0a1-py3-none-any.whl
├── verify_installed_tooling.py
├── reproducibility/
│   ├── mcp-2.3.0-cp313-linux-amd64.manifest.json
│   └── mcp-2.3.0-cp313-linux-amd64.lock.txt
└── wheelhouse/
    └── <the exact 28 locked wheels>
```

Keep the wheel's valid distribution filename when copying it; the runner passes
that exact basename to pip. Copy the frozen wheel and probe, the two tracked
reproducibility files, and only the matching files from
`wheelhouses/linux-amd64/`. Freeze the candidate, probe, manifest, lock,
wheelhouse inventory, and standalone launcher SHA-256 values independently
before transfer. Copy `docs/tooling/linux-reproduction/run.py` to the transfer
location as `run_linux_reproduction.py`; keep its frozen hash with the bundle
record. The launcher and probe are standalone Python scripts and do not require
the source checkout at execution time. Do not modify inputs after freezing.
The runner verifies its own hash, candidate, probe, manifest, lock, and wheel
bytes; target metadata; exact wheel roster; and wheelhouse inventory before it
starts a container.

On a native Linux x86_64 machine with the exact base image already present in
the local Docker store, set the frozen values from that reviewed bundle receipt
and run a prepare-only check:

```sh
python3 /path/to/run_linux_reproduction.py \
  --input-dir /path/to/input-bundle \
  --output-dir /path/to/new-evidence-directory \
  --candidate-sha256 "$CANDIDATE_SHA256" \
  --probe-sha256 "$PROBE_SHA256" \
  --manifest-sha256 "$MANIFEST_SHA256" \
  --wheelhouse-sha256 "$WHEELHOUSE_SHA256" \
  --launcher-sha256 "$LAUNCHER_SHA256"
```

The prepare-only command checks the default native launch host and daemon,
local Unix endpoint and pinned image metadata/digest without starting a container.
An ARM64 launch host or daemon requires the explicit emulation opt-in described
below. To execute the offline probe,
repeat the same command with `--execute`. It uses the local image only
([`--pull=never`](https://docs.docker.com/reference/cli/docker/container/run/#options)),
pins `linux/amd64`, disables container networking, makes the container root
filesystem read-only, mounts all inputs read-only, and writes the receipt only
under the new output directory. If the image is missing, any
hash differs, or an ARM64 launch host/daemon lacks the explicit emulation
opt-in, it stops before starting the probe. Stage/import the pinned image separately if needed; the runner never
pulls or builds it.

After execution starts, the launcher writes a private mode-0600 receipt before
interpreting the probe's JSON output. It records the exact child argv, start/end
times, timeout and exit status, observed stdout/stderr byte counts and SHA-256
values, plus separate raw trace files bounded to 64 KiB each. The evidence
directory is mode 0700. A zero exit with malformed or unexpected JSON therefore
remains diagnosable without exposing raw traces to terminal output.

## Execution boundary and expected record

The current workstation's Docker daemon is ARM64, so it cannot produce the
required Linux x86_64 observation. No image pull, container launch, installed
probe, or Linux result is part of this prepared record.

Retain the candidate commit, wheel, verifier and launcher hashes, lock-manifest
hash, wheelhouse inventory hash, base digest, host and Python versions, installed
distribution/SDK versions, skill-bundle and asset-roster hashes, protocol
control outcomes, exit status, and any failure/timeout. Record missing prerequisites as not executed;
never turn them into passes or failures of the package. This recipe supplies
preparation only and makes no host-acceptance, provider, registration, cohort,
utility, or scientific claim.

## Explicit emulation boundary

On an ARM64 macOS/Linux launch host, add `--allow-amd64-emulation` to the same
hash-bound prepare and execute commands. Default execution still refuses that
host. Every launch observes Docker daemon OS/architecture and retains it separately
from the pinned AMD64 image and in-container probe target. The CLI launch host and daemon execution mode are classified separately; an
ARM64 launch host alone does not prove emulation. Only a local Unix Docker
endpoint is admitted; remote TCP/SSH contexts are refused. Unknown/wrong daemon
platforms refuse; network, image digest, lock/wheel hashes, output isolation and
container confinement remain mandatory. Actual results are indexed in
[the autonomous delivery register](../AUTONOMOUS_COMPLETION.md); the older
preparation record below is historical and is not itself an execution receipt.
