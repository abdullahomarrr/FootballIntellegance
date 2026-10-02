with metrics as (
    select *, metric_name in (
        'goalkeeper_saves_per_90',
        'goalkeeper_save_pct',
        'goalkeeper_distribution_pct',
        'goalkeeper_long_pass_pct',
        'goals_conceded_per_90',
        'claims_and_punches_per_90',
        'sweeper_actions_per_90'
    ) as goalkeeper_metric
    from {{ ref('mart_player_intelligence_metric_percentile') }}
)
select player_id, competition_id, season_id, position_group, metric_name
from metrics
where (position_group = 'GK') <> goalkeeper_metric
