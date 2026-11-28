# T008 diagnosis and Lightning strategy review (2026-11-28)

This note is evidence for the T009 owner review and input for a future ADR on the
Lightning evaluation design. It decides nothing. It records what the T008 run shows,
what it does not show, and which evaluation strategy the literature supports for this
system. Claims are labelled by source: **repo** (committed files), **lab** (the owner's
local run store, reported as counts only), **paper** (opened and read), **abstract**
(abstract only), **own calculation**.

## 1. Summary

- T008 measured a different construct from v2 and v3. On v4, the model called
  `analyze-work` in 53 of 300 rollouts; when it called, the request was valid in 51
  of 53. Authoring is near target. Unprompted invocation is not.
- The cause is not isolated. Seven things changed between v3 and v4 at once. The
  missing product name is one of them.
- The proposed "Lightning evaluation v2" plan points the right way (separate
  authoring from invocation, pair comparisons, keep an audit set), but it is not
  executable as written, and two of its statistical pieces are wrong.
- For invocation, the strongest lever in the literature and in the host
  documentation is architecture (always-loaded tool, server instructions, a hook),
  not text optimization.
- Thompson Sampling was evaluated and is not recommended here.

## 2. What T008 shows

### 2.1 Verified numbers

| Measure | v2-test | v3-test | v4-test | Source |
|---|---|---|---|---|
| Prompts passing (of 100) | 95 | 91 | 17 | repo |
| Prompts at 0/3 | 3 | 2 | 79 | repo |
| Rollouts calling `analyze-work` (of 300) | 297 | 294 | 53 | repo, lab |
| Rollouts with no tool call | 0 | 0 | 221 | lab |
| Rollouts using `ToolSearch` | 300 | 300 | 57 | lab |
| Rollouts invoking the skill | 278 | 281 | 24 | lab |
| Seconds per rollout | 16.4 | 17.9 | 8.5 | repo |
| Within-prompt correlation (ANOVA ICC) | 0.52 | 0.41 | 0.81 | own calculation |

- Host version 2.1.311, model `claude-sonnet-5-5`, the skill hash and the lab config
  digest (`c9e23177…`) are the same for v3 and v4 (repo, lab).
- No v4 rollout passed without calling the tool (0 of 247). This follows from the
  SPEC-069 validity definition and is not a scorer artefact.
- `gate-v4-report.json` now carries `configDigest` and an `invocation` block with the
  v4 counts above, so they no longer depend on the local lab.

### 2.2 The v3 to v4 change is confounded

| # | Difference | v3-test | v4-test |
|---|---|---|---|
| 1 | Prompt names the product | 100/100 | 0/100 |
| 2 | Grammatical form | 100 directives | 87 questions, 0 directives |
| 3 | Completeness sentence ("Those are the only files involved.") | 0 | 90/100 |
| 4 | Tool descriptions (`agent_braid/tooling_mcp.py`) | pre-079 text | new `units` sentence and `analyze` help |
| 5 | Class taxonomy | 10 classes of 10 | 7 new classes; no delete, deploy or partial |
| 6 | Casual openers ("Quick sanity question…") | none | kind-choice-probe class |
| 7 | Answer stated in the prompt | no | dependency-order prompts state the order |

The 079 evaluation protocol already says the two sets admit no paired test. An
estimate such as "80 to 93 of 100 with the product name restored" has no experiment
behind it. A small factorial pilot on development prompts would measure it.

### 2.3 Consequences for T009

- Under the 079 protocol an `instrument` finding invalidates the whole run and
  requires a new split version. It does not replace individual prompts.
- Whether a prompt that states every fact needs the tool at all is a product
  question the repository does not answer. The owner decided on 2026-11-27 to label
  items as tool-necessary, tool-beneficial or tool-unnecessary before measuring.

## 3. Review of the proposed "evaluation v2" plan

### 3.1 Claims that do not hold in the repository

| Plan claim | Finding |
|---|---|
| Lightning optimizes the skill description and tool descriptions | The optimizer mutates only the skill body. Front matter is fixed (`lightning_resources.py`), `target.kind` accepts only `skill` (`lightning_config.py`), and the development set is the fixed SPEC-069 set, where every prompt names the product |
| Add invocation text to the tool description | The description sits at about 1,499 of 1,500 tokens (ADR 0038 D12) |
| `parallel` 2 to 4 is already available | The configuration accepts it; the runner loop is sequential |
| The gate B rates can be measured in the current lab | The lab disables Read, Grep, Glob and Bash and installs one plugin, so there is no competing tool or skill |
| ADR 0039 must be amended for adaptive allocation and precision rewards | ADR 0039 does not address allocation, and section 5 already allows verifiable rewards |
| The sign test is part of OD-1 | It is the H-G2 candidate-versus-baseline test |
| v1 failed for lack of prompts | v1 failed on a guidance defect (HELD-04) |

### 3.2 Statistics

The four cited preprints exist. Two are overstated.

| arXiv id | Title | What it supports |
|---|---|---|
| 2512.21326 | Measuring all the noises of LLM Evals (Wang) | Pairing alone gives about 2.25 times in sample size. The "3 to 6 times" figure needs pairing plus averaging over repeated runs. The 260 to 430 versus 900 rollout figures are not in the paper (they reproduce as an own calculation) |
| 2606.07726 | Cutting LLM Evaluation Costs with SySRs (Lyu et al.) | Synchronized successive rejects on shared queries. Experiments use deterministic scores and do not compare against racing, top-two Thompson sampling or covariance-adaptive best-arm identification |
| 2610.09239 | The Winner's Curse in LLM Self-Improvement Loops (Hu, Tang) | GEPA with 16 validation items reported +38.8 against +19.2 held out. This is an instrumented follow-up; the preregistered part covers greedy loops. A 64-item audit set removes the average bias with RMSE near 6 points; 128 items give about 4.5 |
| 2611.26592 | Realized versus Population Reliability (Agbeyegbe, Agbeyegbe) | Extra rollouts of one prompt saturate at 1/ρ effective samples. With a per-prompt cost the optimum is n* = √((c_p/c_r)(1−ρ)/ρ) |

Design findings:

1. **The share of prompts with pass probability below a threshold is not
   identifiable from a few repetitions.** With n rollouts per item only moments of
   degree n or lower are identified (2609.09245, paper). The plan's stage-two gate
   certifies a quantity the data cannot estimate.
2. **Moving to 300 prompts with one run each changes the estimand** from majority
   pass to mean pass probability. With the measured correlation (0.41 to 0.52) and a
   non-zero cost of authoring a prompt, about three repetitions is already close to
   optimal (own calculation from 2611.26592).
3. **Rerunning only the failures** is valid with a moment estimator and invalid with
   any rule of the form "failed, then passed 2 of 3, so reliable" (own derivation).
4. **Five-case minibatches support no test.** The smallest two-sided exact McNemar
   p-value at n = 5 is 0.0625.
5. **The zero-0/3 rule did not fail on noise.** The 0/3 prompts in v2 and v3 were
   deterministic `units` choices, 25 to 100 times more frequent than independence
   predicts, and SPEC-079 fixed them (`units` use 19 to 2 of 300). An identified
   replacement is an exact upper bound on the all-fail rate E[(1−p)³].
6. The current Wilson bound with z = 1.96 is a one-sided 97.5 % bound with no
   coverage guarantee. An exact Clopper–Pearson bound is the preregisterable form.

### 3.3 Optimizers and agent-lightning

- agent-lightning v1.x is reinforcement learning for open-weight models. APO exists
  only on the `v0.x` branch, last changed in January 2026 (upstream repository).
- The plan cites gains for the Agent Lightning Skill (94.9 versus 88.6; 66.7 versus
  62.9). The upstream report's Table 3 has the unguided condition ahead (0.998
  versus 0.947; 0.694 versus 0.667). The citation should be dropped.
- At budgets of a few hundred rollouts: GEPA returns the unchanged seed in 86 % of
  runs at 250 calls (2610.05671, abstract); generate-and-select matches GEPA with
  55 % fewer rollouts (2611.22605, abstract); one contrastive rewrite of a skill
  description captures most of the gain, and further iterations move F1 by less
  than 0.5 % (2606.30775, paper).
- Detecting a rise in recall from 18 % to 30 % needs about 200 rollouts per arm
  (own calculation).
- The model is closed and its policy is frozen. The problem is best-arm selection
  over text artifacts under host drift, not reinforcement learning of weights.

### 3.4 Invocation

- Host documentation: the skill description decides automatic loading and is
  truncated at 1,536 characters; MCP tools are deferred behind tool search unless a
  tool sets `anthropic/alwaysLoad`; server instructions (up to 4,096 characters)
  tell the model when to search; a `UserPromptSubmit` hook adds context
  deterministically, and its text should be factual, not imperative.
- Measurements elsewhere: a forced-evaluation hook reached 100 % skill activation
  against a 50 to 55 % baseline on 22 prompts (community post, small sample);
  always-on skills were listed 198 times and opened 0, path-gated skills 28 of 66
  (2610.14216, paper).
- An invocation-only reward teaches keyword-triggered calls (2609.16268, abstract).
  Gate B therefore needs a false-positive rate on tool-unnecessary and near-miss
  prompts next to recall.

## 4. Counterfactuals

| Counterfactual | Assessment |
|---|---|
| v4 with the product name, all else equal | Undetermined; six other differences remain. A development-set factorial resolves it |
| The v2 plan executed as written | The invocation spec stalls: no optimizer lever, description at the token cap, lab without competition, and a gate on a non-identified quantity |
| v2 and v3 without the zero-0/3 rule | Both pass (95, 91) with the deterministic `units` defect still present |
| A 300 × 1 gate on v3 | Mean pass probability 272/300 = 0.907 passes; the per-prompt signal that exposed the defect is lost |
| A Gate 0 invocation tripwire before T008 | About 20 prompts and a few minutes would have shown the collapse without spending v4 |
| Thompson Sampling adopted | No useful effect; see section 6 |

## 5. Recommended strategy

Nothing below spends a held-out set until the pilots are done.

1. **Fix the measurement.** Label items by tool necessity. Run a 2³ development
   factorial (product name × form × completeness sentence, about 200 rollouts) and a
   noise pilot (within-prompt correlation, candidate disagreement rate, A/A drift).
   Add an invocation tripwire to every future Gate 0.
2. **Invocation by architecture first.** Each lever is a measurable arm:
   `alwaysLoad`, server instructions, a skill description that leads with the use
   case, a factual `UserPromptSubmit` hook, and an explicit command. Measure in a lab
   with competing tools and co-installed skills.
3. **Light text optimization.** One to three contrastive rewrites yielding 5 to 20
   candidates. Compare all candidates on one fixed slice, sized from the pilot, with
   paired per-prompt differences and synchronized elimination. Keep the incumbent
   unless a preregistered margin is met. Report the winner on a 128-item audit set
   never used for selection.
4. **Gates.**
   - Gate A (authoring, prompts name the product): majority pass per prompt, three
     repetitions, exact Clopper–Pearson lower bound of at least 0.80 at a declared
     α, the class rule, and an exact upper bound on the all-fail rate with review of
     each 0/3 prompt.
   - Gate B (invocation): recall on necessary and beneficial items and
     false-positive rate on unnecessary items, in a preregistered 2 × 2 factorial
     (description × hook) with arms interleaved in randomized blocks.
5. **Drift control.** Pin the host and model versions, record them per rollout, run
   A/A anchors each session, and re-baseline after any host change.

## 6. Thompson Sampling

Thompson Sampling allocates trials among many options to exploit the best one early.
This system has to decide, with guarantees, among a few near-tied candidates measured
with noise.

- It changes how rollouts are allocated. The bottleneck is the power of each
  comparison.
- Candidates fail on the same hard prompts. Pairing removes that shared noise;
  adaptive allocation does not. Sample size grows as 1/Δ² under any allocation.
- Adaptively collected data biases arm means and can double false-positive and
  false-negative rates (1905.11397 and 2103.12198, abstracts). It is excluded from a
  frozen gate in any case.
- It remains an option for wide candidate pools, to be chosen by simulation against
  synchronized halving.

## 7. Limits

- Most 2026 sources are single-team preprints, several read as abstracts only.
- The host's tool-search ranking is undocumented, and `alwaysLoad` on a
  plugin-provided server is untested here.
- Community activation measurements use 22 to 24 prompts on earlier models.
- Skill Roulette (2611.23266) is a registered report without results.
- The ICC values are ANOVA estimates from per-prompt pass counts.

## 8. Sources

Papers (arXiv): 2512.21326, 2606.07726, 2610.09239, 2611.26592, 2609.09245,
2610.04135, 2411.00640, 2306.02630, 1905.11397, 2103.12198, 2010.09686, 2610.05671,
2611.22605, 2607.11944, 2606.30775, 2610.14216, 2611.23266, 2609.16268, 2605.14038,
2402.09723, 2507.19457, 2608.17528.

Upstream and host documentation: `github.com/microsoft/agent-lightning` (releases,
`skills/assets/agl-skill.pdf`); `code.claude.com/docs/en/skills`, `/mcp`, `/hooks`,
`/plugin-evals`; `github.com/anthropics/skills` (`skill-creator`).
