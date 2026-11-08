# Semantic review v1

Semantic Analysis V1 starts with a human-labelled gold set. No model is called at this stage.

## Objective

The first semantic decision is deliberately independent of ideology:

> Does the source plausibly describe pressure, sanction, exclusion, obstruction, threat or violence tied to political or ideological expression, affiliation, participation or viewpoint?

Only after relevance is established will a separate analysis pass propose actor/target/action fields and, later, ideological attribution.

## Labels

`human_relevance` accepts:

- `relevant`
- `not_relevant`
- `uncertain`

Suggested `reason_code` values for non-relevant cases:

- `political_noncoercive` — political criticism, disagreement or persuasion without coercive action or threatened cost
- `weather_or_safety`
- `ordinary_crime`
- `sport_or_entertainment`
- `routine_regulation`
- `commercial_or_nonpolitical_hr`
- `infrastructure_or_transport`
- `nonpolitical_legal_case`
- `other_nonpolitical`

For relevant/uncertain cases, use `evidence_text` to record the phrase or fact that made the decision possible.

## Sampling

The default sample is 500 documents:

- 70% discovery candidates
- 30% negative controls

Sampling is deterministic from a seed and language-balanced across English/unknown, French and Dutch where data exists. Negative controls are restricted to the languages the current discovery lexicon actually searches; this avoids diluting recall estimates with out-of-scope languages.

Create a review file:

```bash
uv run odo semantic-sample \
  --start 2025-01-01 \
  --end 2025-01-08 \
  --size 500
```

The CSV is written under `data/silver/semantic-review/semantic-review-v1/`. Fill only the review columns; do not modify IDs or source fields.

Import completed labels:

```bash
uv run odo semantic-import \
  data/silver/semantic-review/semantic-review-v1/<sample>.csv \
  --reviewer simon
```

Inspect progress:

```bash
uv run odo semantic-stats --run-id <sample-run-id>
```

## AI boundary

The gold set will be used to benchmark future semantic classifiers. Model results remain in `staging.ai_analysis` and are evaluated against `staging.semantic_gold_label`. No model output is promoted directly into `research.*`.
