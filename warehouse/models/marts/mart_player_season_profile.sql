{{ config(materialized='table') }}

select
    player_id,
    team_id,
    competition_id,
    season_id,
    mode() within group (order by position) filter (where position is not null) as position_group,
    count(distinct match_id) as appearances,
    count(*) filter (where started) as starts,
    sum(minutes) as minutes_played,
    sum(goals) as goals,
    sum(assists) as assists,
    sum(shots) as shots,
    sum(shots_on_target) as shots_on_target,
    sum(passes) as passes,
    sum(key_passes) as key_passes,
    sum(tackles) as tackles,
    sum(interceptions) as interceptions,
    case when sum(minutes) > 0 then sum(goals) * 90.0 / sum(minutes) end as goals_per_90,
    case when sum(minutes) > 0 then sum(assists) * 90.0 / sum(minutes) end as assists_per_90,
    case when sum(minutes) > 0 then sum(shots) * 90.0 / sum(minutes) end as shots_per_90,
    case when sum(minutes) > 0 then sum(shots_on_target) * 90.0 / sum(minutes) end as shots_on_target_per_90,
    case when sum(minutes) > 0 then sum(passes) * 90.0 / sum(minutes) end as passes_per_90,
    case when sum(minutes) > 0 then sum(key_passes) * 90.0 / sum(minutes) end as key_passes_per_90,
    case when sum(minutes) > 0 then sum(tackles) * 90.0 / sum(minutes) end as tackles_per_90,
    case when sum(minutes) > 0 then sum(interceptions) * 90.0 / sum(minutes) end as interceptions_per_90,
    max(data_as_of) as data_as_of,
    case
        when sum(minutes) < 450 then 'LOW'
        when sum(minutes) < 900 then 'LIMITED'
        else 'STANDARD'
    end as sample_confidence
from {{ source('canonical', 'fact_player_match') }}
group by 1, 2, 3, 4

