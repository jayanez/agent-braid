<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# First-cohort budget limits

The owner approved the following numeric limits on 2026-10-08 in the M4.5
implementation chat. On 2026-10-09 the owner subsequently selected existing
Codex and Claude subscriptions within included quotas and authorized read-only
authentication and billing-control verification. **Additional spending is
authorized at EUR 0.** Paid API calls, purchased credits, overage, automatic
recharge and subscription upgrades are outside this authorization. The earlier
EUR 25 cap below remains an accounting ceiling, not permission to spend.
Exact account/model bindings, source rights, two human raters, the frozen rubric
and complete registration approval remain pending. The committed example remains
an intentionally invalid draft; private decision records retain the actual replies.

| Boundary | Approved cap |
| --- | ---: |
| Total provider cost, including setup and retries | EUR 25 |
| Total input/output/retry tokens | 4,000,000 |
| Total accounted wall time, including setup and human review | 57,600 seconds (16 hours) |
| Peak aggregate resident memory of an attempt's processes | 4 GiB |
| Retained fixture/result/receipt disk footprint | 5 GiB |

Proposed host models are `gpt-6-luna` with medium effort and
`claude-sonnet-5-5` with medium effort. Validate actual host support and freeze
exact native host builds and explicit provider model identities before registration;
use immutable provider build IDs whenever exposed, otherwise the approved observable
selector/effort/catalog/configuration/account route with backend identity unavailable.
No model session was run to establish support.

For historical reference only, at the previously reviewed standard API rates,
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) costs USD
0.10/0.50 per million input/output tokens and
[Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) costs
USD 2/10. Assuming 36 model attempts per host, each consuming 25,000 input and
3,000 output tokens, gives USD 3.024 before setup, retries, taxes, processing
premiums or other applicable charges. This is arithmetic on an unmeasured
volume assumption, not a spending forecast or receipt. No cache discount is
assumed. The remaining 36 CLI-arm slots retain their own costs and outcomes.

These reference rates do not authorize API use. Subscription consumption,
additional charges, allocated subscription cost and API-equivalent estimates are separate
quantities. Freeze the actual billing route, applicable rate records and USD/EUR
conversion before capture; unavailable monetary costs stay null. Stop when either
the EUR or token cap is reached; the budget does not guarantee 108 completions.
Subscription-only requests also refuse when fresh authenticated account, quota
or billing-control observations are unavailable, and stop on quota exhaustion
or an enabled paid fallback. Read-only verification is not registration approval
or evidence that this stop behavior has operated in a native host cohort.

Two independently scoring human raters remain required. The proposed arrangement
is the owner and a second person familiar with Python/Git, with 2–4 hours reserved
per person and disclosed blinding limits. No second identity or human score is
invented. Luna technical review cannot replace either human rating.

The time proposal reserves up to eight hours for the two human raters together
and up to eight for setup and all attempts. It is an accounting ceiling, not an
elapsed-time forecast: overlap inside one attempt is not added twice, and
separate attempts and setup retain their costs. The earlier eight-hour proposal
left too little margin when including human review. No measured throughput or
completion guarantee is implied by this allocation.
