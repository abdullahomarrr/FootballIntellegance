{{ config(materialized='table') }}

with metrics as (
    select profile.player_id, profile.team_id, profile.competition_id, profile.season_id,
           profile.position_group, profile.minutes_played, profile.data_as_of,
           metric.metric_name, metric.metric_value
    from {{ ref('mart_player_season_profile') }} profile
    cross join lateral (values
        ('goals_per_90'::text, profile.goals_per_90::numeric),
        ('assists_per_90', profile.assists_per_90::numeric),
        ('shots_per_90', profile.shots_per_90::numeric),
        ('shots_on_target_per_90', profile.shots_on_target_per_90::numeric),
        ('passes_per_90', profile.passes_per_90::numeric),
        ('key_passes_per_90', profile.key_passes_per_90::numeric),
        ('tackles_per_90', profile.tackles_per_90::numeric),
        ('interceptions_per_90', profile.interceptions_per_90::numeric)
    ) as metric(metric_name, metric_value)
), ranked as (
    select *,
           percent_rank() over (
               partition by competition_id, season_id, position_group, metric_name
               order by metric_value
           ) * 100.0 as percentile
    from metrics
    where metric_value is not null and minutes_played >= 900 and position_group is not null
)
select
    player_id,
    team_id,
    competition_id,
    season_id,
    position_group,
    minutes_played,
    metric_name,
    metric_value,
    round(percentile::numeric, 2) as percentile,
    'competition_season_position_min_900'::text as comparison_population,
    'player_style_v2'::text as feature_set_version,
    data_as_of
from ranked
