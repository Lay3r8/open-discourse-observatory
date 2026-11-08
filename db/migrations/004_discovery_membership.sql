create table if not exists staging.discovery_batch_document (
    batch_id text not null
        references staging.discovery_batch(batch_id) on delete cascade,
    candidate_document_id text not null
        references staging.candidate_document(candidate_document_id) on delete cascade,
    sample_kind text not null
        check (sample_kind in ('candidate', 'negative_control')),
    matched_token text,
    created_at timestamptz not null default now(),
    primary key (batch_id, candidate_document_id)
);

insert into staging.discovery_batch_document(
    batch_id,
    candidate_document_id,
    sample_kind,
    matched_token
)
select
    batch_id,
    candidate_document_id,
    sample_kind,
    matched_token
from staging.candidate_document
on conflict (batch_id, candidate_document_id) do nothing;

alter table staging.candidate_document
    rename column batch_id to first_batch_id;

alter table staging.candidate_document
    rename column sample_kind to first_sample_kind;

alter table staging.candidate_document
    rename column matched_token to first_matched_token;

create index if not exists idx_discovery_batch_document_candidate
    on staging.discovery_batch_document(candidate_document_id);

create or replace view analytics.discovery_candidate_documents as
select
    d.candidate_document_id,
    m.batch_id,
    d.discovery_date,
    d.source_common_name,
    d.source_language,
    d.title,
    d.canonical_url,
    d.title_sha256,
    d.url_sha256,
    m.sample_kind,
    m.matched_token
from staging.discovery_batch_document m
join staging.candidate_document d
  on d.candidate_document_id = m.candidate_document_id;
