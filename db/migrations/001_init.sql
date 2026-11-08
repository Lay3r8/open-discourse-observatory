create extension if not exists pgcrypto;

create schema if not exists staging;
create schema if not exists research;
create schema if not exists analytics;

create table if not exists research.country (
    country_iso3 char(3) primary key,
    country text not null,
    region text,
    subregion text,
    predominant_language_group text,
    eu_2026 boolean not null default false
);

create table if not exists research.country_group (
    group_id text primary key,
    group_name text not null unique,
    description text
);

create table if not exists research.country_group_membership (
    country_iso3 char(3) not null references research.country(country_iso3),
    group_id text not null references research.country_group(group_id),
    membership_type text not null check (membership_type in ('core', 'partial')),
    filter_weight numeric(6,3) not null default 1,
    primary key (country_iso3, group_id)
);

create table if not exists research.incident (
    incident_id text primary key,
    event_date date,
    date_precision text,
    year smallint,
    country text,
    country_iso3 char(3) references research.country(country_iso3),
    city text,
    sector text,
    target_type text,
    target_name text,
    initiator_name text,
    initiator_specific_ideology text,
    analysis_camp text,
    camp_confidence text,
    attribution_basis text,
    include_left_right boolean not null default false,
    issue text,
    action_primary text,
    organized_pressure boolean not null default false,
    deplatforming_attempt boolean not null default false,
    deplatforming_success boolean not null default false,
    content_removal_or_suppression boolean not null default false,
    employment_sanction boolean not null default false,
    career_exit boolean not null default false,
    mandatory_training boolean not null default false,
    professional_sanction boolean not null default false,
    formal_investigation_or_discipline boolean not null default false,
    doxxing boolean not null default false,
    targeted_harassment boolean not null default false,
    threats boolean not null default false,
    physical_obstruction boolean not null default false,
    violence boolean not null default false,
    legal_restriction boolean not null default false,
    state_power boolean not null default false,
    judicially_unlawful boolean not null default false,
    same_camp_dissent boolean not null default false,
    outcome text,
    evidence_grade text,
    notes text,
    verified_on date,
    source_dataset text not null default 'pilot-v0.1',
    ingested_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_incident_event_date on research.incident(event_date);
create index if not exists idx_incident_country on research.incident(country_iso3);
create index if not exists idx_incident_camp on research.incident(analysis_camp, camp_confidence);
create index if not exists idx_incident_sector on research.incident(sector);

create table if not exists research.source (
    source_id text primary key,
    incident_id text not null references research.incident(incident_id) on delete cascade,
    publisher text,
    source_date date,
    source_type text,
    url text not null,
    supports text,
    ingested_at timestamptz not null default now()
);

create index if not exists idx_source_incident on research.source(incident_id);

create table if not exists research.coding_decision (
    coding_decision_id bigserial primary key,
    incident_id text not null references research.incident(incident_id) on delete cascade,
    field_name text not null,
    value_text text,
    confidence text,
    basis_type text not null,
    basis_description text,
    source_id text references research.source(source_id),
    coder_id text not null,
    source_dataset text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (incident_id, field_name, coder_id, source_dataset)
);

create table if not exists staging.document (
    document_id uuid primary key default gen_random_uuid(),
    source_system text not null,
    source_url text,
    retrieved_at timestamptz not null default now(),
    published_at timestamptz,
    title text,
    language text,
    content_sha256 text not null,
    raw_path text not null,
    metadata jsonb not null default '{}'::jsonb,
    unique (content_sha256)
);

create table if not exists staging.candidate_incident (
    candidate_id uuid primary key default gen_random_uuid(),
    document_id uuid references staging.document(document_id) on delete set null,
    discovered_at timestamptz not null default now(),
    event_date date,
    country_iso3 char(3),
    actor_name text,
    target_name text,
    action_primary text,
    proposed_camp text,
    proposed_confidence numeric(5,4),
    extraction_model text,
    extraction_schema_version text,
    extracted_payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending' check (status in ('pending','rejected','promoted')),
    promoted_incident_id text references research.incident(incident_id)
);

create table if not exists staging.classification (
    classification_id uuid primary key default gen_random_uuid(),
    document_id uuid not null references staging.document(document_id) on delete cascade,
    classifier text not null,
    schema_version text not null,
    confidence numeric(5,4),
    payload jsonb not null,
    created_at timestamptz not null default now()
);
