# AI analysis boundary

AI is part of the analysis pipeline, but it is not an autonomous research adjudicator.

## Planned stages

1. **Semantic relevance — two axes**  
   Predict coercion first, then expressive political/ideological scope separately. The final relevance label is derived from those two predictions. Each axis must include confidence and evidence.

2. **Structured extraction**  
   Extract candidate event date, country, initiator, target, action types, institutional role, trigger and consequences. Each field must retain provenance.

3. **Clustering assistance**  
   Suggest which documents refer to the same underlying incident. Media coverage rows remain separate from incident counts.

4. **Ideological attribution**  
   Performed separately from relevance detection. The model may propose an attribution only from explicit evidence such as affiliation, self-identification, named organization or reliable sourcing. It must support `uncertain` and provide a confidence score and rationale.

5. **Human validation**  
   No AI output can promote a record into `research.*`. Human review remains mandatory.

## Anti-bias design

- Discovery lexicons contain action terms, not ideological labels.
- Relevance analysis should not use the desired left/right comparison as an objective.
- Ideological attribution is a separate pass so relevance cannot be conditioned on camp.
- Store model/provider, model version, prompt version, schema version, confidence and raw structured response.
- Preserve negative-control samples to estimate false negatives.
- Build a manually labelled benchmark set and report precision/recall by language, country and ideological camp once enough cases exist.
- Run robustness checks excluding low-confidence AI-assisted fields.
- Where practical, blind coders/models to outcome variables that are not needed for the current task.

## Gold-set prerequisite

Before enabling a live semantic model, build a manually reviewed benchmark with `odo semantic-sample`. The initial target is 500 documents with both discovery candidates and in-scope negative controls. Model precision/recall must be measured against these labels before large-scale automated use.

## Database boundary

Human benchmark labels live in `staging.semantic_gold_label`. AI results are stored only in `staging.ai_analysis`. Human-validated research records live in `research.*`.
