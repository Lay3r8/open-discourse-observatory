create table if not exists staging.discovery_batch (
    batch_id text primary key,
    source_system text not null,
    query_version text not null,
    lexicon_version text not null,
    batch_date date not null,
    gcp_project_id text,
    bigquery_location text,
    query_bytes_processed bigint,
    query_bytes_billed bigint,
    max_bytes_billed bigint,
    candidate_rows integer not null default 0,
    negative_control_rows integer not null default 0,
    unique_urls integer not null default 0,
    unique_titles integer not null default 0,
    raw_path text,
    bronze_path text,
    manifest_path text,
    status text not null check (status in ('complete', 'failed')),
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_discovery_batch_date
    on staging.discovery_batch(batch_date);

create table if not exists staging.candidate_document (
    candidate_document_id text primary key,
    batch_id text not null references staging.discovery_batch(batch_id) on delete cascade,
    discovery_date date not null,
    gdelt_date text,
    source_common_name text,
    source_language text,
    title text,
    normalized_title text,
    title_sha256 char(64),
    source_url text,
    canonical_url text,
    url_sha256 char(64),
    sample_kind text not null check (sample_kind in ('candidate', 'negative_control')),
    matched_token text,
    metadata jsonb not null default '{}'::jsonb,
    discovered_at timestamptz not null default now()
);

create index if not exists idx_candidate_document_batch
    on staging.candidate_document(batch_id);
create index if not exists idx_candidate_document_sample
    on staging.candidate_document(sample_kind);
create index if not exists idx_candidate_document_title_sha
    on staging.candidate_document(title_sha256);
create index if not exists idx_candidate_document_url_sha
    on staging.candidate_document(url_sha256);

create table if not exists staging.ai_analysis (
    analysis_id uuid primary key default gen_random_uuid(),
    candidate_document_id text not null
        references staging.candidate_document(candidate_document_id) on delete cascade,
    analysis_type text not null,
    model_provider text not null,
    model_name text not null,
    prompt_version text not null,
    schema_version text not null,
    response_json jsonb not null,
    confidence numeric(5,4),
    human_review_status text not null default 'pending'
        check (human_review_status in ('pending', 'accepted', 'rejected', 'corrected')),
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    unique (
        candidate_document_id,
        analysis_type,
        model_provider,
        model_name,
        prompt_version,
        schema_version
    )
);

create or replace view analytics.discovery_batches as
select
    batch_id,
    source_system,
    query_version,
    lexicon_version,
    batch_date,
    query_bytes_processed,
    query_bytes_billed,
    max_bytes_billed,
    candidate_rows,
    negative_control_rows,
    unique_urls,
    unique_titles,
    status,
    completed_at
from staging.discovery_batch;

create or replace view analytics.discovery_candidate_documents as
select
    candidate_document_id,
    batch_id,
    discovery_date,
    source_common_name,
    source_language,
    title,
    canonical_url,
    title_sha256,
    url_sha256,
    sample_kind,
    matched_token
from staging.candidate_document;
