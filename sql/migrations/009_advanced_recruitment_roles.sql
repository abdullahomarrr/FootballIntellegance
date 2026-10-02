INSERT INTO recruitment_role (
    name, positions, feature_weights, hard_constraints, feature_set_version
) VALUES
(
    'Pressing forward',
    ARRAY['FW'],
    '{"box_entries_per_90": 5, "defensive_actions_per_90": 5, "progressive_passes_per_90": 3, "passes_into_final_third_per_90": 3, "pass_completion_pct": 2}'::jsonb,
    '{"maximum_age": 28, "minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Progressive midfielder',
    ARRAY['MD'],
    '{"progressive_passes_per_90": 5, "passes_into_final_third_per_90": 5, "progressive_carries_per_90": 4, "pressured_pass_completion_pct": 3, "recoveries_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
),
(
    'Sweeper goalkeeper',
    ARRAY['GK'],
    '{"sweeper_actions_per_90": 5, "claims_and_punches_per_90": 4, "goals_conceded_per_90": 3, "goalkeeper_saves_per_90": 2}'::jsonb,
    '{"minimum_minutes": 900}'::jsonb,
    'event_intelligence_v1'
)
ON CONFLICT (name) DO UPDATE SET
    positions = EXCLUDED.positions,
    feature_weights = EXCLUDED.feature_weights,
    hard_constraints = EXCLUDED.hard_constraints,
    feature_set_version = EXCLUDED.feature_set_version,
    updated_at = now();
