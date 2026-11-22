# ADR 0045: Hybrid harness evaluation substrate (Harbor containers plus a macOS shadow)

- **Status:** Proposed (2026-11-22). Not accepted, and it implements, installs and runs
  nothing. The owner chose this direction on 2026-11-22 (F2 in the
  [harnessing benchmark](../strategy/HARNESSING_BENCHMARK.md)). The founder accepts or
  rejects it in the SPEC-084 T001 review.
- **Date:** 2026-11-22
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 0, 4–7, 12–15, 19, 20, 24
- **Specification:** [SPEC-084](../../specs/084-harbor-evaluation-substrate/spec.md)
- **Relation to ADR 0035:** narrows the role of [ADR 0035](0035-native-claude-laboratory-containment.md). Its mechanism stays as accepted, but it is no longer the only way to run native evaluation. It becomes the macOS fidelity shadow.

## Context

Today every host needs its own qualified native laboratory before it can be evaluated
natively:

- **Claude:** SPEC-065. Its qualification is pinned to an OS build and a CLI version,
  and a macOS update voided it once.
- **Codex:** refused.
- **OpenCode, Pi and ThinkRail:** nothing.

SPEC-049 T014 ran 15 units on one lineage and was inconclusive under D3.

The field separates two kinds of isolation:

- **For evaluation:** one container per trial, from a pinned image with a fresh
  filesystem. Harbor, Inspect and SWE-bench all work this way.
- **For daily use:** the host's own sandbox.

Harbor already runs claude-code, codex, opencode and pi as black-box adapters. It
offers per-phase network policies, `-k` attempts and ATIF trajectories. Terminal-Bench
2.0 runs on it with at least 5 trials per pair and task QA.

## Decision (proposed)

1. **Primary substrate.** Agent Braid runs cross-host harness evaluations as Harbor
   jobs. Each job uses one container per trial, a pinned agent version and image
   digest, a recorded resource configuration, and a network policy per phase. The
   policies are: install public, run on an allowlist limited to the provider API, and
   the verifier offline.
2. **Agent Braid keeps its own layer.** Registration, the statistics of SPEC-083 and
   SPEC-049, the promotion pointers of SPEC-085, and human promotion all stay in
   Agent Braid. Harbor's default metric (a mean, with missing rewards counted as 0) is
   never used as a verdict. ATIF trajectories are ingested into the Agent Braid
   evidence format.
3. **macOS shadow.** A small, registered subset runs on the real macOS host under ADR
   0035 containment. It checks fidelity to the user's actual install and adds no
   statistical power. A disagreement between the shadow and the container results
   blocks promotion until it is explained.
4. **Gates before first use.** SPEC-084 must establish each of these before Harbor is
   used:
   - subscription authentication inside containers works with no secret copied into
     an image;
   - Docker or Podman is available on the operator machine;
   - cash spend stays at EUR 0 and quota stops are respected;
   - the image and agent versions are pinned by digest.

   If any gate fails, the substrate is recorded as infeasible, and evaluation stays
   on the current laboratory path.

## Alternatives considered

- **Keep a qualified laboratory per host.** Gives the highest fidelity to the real
  install. But it costs a separate containment and qualification for every host, and
  it breaks on every OS or CLI update. Rejected as the primary substrate.
- **Harbor only.** Simplest. It loses fidelity to macOS and to the user's actual
  install. Rejected; the shadow keeps that check.
- **Inspect AI.** Has stronger built-in statistics and model-call proxying. It does
  not cover Pi, and its adapter catalogue is narrower. Kept as an alternative if
  Harbor fails a gate.

## Consequences

- **Positive:**
  - Every target host can be evaluated through one substrate.
  - Trials get fresh filesystems and pinned images.
  - Infrastructure errors become observable apart from agent failures.
- **Negative:**
  - New dependencies: Harbor, a container runtime and images.
  - The test environment is Linux rather than macOS.
  - Running subscription auth inside containers is an open risk.
- **Compatibility:** SPEC-065 artifacts and the ADR 0035 mechanism are unchanged.
- **Security:**
  - Containers become a new trust boundary.
  - Credentials must never enter an image.
  - Model traffic leaves only through the policy allowlist.
- **Research:** whether results from containers and the shadow agree is itself a
  hypothesis that SPEC-084 tests.

## Validation

SPEC-084 plans:
- the four feasibility gates above;
- one reproducible job, rerun from its exported config;
- a shadow/container agreement check on a registered subset;
- negative controls: blocked network, a missing credential, a stale image.

None has run.

## References

- [Harbor](https://docs.harborframework.com/),
  [network policies](https://docs.harborframework.com/tasks/network-policies.md),
  [Terminal-Bench 2.0](https://arxiv.org/html/2601.11868v1)
- [Inspect agent bridge](https://inspect.aisi.org.uk/agent-bridge.html)
- [Anthropic, infrastructure noise](https://www.anthropic.com/research/infrastructure-noise)
- [ADR 0035](0035-native-claude-laboratory-containment.md),
  [harnessing benchmark](../strategy/HARNESSING_BENCHMARK.md)
