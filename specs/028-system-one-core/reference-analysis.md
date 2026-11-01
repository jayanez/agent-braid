# System 1 reference analysis and proposed native program

Status: source inspection and planning, 2026-10-05. No upstream models were run, no
weights downloaded, no benchmark reproduced and no architecture approved here.
Public evidence is bounded to the immutable source commits in `reference-sources.json`.
This is an original Agent Braid implementation proposal, not a vendoring plan.

## Recommendation and decision rule

Start with Strands-like **typed, non-generative decision contracts**, provenance,
strict budgets and safe fallback. Do not equate that with selecting a 2B decoder.
Then compare native decoder/pointer and compact encoder/option-scoring candidates
with rules and the existing linear predictor at common risk and cost budgets.
Add Laya-like product capabilities incrementally where they earn their cost.
The recommendation is about contract and delivery order; architecture remains an
empirical choice. CPU-first or small-data deployments may favor an encoder or rules.

System 1 means a fast bounded decision path here, not a claim about cognition.
A single forward pass still reads tokens, can be expensive, can misunderstand
instructions and is not synonymous with deterministic or trustworthy reasoning.

## Existing Agent Braid constraints

The inspected base is develop `f1bc304`. The Python core has zero runtime dependencies.
`analysis.py` and Git analysis/replay preserve portable semantics; `structured_exchange.py`
implements the finite anchored-sequence domain; `runtime_policy.py` independently
verifies plans and requires separate operator grants; `runtime_scheduler.py` bounds
isolated fixed-patch preparation; `mcp_runtime.py` is a pinned stdio transport.
Predictions must stay outside these trust boundaries. The native module can be part
of Agent Braid while optional neural code lives in a separately installed package.

SPEC-019 already proposes a standard-library linear advisor for **human-assessed
usefulness**, not proof of exchange correctness. Its source audit lacks sufficient
admitted real pairs, and current valid finite verifier outcomes are degenerate for
training a correctness classifier. Reuse approved source tooling and the comparator;
do not relabel invalid requests as semantic counterexamples, expand its population
silently, or invent useful labels from a verifier that accepts all valid examples.

SPEC-021 has working bounded runtime evidence but a founder G4 NO-GO on usefulness:
six paired trials, median serial/parallel wall ratio 0.5581, uncontrolled small sample.
System 1 does not reopen that decision or close M4. Decision-cost improvements and
parallel-execution improvements are different outcomes and require separate evidence.

## Strands Decider: architecture and implementation

Inspected commit: `3e94e9d84c620ed5a95f1a3310c3decb971e261c`.

1. **Readout rather than generation.** `modeling.py` removes the LM head from a
   pretrained causal torso, adapts it with LoRA and scores request-defined options.
   The v21 family uses Qwen3.5-2B-Base, around 1.9B parameters. A small pointer head
   compares a final decision query with the last-token representation of each option.
   fp32 readout/calibration reduce unnecessary precision loss. Dynamic option count
   is architectural, but practical context/memory limits still exist.
2. **Why pointer beats slots in its experiments.** Shared query/key projections avoid
   dedicated option-slot weights and the hard trained-slot ceiling. This does not
   prove immunity to positional or semantic-label bias: a causal option representation
   still depends on preceding context and token position. Our tests must permute labels,
   descriptions, positions and instructions independently.
3. **Unified primitives.** `schema.py` and `prompting.py` map yes/no (`noul`), choice and
   ordinal score onto a masked probability distribution. A score is expectation over
   an ordered rubric, not unrestricted numerical reasoning. Choices preserve option
   identity. Boolean P(true), normalized choice concentration and score confidence
   have distinct meanings; none is a semantic assurance level.
4. **State reuse.** `infer.py` encodes a shared prefix once and forks KV/recurrent state
   across independent questions. The compute shape becomes state + sum(question)
   instead of sum(state + question). Hybrid recurrent cache tensors must be copied,
   not shared mutably. One-question calls skip the prefix path. Unsupported cache
   layouts fall back. Reuse must be tested against uncached inference, including
   numeric tolerance and device-dependent threshold crossings.
5. **Context handling.** `_fit` keeps option spans and can shorten state/question input;
   `strict_window` refuses overflow. Agent Braid should choose refusal by default and
   report exact coverage for any later partial-view mode. Losing an effect, negation
   or dependency in truncation must not look like full-state analysis.
6. **Serving limit found in source.** `server.py` stores one module-global `_engine`;
   inference keeps fitting offsets on the engine. The docs explicitly state request
   concurrency is unverified and identify the race. A single uvicorn worker is not
   proof of request serialization. Use request-local data and bounded admission in
   our implementation, and test overlapping requests with different option layouts.
   The reference HTTP server is local and unauthenticated; it is not our deployment.
7. **Training/research discipline.** Proper distribution targets, supervised/ranking
   examples, multi-step tasks, LoRA, distillation, replay, per-kind temperature and
   preregistered multi-seed runs are reusable ideas. Adopt the discipline, not all
   objectives by default. Data rights and preprocessing are separate from code rights.
8. **Artifact discipline.** `hf_export.py` supports safetensors, provenance, manifests
   and base revision identity. Older/unpinned loaders and pickle-style head files are
   patterns to avoid. Require immutable base/tokenizer/head/calibration bindings and
   reject unsafe loading or automatic network retrieval in the core.
9. **Reported performance is bounded.** README v21: JevBench 176/231 (0.762), Brier
   0.323, ECE 0.064; v19: 167/231 (0.723), Brier 0.342, ECE 0.052. v19 latency median
   115 ms/p95 299 ms on RTX 3090 is not a measurement of v21 or Agent Braid. The
   README reports same-host multi-seed recipe means around 172.8 vs 172.3 tasks,
   so the single released-checkpoint gap does not establish a recipe improvement.
   Evaluation docs lag parts of the current README; retain version/run identity.
10. **Capability limits.** Evaluation documents instruction-negation sensitivity,
    multi-step and numeric weaknesses and benchmark/sample noise. Good calibration
    on an aggregate public set is not a guarantee for Agent Braid effect semantics.
    Vision and custom accelerator kernels are interesting extensions, not MVP scope.

## Laya: architecture and implementation

Inspected version 0.3.28, commit `a4a8921afebfd852bba0000475cfb6ab737a124c`.

1. **Compact encoder alternatives.** `common.py::DecisionModel` uses a bidirectional
   backbone, type embeddings, optional Transformer head layers and a shared scorer
   over option marker states. Published English/typed checkpoints use ModernBERT-large
   (about 421M); multilingual uses mmBERT-base (about 322M). State and questions are
   read jointly rather than the decoder prefix-cache design. Reusing state tokenization
   does not mean reusing a question-independent contextual state encoding.
2. **Multiple output signals.** The action head reads pooled features, top probabilities,
   entropy and option count. README reports its act_probability lacks usable signal
   (AUROC 0.30 on 396 items). Do not reproduce a learned act/defer head as an authority
   gate. Use a transparent, calibrated abstention policy with a stated target instead.
3. **Confidence distinction is essential.** `confidence.py` distinguishes entropy-derived
   concentration from `answer_confidence = max(p)`. Entropy is not calibrated and its
   threshold does not transfer across option counts. `calibrate.py` fits temperatures
   by type/cardinality and reports sparse buckets. Neutral fallback or temperature
   clamping prevents crashes; it does not establish calibrated confidence.
4. **Routing before trust.** `router.py` chooses language/task checkpoints and manages
   loaded model lifecycle. English models can be confidently wrong off domain: README
   reports Khmer accuracy 0 with raw confidence 0.952 in one suite. We should bind
   English/Spanish/code-mix support to group evidence and defer unknown input, rather
   than route solely on confidence. General language identification is not free truth.
5. **Measured versus provisional claims.** Base typed-decision accuracy is about 0.362
   English and 0.352 multilingual, below majority 0.461 in that suite. Fine-tuned 0.766
   is reported for a different training/evaluation setup and the README explicitly says
   that row lacks a committed result file. It is not directly comparable to Strands'
   JevBench 231-task result. Teacher agreement is a proxy, not task-ground-truth ceiling.
6. **Known semantic failures.** README documents boolean-label domination, negated
   cancellation requests selecting cancellation at high confidence, ordinal position
   bias and checkpoint-specific wording sensitivity. These become permanent negative
   slices in our suite, including Spanish negation and model-facing opaque label maps.
7. **Option/context budgets.** `build_sequence`/`build_head` account for actual head length;
   high-cardinality options can exceed the nominal budget and collapse descriptions
   to a few tokens. A documented 100-option English prompt leaves only about 100 state
   tokens at a 512-token limit. Our contract refuses indistinguishable/truncated options
   and counts rendered option tokens rather than estimating state room from a cap.
8. **Shortlisting and tournament.** `shortlist.py` supports embedding retrieval, bounded
   LRU embedding cache and grouped tournaments. Preserve candidate subset identities,
   recall@k, instruction-aware retrieval and conditional finalist probabilities. A
   classifier cannot recover a label pruned by retrieval. Tournament group/order and
   narrowing errors need end-to-end calibration; full-catalogue distributions cannot
   be reconstructed by pretending dropped labels have zero probability.
9. **Option invariance extension.** New parallel option layout assigns equal positions
   and blocks cross-option attention; it is opt-in and not in the published default
   checkpoints. This is a train/runtime layout contract, not a free inference switch.
   Test equivariance on our own implementation before claiming invariance.
10. **Product surface worth adapting.** `structured.py` compiles booleans/enums/rubrics;
    hooks expose bounded observations; `serve.py` validates token/admission budgets;
    router handles idle unloading and registration. These inspire independent APIs
    with narrower initial scope. Arbitrary fields, cycles and external schema refs
    must not introduce implicit generation or network access.
    `hooks.py` explicitly notes that a timed-out callback thread continues running;
    request latency bounds are distinct from process resource/side-effect bounds.
    Our observer-only hooks need sealed metadata and a killable boundary when hard
    termination is required, rather than trusting a callback timeout as isolation.
11. **Concurrency and lifecycle.** Shared tokenizer locks and request-scoped token
    caches address real mutation races; serving bounds concurrency and idle unloading.
    Preserve immutable model identity during in-flight requests. Quantization, compile,
    ONNX and TileLang need parity and cold-start/memory measurements, not feature badges.
12. **Training and distribution.** Supervised soft targets, optional proper-scoring
    reward training, calibration and gradient checkpointing are candidates for ablation.
    The README admits a notebook calibrates on training items; use disjoint data instead.
    Recent release fixed missing `laya.backends` in wheels: a source checkout test is
    insufficient. Add clean installed-wheel and optional-extra discovery checks.
13. **Breadth is not priority.** Python/TS/.NET/Java, email parsing, browser examples and
    framework adapters show ecosystem breadth. Agent Braid first needs correct native
    boundaries; porting all integrations would create unsupported maintenance scope.

## Side-by-side decision matrix

| Dimension | Strands-like native design | Laya-like native design | Rules / linear native design |
|---|---|---|---|
| Inference | Causal torso + pointer, no decode | Encoder + option markers/head | Structural rules / feature scoring |
| Expected footprint | Larger, accelerator-friendly | Smaller, CPU candidate | Minimal; existing core compatible |
| Shared many-question state | Prefix KV/recurrent reuse | Tokenization reuse; joint contextual pass | Cheap feature reuse |
| Unknown dynamic options | Pointer scoring candidate | Shared option scoring candidate | Domain-specific; abstain outside scope |
| Instruction/general transfer | Hypothesis; negation weaknesses | Specialization usually needed | Explicit narrow domain |
| Implementation risk | Cache/torso/toolchain/memory | Budget/routing/layout/export parity | Feature/label degeneracy and limited transfer |
| Selection rule | Paired risk/cost/quality, not README score | Same data and rule | Keep as fallback and eligible comparator |

No numerical architecture ranking is justified by the current evidence. Public
benchmarks differ in labels, sample sizes, adaptation, option counts, hardware and
calibration. Our comparison fixes those where possible and reports irreducible
differences, rather than multiplying incompatible speed/accuracy claims.

## Capability-to-stage mapping

| Agent Braid stage | Native feature candidate | Preserved authoritative boundary |
|---|---|---|
| Task planning | Route to bounded advisor or System 2, prioritize requests | Host/operation contract; no generated plan assumed |
| Effect acquisition | Suggest missing effect review and metadata conflicts | Declarations + static/observed evidence remain separate |
| Interaction graph | Prioritize suspicious edges / diagnostics | Actual typed graph construction and identities |
| Analysis | Pick cheap sufficient analysis candidate; rank verifier work | Verifier independently recomputes supported claims |
| Scheduling | Priority only among constraint-admissible candidates | Enabledness, versions, dependencies, execution contract |
| Isolated execution | Recommend supported policy; argument triage | Operator grant and bounded manifest, no arbitrary tools |
| Observation/normalization | Route to registered normalizer; adequacy hints | Exact normalizer/equivalence version; model never equality oracle |
| Traces/certificates | Categorize findings, collect disagreement | Content hashes and consumer verification, no model certificates |
| Counterexamples/research | Prioritize reduction/search effort | Actual replay/divergence and unchanged scientific domain |
| Host/model/tool selection | Bounded shortlist and local advice transport | Available registry; supported tools, no new execution scope |

## What to adopt, adapt and reject

Adopt typed distributions, request-defined options, exact provenance, preregistration,
counterexamples, calibration/abstention separation, common evaluation and offline
artifact checks. Adapt prefix reuse, option-layout invariance, compact specialization,
shortlisting, schema compilation, language routing and lifecycle only after evidence.
Reject confidence-as-proof, automatic action heads, silent truncation, mutable shared
request offsets, calibration on test/train data, README-based winner selection,
unbounded fallback and automatic downloads/online learning in the core.

## Original implementation and reuse rights

Both inspected code repositories identify Apache-2.0 licenses. This allows substantial
reuse under its conditions; it does not confer rights to every referenced dataset,
base weight, logo or externally generated corpus. Implement analogous systems inside
Agent Braid without either upstream package or released head/checkpoint. If a later
task copies actual source, preserve applicable license/NOTICE/attribution, mark changes
and review Agent Braid's existing AGPL software / CC-BY-SA documentation mapping.
Do not assume repository code license licenses model weights or training data.
Strands `data/sources.md` explicitly leaves several dataset/generated-text rights
unrecorded; its dataset recipes are references, not an approved corpus inventory.

## Evidence coverage and limits

Source reviewed: model/readout, prompting, inference/caches, schemas, serving,
confidence, routing, shortlisting, training/calibration and relevant evaluation,
research and integration documents in the manifest. Larger SDKs, notebooks and
custom kernels were assessed at documented interfaces, not exhaustively executed.
The analysis covers the requested architecture and implementation planning; it is
not a complete line-by-line security audit of either repository. No upstream tests,
paid calls, training or GPU performance experiments were executed in this work.
All public numbers above are upstream reports. Agent Braid findings come from its
own versioned source/evidence; proposed gains are hypotheses only.

## 2026-11-01 update

Status: source survey for SPEC-066 and ADR 0034. Nothing below was run, downloaded
or reproduced here. Every number is **upstream-reported** (project READMEs,
documentation, blog posts and third-party design notes), not reproduced by Agent
Braid. Only the Laya release tag, its commit and the Laya, GBrain and SynapsCLI
file hashes were verified directly; they match `reference-sources.json`.

### Laya v0.4.19

Laya was inspected at v0.3.28 on 2026-10-05; v0.4.19 was released 2026-10-31
(commit `55a19f7b7b56787e1a3e41063def9bb9a8737351`; a later tag, v0.4.20, appeared
on 2026-11-01 and was not inspected). Apache-2.0.

- **Checkpoints:** `laya` (ModernBERT-large, 421M parameters, 512-token context),
  `laya-multilingual` (mmBERT-base, 322M) and `laya-typed-decisions` (421M).
- **Routing:** a router with language and script detection, exposed as
  `POST /v1/route`. A Jev-compatible `POST /v1/systemone` and
  `/v1/systemone/batch` (at most 64 states).
- **Confidence:** two signals, entropy confidence and `answer_confidence` (the
  maximum probability), with per-(type, option band) temperatures. Refit reports
  ECE 0.466 to 0.081 on held-out data. The multilingual checkpoint ships without
  fitted temperatures.
- **Abstention:** `min_confidence` with per-bucket thresholds (12 buckets plus a
  default); tri-state `passed | abstained | unevaluated`; the threshold is
  echoed; `fit_abstention_thresholds(target_error)`.
- **Option layout:** option-order rotation (order-dependent answers 16.3% to
  6.1%) and an opt-in parallel layout. `predict_shortlist` and
  `predict_tournament` for many options; accuracy degrades past about 20 options
  (Banking77 0.425). `predict_long` uses windows. `decide` and `decide_batch`;
  hooks.
- **Gate:** `laya-evals` CI gate (minimum accuracy, maximum ECE, per-slice
  metrics, tolerance against a baseline).
- **Stated limits:** near-chance zero-shot (0.362 against a 0.461 majority
  baseline), negated cancellations, boolean-word label bias. CPU latency about 110
  ms per question (421M) and about 48 ms (322M) on a 56-core host.

### Jev (TypeSafe AI, hosted)

Documentation: <https://docs.typesafe.ai>; announcement:
<https://typesafe.ai/blog/introducing-system-one-models-and-jev>.

- **API:** `POST /v1/systemone` with `{model, state, questions}` returning
  `{model, answers, usage}`. Question identifiers are never sent to the model;
  meaning lives in instructions and criteria.
- **Answer types:** `noul` (P(yes)); `choice` with at most 255 options, with
  probabilities and `confidence = (p_max - 1/n) / (1 - 1/n)`; `score` with 2 to 10
  levels. Questions are evaluated in parallel against one state.
- **Calibration and thresholds:** group-level calibration (RLCD); act-above and
  ask-below thresholds scaled with risk.
- **Versions:** alias `jev-latest` points to `jev-1.14.0` (2026-10-14);
  `response.model` names the answering version; pin versioned identifiers after
  tuning.
- **Limits and price:** 64k tokens per request, 32k per question; $0.042 per
  million input tokens.
- **Documented failure modes:** literal instructions, no counting, arithmetic or
  dates, weak indirection, large noisy state, adversarial state steering,
  first-option bias.
- **Third-party results:** GBrain reranking Recall@1 20.8% to 33.2% on 404
  queries (it fixes judgment, not recall; a naive delete threshold kept nothing)
  [design note](https://github.com/garrytan/gbrain/blob/922ba1a9d295d6a0d3bb6154ee40e3e95a964d20/docs/designs/SYSTEM_ONE_JEV_V1.md).
  SynapsCLI tool-call guard 17 of 18 at about 361 ms mean, with a fail-open host
  timeout flagged
  [research note](https://github.com/haseebkhalid1507/synapscli/blob/f2632cef12266e50dfee2a9f72d87ff5465889e6/docs/research/2026-09-20-jev-decision-layer.md).

### Open local replicas (reported, not inspected)

- **Von:** Apache-2.0, 395M ModernBERT.
- **kev:** Apache-2.0, LoRA plus pointer head on Qwen3.5 0.8B/4B/9B; speaks
  `/v1/systemone`; 9B 0.822 against Jev 0.857 as reported by its authors.
- **Rizzo Flow:** Apache-2.0, 4B and 1.7B on llama.cpp.
- **SemIf (ex-OpenJev):** frozen Qwen3.5-4B logits.
- **Nimble:** Qwen3.5-9B LoRA.
- **NanoJev:** MIT, games only.
- **Strands Decider:** already analyzed above.

### Capability mapping for SPEC-066

| Capability | Laya | Jev | Agent Braid today | SPEC-066 |
|---|---|---|---|---|
| Shadow evidence store | none | none | no episodes; telemetry is aggregate-only | Episode contract v0.1, S1.5a |
| Pinned identity | checkpoint name | versioned ids; alias drifts | `BACKEND_ID` rule fixture, no digest | REQ-007, REQ-203 |
| Tri-state abstention | `passed/abstained/unevaluated`, per-bucket thresholds | act-above and ask-below by risk | abstention absent | REQ-201 |
| Declared confidence | entropy and max probability, per-band temperatures | `p_max` based, group calibration | rule score, uncalibrated | REQ-202 |
| Batched questions | `/v1/systemone/batch` (at most 64), `decide_batch` | parallel questions on one state | one pair at a time | REQ-204 |
| Option-order invariance | rotation, parallel layout | first-option bias documented | none | REQ-205 |
| Evaluation gate | `laya-evals` | none | no committed baseline | REQ-206 |
| Local learned backend | checkpoints under Apache-2.0 | hosted only | none | REQ-301, optional extra |
| Hosted inference | none | `/v1/systemone`, paid | none | excluded pending owner egress, cost and consent decision |

### Do not adopt

- **Delete or skip by score.** The GBrain note found a naive delete threshold kept
  nothing; the value was in reranking judgment. A score never removes an item.
- **Confidence as authority.** Calibrated or not, confidence is a signal; Jev
  documents adversarial state steering, so output is never a boundary
  (`executionAuthorization` stays false).
- **Learned act head.** No head that selects or triggers actions; advice only.
- **Silent truncation.** `predict_long`-style windowing and over-limit states must
  refuse or report the truncation, never drop content silently.
- **Fail-open timeouts** (flagged in SynapsCLI) and floating model aliases.
