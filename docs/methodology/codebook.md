# Codebook v0.1

## Ideological attribution

`analysis_camp` is a research coding field, not a statement about personal identity.

Allowed broad values in the pilot include:

- `Left/progressive`
- `Right/conservative`
- `Other/uncertain`
- `Institutional/uncertain`

`include_left_right=true` only when attribution is sufficiently supported for direct binary comparison.

`camp_confidence` should be `High`, `Medium` or `Low` and must be backed by `attribution_basis`.

## Action flags

Each action is coded independently.

- `organized_pressure`: coordinated petition, boycott, campaign to a venue/employer/platform, or equivalent.
- `deplatforming_attempt`: explicit attempt to prevent a person/work/event from being hosted or distributed.
- `deplatforming_success`: the targeted event/work was actually cancelled, removed or materially prevented.
- `content_removal_or_suppression`: content was withdrawn, suppressed or made unavailable.
- `employment_sanction`: dismissal, suspension or non-renewal tied to the dispute.
- `career_exit`: resignation or departure materially connected to the pressure episode.
- `mandatory_training`: corrective/ideological training imposed as a consequence.
- `professional_sanction`: action by a professional regulator or comparable body.
- `formal_investigation_or_discipline`: formal internal or regulatory procedure.
- `doxxing`: non-public personal information disclosed to facilitate pressure/harassment.
- `targeted_harassment`: sustained personalized harassment rather than ordinary criticism.
- `threats`: credible or explicit threats of harm or intimidation.
- `physical_obstruction`: access/movement physically blocked.
- `violence`: physical attack, projectiles, assault or comparable force.
- `legal_restriction`: law/regulation directly restricting the targeted expression/activity.
- `state_power`: coercive action exercised by a public authority.
- `judicially_unlawful`: a competent court/tribunal later found the relevant action unlawful.
- `same_camp_dissent`: initiator and target were reasonably part of the same broad political coalition before the disputed deviation.

## Evidence grade

- `A`: primary/legal record or multiple strong independent sources.
- `B`: credible reporting with some unresolved factual limitations.
- `C`: plausible but insufficient for strong comparative claims.

Comparative headline analysis should default to A/B and run a high-confidence attribution robustness view.
