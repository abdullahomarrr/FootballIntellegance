-- Built-in recruitment roles for every position group, plus cleanup of roles that
-- automated validation runs saved into the live table.

INSERT INTO recruitment_role (
    name, positions, feature_weights, hard_constraints, feature_set_version
) VALUES
(
    'Ball-playing centre-back',
    ARRAY['DF'],
    '{"progressive_passes_per_90": 5, "pressured_pass_completion_pct": 5, "pass_completion_pct": 4, "defensive_duels_per_90": 3, "recoveries_per_90": 3, "turnovers_per_90": 3}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Stopper centre-back',
    ARRAY['DF'],
    '{"defensive_duels_per_90": 5, "defensive_actions_per_90": 5, "pressures_per_90": 3, "recoveries_per_90": 3, "pass_completion_pct": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Attacking full-back',
    ARRAY['DF'],
    '{"progressive_carries_per_90": 5, "passes_into_final_third_per_90": 5, "box_entries_per_90": 4, "successful_dribbles_per_90": 3, "xt_added_per_90": 3, "recoveries_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Defensive full-back',
    ARRAY['DF'],
    '{"defensive_duels_per_90": 5, "defensive_actions_per_90": 4, "recoveries_per_90": 4, "pass_completion_pct": 3, "turnovers_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Deep-lying playmaker',
    ARRAY['MD'],
    '{"pass_completion_pct": 5, "pressured_pass_completion_pct": 5, "progressive_passes_per_90": 5, "passes_into_final_third_per_90": 4, "turnovers_per_90": 3}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Ball-winning midfielder',
    ARRAY['MD'],
    '{"pressures_per_90": 5, "recoveries_per_90": 5, "defensive_duels_per_90": 5, "defensive_actions_per_90": 4, "pass_completion_pct": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Box-to-box midfielder',
    ARRAY['MD'],
    '{"progressive_carries_per_90": 4, "recoveries_per_90": 4, "box_entries_per_90": 4, "pressures_per_90": 3, "defensive_actions_per_90": 3, "xg_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Attacking midfielder',
    ARRAY['MD'],
    '{"box_entries_per_90": 5, "passes_into_final_third_per_90": 5, "xt_added_per_90": 4, "xg_per_90": 4, "successful_dribbles_per_90": 3, "progressive_passes_per_90": 3}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Goal poacher',
    ARRAY['FW'],
    '{"xg_per_90": 5, "average_shot_xg": 5, "box_entries_per_90": 3, "turnovers_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Direct winger',
    ARRAY['FW'],
    '{"successful_dribbles_per_90": 5, "progressive_carries_per_90": 5, "box_entries_per_90": 4, "xt_added_per_90": 3, "xg_per_90": 3}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Creative winger',
    ARRAY['FW'],
    '{"passes_into_final_third_per_90": 5, "box_entries_per_90": 5, "xt_added_per_90": 4, "progressive_passes_per_90": 4, "successful_dribbles_per_90": 3}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Shot-stopping goalkeeper',
    ARRAY['GK'],
    '{"goalkeeper_save_pct": 5, "goals_conceded_per_90": 5, "goalkeeper_saves_per_90": 3, "claims_and_punches_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Ball-playing goalkeeper',
    ARRAY['GK'],
    '{"goalkeeper_distribution_pct": 5, "goalkeeper_long_pass_pct": 4, "sweeper_actions_per_90": 4, "goalkeeper_save_pct": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
)
ON CONFLICT (name) DO UPDATE SET
    positions = EXCLUDED.positions,
    feature_weights = EXCLUDED.feature_weights,
    hard_constraints = EXCLUDED.hard_constraints,
    feature_set_version = EXCLUDED.feature_set_version,
    updated_at = now();

-- Roles named "Validation ..." were written by automated end-to-end checks, not people.
UPDATE shortlist SET role_id = NULL
WHERE role_id IN (SELECT role_id FROM recruitment_role WHERE name LIKE 'Validation %');
DELETE FROM recruitment_role WHERE name LIKE 'Validation %';
