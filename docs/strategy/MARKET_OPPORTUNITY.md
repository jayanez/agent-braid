# Market opportunity and validation path

## What is being sized

The 2026 model estimates an **organization-equivalent opportunity proxy**, not a
revenue TAM and not the number of all organizations globally. It starts from a
vendor-reported business-customer signal, applies explicit scenario assumptions,
and nests SAM inside TAM. Its purpose is to expose uncertainty and prioritize
validation, not to support a fundraising claim.

The reproducible source is
[`research/market/2026-opportunity-model.json`](../../research/market/2026-opportunity-model.json);
run `python3 scripts/market_sizing.py` for the computed table.

## Definitions

- **TAM proxy:** organizations in the observed signal assumed to develop or
  deploy agents and to face shared-state concurrency.
- **SAM proxy:** the TAM proxy subset assumed to be engineering-intensive and in
  the EU or US.
- **SOM:** attainable 12–18 month open-community adoption, measured as maintained
  integrations, independent reproductions, contributors, and analyzed workloads.
- **Economic reference:** SAM proxy multiplied by a hypothetical annual assurance
  spend. It is neither observed demand nor forecast revenue.

## Observed context

[OpenAI's 2025 enterprise report](https://openai.com/business/guides-and-resources/the-state-of-enterprise-ai-2025-report/)
reports more than one million business customers and describes agentic workflow
automation and coding tools among leading API use cases. This is a vendor-specific
signal, not a census. [GitHub Octoverse 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
reports 4.3 million AI projects and 1.1 million public repositories using an LLM
SDK; project counts cannot be converted directly into organizations. A
[Gartner forecast](https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025)
is retained only as forecast context.

## Validation priorities

1. Measure how many target teams actually experience cross-agent shared-state
   conflicts and their severity.
2. Establish willingness to adopt a local evidence report before testing payment.
3. Estimate unique organizations without double-counting projects, seats, and
   vendor customers.
4. Measure integration and review cost for each platform family.
5. Test whether assurance has an identifiable budget owner only after M2 evidence.

The Software → Platforms → Enterprise sequence is a learning path. It is not a
commitment to a commercial layer.
