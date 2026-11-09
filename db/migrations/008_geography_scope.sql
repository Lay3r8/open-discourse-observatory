alter table staging.discovery_batch
    add column if not exists geography_scope_version text,
    add column if not exists target_country_codes jsonb;

alter table staging.semantic_review_run
    add column if not exists query_version text,
    add column if not exists geography_scope_version text;

drop view if exists analytics.discovery_batches;

create view analytics.discovery_batches as
select
    batch_id,
    source_system,
    query_version,
    lexicon_version,
    geography_scope_version,
    target_country_codes,
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
