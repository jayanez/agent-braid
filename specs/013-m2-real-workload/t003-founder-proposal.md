# T003 — proposed separate founder decision for the M2 real corpus

**Status:** proposed; founder acceptance pending. This document does not authorize repository-code execution, implement the container-command stage, run the ADR 0015 experiment, close M2, or establish external human validation.

The exact machine-readable input proposal is [m2-t003-inputs.json](m2-t003-inputs.json); its status is `pending-founder-decision`.

## Inputs to bind

- Repository and target: `jayanez/agent-braid`, `refs/heads/develop`.
- Frozen base: `f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6`.
- Workstream 1: [PR #137](https://github.com/jayanez/agent-braid/pull/137), `014-m2-observation-normalizer`, source `58351f812614058e53a8ee6aef1dd458f1bb70fc`, dependencies `[]`.
- Workstream 2: [PR #138](https://github.com/jayanez/agent-braid/pull/138), `015-m2-counterexample-reducer`, source `083f1a390988a9527a5aaeb19133401243b1d714`, dependencies `[]`.
- Registered [manifest](m2-corpus-manifest.json) file SHA-256 `5bd3dbd8c1170d8b0a2498b3b6830177dc5476a5ab4f99cfed0052ea88192107`.
- Declared [selection and footprints](m2-corpus-selection.json) file SHA-256 `978a40379b049d023be95d8eae652d7bbd06ea07942ce5776d40d2b0ad0b9737`; canonical selection SHA-256 `1ea5bc98d0daccc841f0ffcc9554fb84a5468e26dc504548d5a39042866d63a9`.
- Profile: accepted ADR 0015 `m2-real-read-only-v1`, with its exact `python -m unittest discover -s tests` allowlisted command in separate candidate and serial containers **only after this T003 decision**.
- Image: local pinned Linux ARM64 ID `sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005`.

## Frozen dependency-file bytes

| Path at base | SHA-256 |
| --- | --- |
| `scripts/docker/t013/Dockerfile` | `d96d3e097d01b98bb7cc40f5575cb0d1b7b23a4ae66a6882b41196b0284b12f5` |
| `scripts/docker/t013/apt-packages.lock` | `db23b2947328c4407d0d055c4ef9081e584b0662ec0102a8b2d5281457bd335c` |
| `scripts/docker/t013/constraints-t013.txt` | `b12b51229e18fa1ca35c7bd1404f2359debb1d877203c1e37bab685111accad5` |
| `requirements-dev.txt` | `24a8316f230a1f408b5c953bf0217968f7ccab452594e774a1771ae28df86448` |
| `requirements-speckit.txt` | `daa35d1e5551fba64cada1787b2646c283f9fb56ddc00b48f9b596b68134c392` |

## Completed selection and review

Both PRs remain open on separate branches descending from the same base. Their exact source SHAs passed their focused suites, Spec Kit, `quick`, and `pr`; both GitHub complete suites passed. Claude reviewed #137 as an agent; Luna Latest and a Codex supervising reviewer reviewed #138 at its final SHA with no blocking finding. Codex accepted both source SHAs internally as T002 candidates. These are agent reviews, not independent human validation.

The reducer's real-Git tests cover rejection and timeout paths. Its positive reduction and irreducibility cases use a controlled backend because bounded local probes did not find a real all-complete divergent replay fixture. This does not prove such a fixture is impossible, and ordinary development tests are not the ADR 0015 experiment.

The [official read-only preflight](m2-official-preflight.json) and [supplemental selection preflight](m2-corpus-preflight.json) passed. The latter rejected a stale base, a valid but substituted source commit, a duplicated PR URL, and an undeclared tracked-path write. It confirmed the remote branch heads, unchanged `origin/develop`, exact tracked-path write lists, and no execution authorization. The declared read/write footprints are scoped to static tracked paths in each fixed patch; runtime reads, generated files, hidden effects, and external effects were not dynamically observed.

## Scope of a possible acceptance

An explicit founder acceptance of **these exact inputs** would permit implementing and executing only the ADR 0015 experiment stage for this corpus. It would first run the existing Git-only preparation and serial comparison. Only after tree and stale-base checks pass may separate private containers run the single fixed test command in candidate and serial lanes, with the same image and dependencies, network/hooks/credentials/host writes/ref updates disabled, and caps of two CPUs, 2 GiB memory, 512 processes, 180 seconds and 8 MiB captured output per container. Truncation, missing dependencies, test failure, hidden effects, stale state, resource breach, or non-repeatability yield an inconclusive or rejected result, not a positive parallelism claim.

Changing the base, either PR source, manifest or footprint, image, dependency bytes, command, limits, observation contract, or target repository requires renewed review and a new decision. A positive result would apply only to this finite workload. M2 closure and external human validation remain separate decisions.

**Decision requested:** accept or reject T003 for exactly the inputs above. No acceptance is recorded in this proposal.
