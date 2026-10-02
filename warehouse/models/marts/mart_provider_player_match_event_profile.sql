{{ config(materialized='table') }}

select
    event.provider,
    event.provider_match_id,
    event.provider_player_id,
    event.provider_team_id,
    event.player_id,
    player.canonical_name,
    count(*) as event_count,
    count(normalized_x_m) as located_event_count,
    avg(normalized_x_m) as mean_x_m,
    avg(normalized_y_m) as mean_y_m,
    count(*) filter (where event_type = 'Pass') as passes,
    count(*) filter (where event_type = 'Carry') as carries,
    count(*) filter (where event_type = 'Dribble') as dribbles,
    count(*) filter (where event_type = 'Shot') as shots,
    sum(shot_xg) as shot_xg,
    max(data_as_of) as data_as_of,
    case when event.player_id is null
        then 'PROVIDER_UNRESOLVED'
        else 'CANONICAL_SINGLE_PROVIDER'
    end as identity_status
from {{ source('canonical', 'fact_event') }} event
left join {{ source('canonical', 'dim_player') }} player on event.player_id = player.player_id
where event.provider_player_id is not null
group by 1, 2, 3, 4, 5, 6

