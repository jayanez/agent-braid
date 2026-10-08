<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Proposed first-cohort budget

Proposal dated 2026-10-08, not an approved budget or provider opt-in. The draft
registration retains `status: draft` and `provider.optIn: false`.

| Boundary | Proposed cap |
| --- | ---: |
| Total provider cost, including setup and retries | EUR 25 |
| Total input/output/retry tokens | 4,000,000 |
| Total wall boundary, including setup and human review | 28,800 seconds |
| Peak aggregate resident memory of an attempt's processes | 4 GiB |
| Retained fixture/result/receipt disk footprint | 5 GiB |

Proposed host models are `gpt-6-luna` with medium effort and
`claude-sonnet-5-5` with medium effort. Validate actual host support and freeze
exact builds before registration; no model session was run to establish support.

At the reviewed standard API reference rates,
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) costs USD
0.10/0.50 per million input/output tokens and
[Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) costs
USD 2/10. Assuming 36 model attempts per host, each consuming 25,000 input and
3,000 output tokens, gives USD 3.024 before setup, retries, taxes, processing
premiums or other applicable charges. This is arithmetic on an unmeasured
volume assumption, not a spending forecast or receipt. No cache discount is
assumed. The remaining 36 CLI-arm slots retain their own costs and outcomes.

Subscription consumption, marginal invoices and API-equivalent cost are separate
quantities. Freeze the actual billing route, applicable rate records and USD/EUR
conversion before capture; unavailable monetary costs stay null. Stop when either
the EUR or token cap is reached; the budget does not guarantee 108 completions.

Two independently scoring human raters remain required. The proposed arrangement
is the owner and a second person familiar with Python/Git, with 2–4 hours reserved
per person and disclosed blinding limits. No second identity or human score is
invented. Luna technical review cannot replace either human rating.
