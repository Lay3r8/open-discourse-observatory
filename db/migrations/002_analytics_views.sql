create or replace view analytics.fact_incidents as
select * from research.incident;

create or replace view analytics.fact_sources as
select * from research.source;

create or replace view analytics.dim_country as
select * from research.country;

create or replace view analytics.dim_group as
select * from research.country_group;

create or replace view analytics.country_group_bridge as
select * from research.country_group_membership;

create or replace view analytics.incident_action_flags as
select
    i.incident_id,
    action.action_type,
    action.occurred
from research.incident i
cross join lateral (values
    ('organized_pressure', i.organized_pressure),
    ('deplatforming_attempt', i.deplatforming_attempt),
    ('deplatforming_success', i.deplatforming_success),
    ('content_removal_or_suppression', i.content_removal_or_suppression),
    ('employment_sanction', i.employment_sanction),
    ('career_exit', i.career_exit),
    ('mandatory_training', i.mandatory_training),
    ('professional_sanction', i.professional_sanction),
    ('formal_investigation_or_discipline', i.formal_investigation_or_discipline),
    ('doxxing', i.doxxing),
    ('targeted_harassment', i.targeted_harassment),
    ('threats', i.threats),
    ('physical_obstruction', i.physical_obstruction),
    ('violence', i.violence),
    ('legal_restriction', i.legal_restriction),
    ('state_power', i.state_power),
    ('judicially_unlawful', i.judicially_unlawful),
    ('same_camp_dissent', i.same_camp_dissent)
) as action(action_type, occurred);

create or replace view analytics.left_right_incidents as
select *
from research.incident
where include_left_right = true
  and analysis_camp in ('Left/progressive', 'Right/conservative');
