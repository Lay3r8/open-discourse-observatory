create table if not exists staging.semantic_gold_label_audit (
    audit_id bigserial primary key,
    sample_run_id text not null,
    candidate_document_id text not null,
    previous_relevance text,
    previous_reason_code text,
    previous_evidence_text text,
    previous_notes text,
    previous_reviewer_id text,
    previous_reviewed_at timestamptz,
    new_relevance text not null
        check (new_relevance in ('relevant', 'not_relevant', 'uncertain')),
    new_reason_code text,
    new_evidence_text text,
    new_notes text,
    new_reviewer_id text not null,
    changed_at timestamptz not null default now(),
    undone_at timestamptz,
    foreign key (sample_run_id, candidate_document_id)
        references staging.semantic_gold_label(sample_run_id, candidate_document_id)
        on delete cascade
);

create index if not exists idx_semantic_gold_label_audit_latest
    on staging.semantic_gold_label_audit(
        sample_run_id,
        new_reviewer_id,
        changed_at desc,
        audit_id desc
    );
