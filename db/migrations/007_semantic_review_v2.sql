alter table staging.semantic_gold_label
    add column if not exists coercion_assessment text
        check (coercion_assessment in ('yes', 'no', 'uncertain')),
    add column if not exists expressive_scope_assessment text
        check (expressive_scope_assessment in ('yes', 'no', 'uncertain', 'not_applicable')),
    add column if not exists review_schema_version text;

alter table staging.semantic_gold_label_audit
    add column if not exists previous_coercion_assessment text,
    add column if not exists previous_expressive_scope_assessment text,
    add column if not exists previous_review_schema_version text,
    add column if not exists new_coercion_assessment text,
    add column if not exists new_expressive_scope_assessment text,
    add column if not exists new_review_schema_version text;

create index if not exists idx_semantic_gold_label_review_schema
    on staging.semantic_gold_label(sample_run_id, review_schema_version);

create or replace view analytics.semantic_gold_labels as
select
    g.sample_run_id,
    g.candidate_document_id,
    g.sample_kind,
    g.language_bucket,
    g.sampling_rank,
    d.discovery_date,
    d.source_common_name,
    d.source_language,
    d.title,
    d.canonical_url,
    g.coercion_assessment,
    g.expressive_scope_assessment,
    g.human_relevance,
    g.reason_code,
    g.evidence_text,
    g.notes,
    g.review_schema_version,
    g.reviewer_id,
    g.reviewed_at
from staging.semantic_gold_label g
join staging.candidate_document d
  on d.candidate_document_id = g.candidate_document_id;
