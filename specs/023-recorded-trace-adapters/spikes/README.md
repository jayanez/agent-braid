# Offline lifecycle projection experiment

This experiment runs ten predeclared synthetic cases from
[corpus.json](corpus.json), then records every mapped and unsupported case in
[results.json](results.json). The corpus uses a feature-local normalized metadata
shape inspired by selected lifecycle documentation. It is neither an actual
provider trace export nor a protocol conformance corpus. Provider/library code,
models, collectors, runtime tools and external state are never executed.

The [source pins](../source-pins.json) were retrieved before corpus creation.
Context7 discovered documentation; immutable primary GitHub source bytes supplied
commit/version and SHA-256 pins. Some Context7 version queries returned moving
branch snippets, so those snippets do not establish selected-version behavior.
Documentation retrieval used read-only network requests. The offline experiment
itself makes zero network/process/model/provider calls. No documentation bodies
were copied into this repository; minimal excerpts and independently authored
summaries identify the inspected boundaries.

Selected OpenAI Agents Python version is `v0.23.1`. Its pinned HITL documentation
describes interruption, approval/rejection and serialized pause/resume. Synthetic
cases retain identities and chronology in the spike packet; mapping into AIM
retains source operation identity and changes coverage to unknown for lifecycle
annotations. Approval is not an effect certificate. Four cases map to unknown;
one repeated-attempt case rejects. Complete provider projection therefore has a
negative outcome, with no adoption conclusion.

Selected MCP task version is **2025-11-25**, deliberately the historical
experimental `taskId`/status contract. Current source discovery found 2026-07-28;
its `requestState` multi-round-trip dialect is kept separate. Three cases map to
unknown. Repeated attempts and a newer-dialect state handle are unsupported.
`taskId` is retained as an opaque synthetic handle in the spike packet; a locally
labelled digest records the handle without decoding it. AIM lacks this lifecycle
and handle dimension. The experiment is negative for complete provider
projection, never evidence of current MCP implementation compatibility.

| Provider | Cases | Mapped unknown | Unsupported | False-safe | Analyzer recompute consistency |
|---|---:|---:|---:|---:|---:|
| OpenAI v0.23.1 | 5 | 4 | 1 | 0/5 | 4/4 mapped |
| MCP 2025-11-25 | 5 | 3 | 2 | 0/5 | 3/3 mapped |

Analyzer recomputation uses the same mapped projection and implementation. These
consistency counts are not an independent mapping baseline or provider conformance
result. The separately frozen generic direct-AIM fixture belongs to T005; T006
uses predeclared expected classifications as its bounded negative controls.

No case is excluded. A false-safe result is an independent-candidate classification
where the predeclared case requires unknown or unsupported. Negative outcomes
complete these bounded spike investigations, while source/provider correctness,
real-source admission and human/adoption decisions remain pending. Timeline
retention in a spike packet does not resolve missing AIM lifecycle semantics.

Run from repository root:

```sh
python3 specs/023-recorded-trace-adapters/spikes/run_lifecycle.py
python3 -m unittest discover -s tests -p 'test_trace_lifecycle_spikes.py' -v
```

## Ecosystem screening

[Screening records](../ecosystem-screening.json) link the same immutable primary
pins. The recorded dispositions are current proposals; historical SPEC-011/radar
bytes and adopted status remain untouched.

- A2A v1.0.1 and the primary TCK were discovered. TCK documentation covers gRPC,
  JSON-RPC and HTTP+JSON; matching selected protocol version and actual conformance
  execution remain pending. Task/context/message status does not certify complete
  effect/version/dependency semantics. Disposition: `watch`.
- NeMo Agent Toolkit v1.9.0 pins document an Apache-2.0 toolkit with plugin-based
  telemetry exporters. No plugin, collector or SDK is installed. Trace execution
  flow lacks complete AIM resource/attempt/version semantics, and exporters may
  transmit sensitive intermediate data. Disposition: `research-only`.
- OpenTelemetry semantic conventions v1.44.0 moved/deprecated relevant GenAI
  attributes. The followup GenAI repository is pinned to an unreleased commit;
  inspected attributes retain development stability, and no stable GenAI version
  is selected. Message attributes can expose raw bodies. No collector/SDK is
  installed, and trace correlation cannot create operation dependencies.
  Disposition: `watch`, version/conformance assessment inconclusive.

Apache-2.0 source-license discovery for these ecosystems does not approve SDK,
plugin, transitive-dependency or service licensing. All such dependency decisions
remain outside this stdlib-only importer. No screened ecosystem is adopted and
no real source is admitted.
