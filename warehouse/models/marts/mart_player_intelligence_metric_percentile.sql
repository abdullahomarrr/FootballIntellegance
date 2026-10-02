{{ config(materialized='table') }}

with metrics as (
    select profile.player_id, profile.team_id, profile.competition_id, profile.season_id,
           profile.position_group, profile.minutes_played, profile.feature_set_version,
           case when profile.has_statsbomb_events then 'statsbomb_open' else 'wyscout_open' end as provider_pool,
           profile.intelligence_data_as_of,
           metric.metric_name, metric.metric_value, metric.higher_is_better
    from {{ ref('mart_player_season_intelligence') }} profile
    cross join lateral (values
        ('pass_completion_pct', profile.pass_completion_pct, true, false),
        ('pressured_pass_completion_pct', profile.pressured_pass_completion_pct, true, false),
        ('progressive_passes_per_90', profile.progressive_passes_per_90, true, false),
        ('passes_into_final_third_per_90', profile.passes_into_final_third_per_90, true, false),
        ('box_entries_per_90', profile.box_entries_per_90, true, false),
        ('progressive_carries_per_90', profile.progressive_carries_per_90, true, false),
        ('successful_dribbles_per_90', profile.successful_dribbles_per_90, true, false),
        ('pressures_per_90', profile.pressures_per_90, true, false),
        ('recoveries_per_90', profile.recoveries_per_90, true, false),
        ('defensive_actions_per_90', profile.defensive_actions_per_90, true, false),
        ('defensive_duels_per_90', profile.defensive_duels_per_90, true, false),
        ('turnovers_per_90', profile.turnovers_per_90, false, false),
        ('xt_added_per_90', profile.xt_added_per_90, true, false),
        ('xg_per_90', profile.xg_per_90, true, false),
        ('average_shot_xg', profile.average_shot_xg, true, false),
        ('goalkeeper_saves_per_90', profile.goalkeeper_saves_per_90, true, true),
        ('goalkeeper_save_pct', profile.goalkeeper_save_pct, true, true),
        ('goalkeeper_distribution_pct', profile.pass_completion_pct, true, true),
        ('goalkeeper_long_pass_pct', profile.goalkeeper_long_pass_pct, true, true),
        ('goals_conceded_per_90', profile.goals_conceded_per_90, false, true),
        ('claims_and_punches_per_90', profile.claims_and_punches_per_90, true, true),
        ('sweeper_actions_per_90', profile.sweeper_actions_per_90, true, true)
    ) as metric(metric_name, metric_value, higher_is_better, goalkeeper_only)
    where profile.minutes_played >= 900
      and profile.position_group is not null
      and metric.metric_value is not null
      and ((profile.position_group = 'GK') = metric.goalkeeper_only)
), ranked as (
    select *,
           percent_rank() over (
               partition by provider_pool, competition_id, season_id, position_group, metric_name
               order by metric_value
           ) * 100.0 as local_ascending_percentile,
           count(*) over (
               partition by provider_pool, competition_id, season_id, position_group, metric_name
           ) as local_population,
           min(metric_value) over (
               partition by provider_pool, competition_id, season_id, position_group, metric_name
           ) as local_minimum,
           max(metric_value) over (
               partition by provider_pool, competition_id, season_id, position_group, metric_name
           ) as local_maximum,
           percent_rank() over (
               partition by provider_pool, position_group, metric_name
               order by metric_value
           ) * 100.0 as pooled_ascending_percentile,
           count(*) over (
               partition by provider_pool, position_group, metric_name
           ) as pooled_population,
           min(metric_value) over (
               partition by provider_pool, position_group, metric_name
           ) as pooled_minimum,
           max(metric_value) over (
               partition by provider_pool, position_group, metric_name
           ) as pooled_maximum
    from metrics
), scoped as (
    select *,
           case
               when local_population >= 15 and local_maximum > local_minimum then 'COMPETITION_SEASON'
               when pooled_population >= 15 and pooled_maximum > pooled_minimum then 'POOLED_PROVIDER_POSITION'
           end as comparison_scope
    from ranked
)
select player_id, team_id, competition_id, season_id, position_group, minutes_played,
       metric_name, metric_value,
       case
           when higher_is_better and comparison_scope = 'COMPETITION_SEASON' then local_ascending_percentile
           when comparison_scope = 'COMPETITION_SEASON' then 100.0 - local_ascending_percentile
           when higher_is_better then pooled_ascending_percentile
           else 100.0 - pooled_ascending_percentile
       end as percentile,
       case when comparison_scope = 'COMPETITION_SEASON' then local_population else pooled_population end
           as comparison_population,
       comparison_scope, provider_pool,
       case
           when pooled_population >= 15 and pooled_maximum > pooled_minimum then
               case when higher_is_better then pooled_ascending_percentile
                    else 100.0 - pooled_ascending_percentile end
       end as pooled_percentile,
       pooled_population,
       higher_is_better, feature_set_version,
       intelligence_data_as_of as data_as_of
from scoped
where comparison_scope is not null
