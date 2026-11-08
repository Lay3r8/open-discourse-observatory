# Semantic review v2

Semantic Analysis starts with a human-labelled gold set. No model decides corpus membership at this stage.

## Two-axis decision

The review no longer collapses two different questions into a single judgment.

### Axis 1 — coercion

> Does the source describe an action that imposes or seeks to impose a cost, restriction, sanction, exclusion, obstruction, suppression, threat or violence?

Values:

- `yes`
- `no`
- `uncertain`

Criticism, disagreement or persuasion alone is not coercion.

### Axis 2 — expressive political/ideological scope

Asked only when coercion is `yes`:

> Does the coercive action target the person/group because of its expression, opinion, affiliation or political/ideological activity?

Values:

- `yes`
- `no`
- `uncertain`

For `coercion=no|uncertain`, the stored scope value is `not_applicable`.

## Derived relevance

`human_relevance` remains for compatibility and benchmarking, but it is derived from the two axes:

| Coercion | Expressive scope | Derived relevance |
| --- | --- | --- |
| no | not_applicable | not_relevant |
| uncertain | not_applicable | uncertain |
| yes | yes | relevant |
| yes | no | not_relevant |
| yes | uncertain | uncertain |

This prevents political-but-non-coercive speech from entering the corpus and also excludes coercion that targets something other than political/ideological expression.

Examples:

- political criticism with no threatened cost → `no / n/a`;
- McDonald’s dismissal for workplace harassment → `yes / no`;
- sports boycott intended to pressure a government policy → `yes / no`;
- violence against random civilians with no expressive target → `yes / no`;
- conference cancelled because of the speaker’s political views → `yes / yes`.

## Reason codes

When coercion is `no`, the UI offers reasons such as:

- `political_noncoercive`
- `weather_or_safety`
- `operational_or_technical`
- `reporting_or_background_only`
- `no_identifiable_coercive_action`
- `other_no_coercion`

When coercion is `yes` but expressive scope is `no`, it offers:

- `state_policy_pressure`
- `violence_without_expression_target`
- `commercial_or_nonpolitical_hr`
- `sport_or_entertainment`
- `routine_regulation`
- `identity_or_conduct_not_expression`
- `nonpolitical_legal_case`
- `other_out_of_scope`

## Legacy labels

Existing v1 annotations are preserved verbatim. They are not silently converted because a v1 `not_relevant` or `uncertain` label does not tell us which axis failed. The browser UI therefore asks the reviewer to recode those documents under v2. Progress counts only completed v2 annotations.

## Sampling

The existing 500-document sample is unchanged:

- 70% discovery candidates;
- 30% negative controls;
- deterministic sampling;
- language balancing across English/unknown, French and Dutch.

The recommended initial human target remains 150 v2-coded documents.

## AI boundary

Future AI models will predict the two axes separately. Model results remain in `staging.ai_analysis` and will be evaluated against these human v2 labels. Ideological attribution of actors remains a later, separate task.
