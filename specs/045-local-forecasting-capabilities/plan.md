# SPEC-045: Implementation plan

## Technical context and scope

Reuse SPEC-034–037 modules for a stdlib core and separate local CPU container. No M4.5 host/quota module is modified.

## Constitution check before research

Articles 6/12 preserve runtime correctness, isolation and independent grants; 7/20 preserve analysis/execution boundaries; 13/14 preserve evidence provenance; 19 requires measured complete cost. No MUST conflict is proposed.

## Research, assumptions and alternatives

Existing M4 is bounded-complete with historical utility NO-GO. Relevant M4.5 measurement primitives are reusable only within their observed scopes: sampled root RSS is not enforced capacity. Docker local cgroup memory/CPU enforcement is a separate model-worker profile. No actual checkpoint approval exists.

## Design and compatibility

Version numeric windows/resources/forecasts/advice independently. API sessions own their copies and lifecycle. CLI forecasting is opt-in; MCP is a separate local read-only transport with no repository/path/grant inputs. Worker: Linux ARM64 on the existing local Docker engine, immutable image/model/lock, CPU1/thread1, memory and memory+swap both 2147483648 bytes, tmpfs64MiB, no network/root permissions, pids64, context128, horizons1/5/10, cold30s/resident1s, one active/no queue. Container memory and sampled process RSS are recorded distinctly. No automatic limit increase.

## Validation strategy

Requirement → scenario → executable test → raw evidence. Stubs and synthetic controls precede actual checkpoint conformance. Default discovery never imports ML or accesses network. Whole-cost paired Git fixtures use independent operator grants and fresh owned arms. quick after coherent increments and pr on stable candidates; feature reproduction and human gates are separate.

## Constitution check after design

Advice cannot alter effects, resources, waves, operator authority or recovery. Failed and unavailable controls stay visible.

## Human review and unresolved decisions

Exact model/dependency/license/provisioning approval, canonical ADR adoption, real source/privacy/window/budget and holdout interpretation/promotion remain distinct actual decisions.
