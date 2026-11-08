create table if not exists staging.semantic_review_run (
    sample_run_id text primary key,
    schema_version text not null,
    lexicon_version text not null,
    start_date date not null,
    end_date date not null,
    sample_size integer not null check (sample_size > 0),
    candidate_target integer not null check (candidate_target >= 0),
    negative_target integer not null check (negative_target >= 0),
    seed text not null,
    population_counts jsonb not null,
    sample_counts jsonb not null,
    output_path text not null,
    created_at timestamptz not null default now(),
    check (end_date > start_date),
    check (candidate_target + negative_target = sample_size)
);

create table if not exists staging.semantic_gold_label (
    sample_run_id text not null
        references staging.semantic_review_run(sample_run_id) on delete cascade,
    candidate_document_id text not null
        references staging.candidate_document(candidate_document_id) on delete cascade,
    sample_kind text not null
        check (sample_kind in ('candidate', 'negative_control')),
    language_bucket text not null,
    sampling_rank integer not null,
    human_relevance text
        check (human_relevance in ('relevant', 'not_relevant', 'uncertain')),
    reason_code text,
    evidence_text text,
    notes text,
    reviewer_id text,
    reviewed_at timestamptz,
    created_at timestamptz not null default now(),
    primary key (sample_run_id, candidate_document_id)
);

create index if not exists idx_semantic_gold_label_status
    on staging.semantic_gold_label(sample_run_id, human_relevance);

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
    g.human_relevance,
    g.reason_code,
    g.evidence_text,
    g.notes,
    g.reviewer_id,
    g.reviewed_at
from staging.semantic_gold_label g
join staging.candidate_document d
  on d.candidate_document_id = g.candidate_document_id;
