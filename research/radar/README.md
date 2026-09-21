# Scientific and technology radar

The radar records candidates and review decisions without treating recency or
popularity as scientific validation. Entries distinguish peer-reviewed research,
standards, official documentation, unreproduced results, products, and market
signals. Each record declares provenance, claim level, relevance, affected
artifacts, and the human decision.

## Cadence

- Weekly, Monday 09:00 Europe/Madrid: read-only candidate report; no repository edits.
- First Monday monthly: deep review proposed through a human-reviewed pull request.
- Before every milestone closure: an explicit milestone review, regardless of
  monthly-review recency.

CI validates committed structure and provenance only. It does not browse the web,
assert current scientific consensus, approve evidence, refresh normative hashes,
or modify the Constitution.

## Status and claim vocabulary

- Entry status: `candidate`, `adopted`, `rejected`, or `watch`.
- Claim level: `official-documentation`, `peer-reviewed-result`,
  `unreproduced-result`, `product-capability`, `market-observation`, or `forecast`.
- Source class: `paper`, `standard`, `official-documentation`, `product`, or
  `market-signal`.

Adoption means only that the stated project decision was taken. It does not
upgrade the source's scientific strength.
