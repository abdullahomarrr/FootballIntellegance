{{ config(materialized='table') }}

with event_profile as (
    select
        event.player_id,
        event.team_id,
        match.competition_id,
        match.season_id,
        count(*) as event_count,
        bool_or(event.provider = 'statsbomb_open') as has_statsbomb_events,
        bool_or(event.provider = 'wyscout_open') as has_wyscout_events,
        count(event.normalized_x_m) as located_event_count,
        count(*) filter (where event.event_type = 'Pass') as passes_attempted,
        count(*) filter (
            where event.event_type = 'Pass'
              and (
                (event.provider = 'statsbomb_open' and event.outcome is null)
                or (event.provider = 'wyscout_open' and event.qualifiers @> '{"tags":[{"id":1801}]}'::jsonb)
              )
        ) as passes_completed,
        count(*) filter (where event.event_type = 'Pass' and (event.qualifiers->>'under_pressure')::boolean) as pressured_passes,
        count(*) filter (
            where event.event_type = 'Pass'
              and (event.qualifiers->>'under_pressure')::boolean
              and event.outcome is null
        ) as pressured_passes_completed,
        count(*) filter (
            where event.event_type = 'Pass'
              and event.normalized_end_x_m - event.normalized_x_m >= 10
        ) as progressive_passes,
        count(*) filter (
            where event.event_type = 'Pass'
              and event.normalized_end_x_m >= 70
              and event.normalized_x_m < 70
        ) as passes_into_final_third,
        count(*) filter (
            where event.event_type in ('Pass', 'Carry')
              and event.normalized_end_x_m >= 88.5
              and event.normalized_end_y_m between 13.6 and 54.4
              and not (
                event.normalized_x_m >= 88.5
                and event.normalized_y_m between 13.6 and 54.4
              )
        ) as box_entries,
        count(*) filter (where event.event_type = 'Carry') as carries,
        count(*) filter (
            where event.event_type = 'Carry'
              and event.normalized_end_x_m - event.normalized_x_m >= 10
        ) as progressive_carries,
        count(*) filter (where event.event_type = 'Dribble') as dribbles_attempted,
        count(*) filter (
            where event.event_type = 'Dribble'
              and (
                (event.provider = 'statsbomb_open' and event.outcome = 'Complete')
                or (event.provider = 'wyscout_open' and event.qualifiers @> '{"tags":[{"id":1801}]}'::jsonb)
              )
        ) as dribbles_completed,
        count(*) filter (where event.event_type = 'Pressure') as pressures,
        count(*) filter (where event.event_type = 'Ball Recovery') as recoveries,
        count(*) filter (where event.event_type = 'Interception') as event_interceptions,
        count(*) filter (where event.event_type = 'Block') as blocks,
        count(*) filter (where event.event_type = 'Clearance') as clearances,
        count(*) filter (
            where event.event_type = 'Duel'
              and (
                lower(coalesce(event.event_subtype, '')) like '%defending%'
                or (event.provider = 'statsbomb_open' and event.event_subtype = 'Tackle')
              )
        ) as defensive_duels,
        count(*) filter (where event.event_type in ('Miscontrol', 'Dispossessed')) as turnovers,
        count(*) filter (where event.event_type = 'Shot') as event_shots,
        count(event.shot_xg) filter (where event.event_type = 'Shot') as xg_shot_count,
        sum(event.shot_xg) filter (where event.event_type = 'Shot') as shot_xg,
        count(*) filter (
            where event.event_type = 'Goal Keeper'
              and event.qualifiers->'goalkeeper'->'type'->>'name' in (
                'Shot Saved', 'Shot Saved Off Target', 'Shot Saved to Post',
                'Save', 'Penalty Saved', 'Penalty Saved to Post', 'Saved to Post'
              )
        ) + count(*) filter (where event.event_type = 'Save attempt') as goalkeeper_saves,
        count(*) filter (where event.event_type = 'Goal Keeper') as goalkeeper_detail_events,
        count(*) filter (where event.event_type = 'Save attempt') as save_attempt_events,
        count(*) filter (where event.event_type = 'Goalkeeper leaving line') as leaving_line_events,
        count(*) filter (
            where event.event_type = 'Goal Keeper'
              and event.qualifiers->'goalkeeper'->'type'->>'name' = 'Goal Conceded'
        ) as goals_conceded,
        count(*) filter (
            where event.event_type = 'Goal Keeper'
              and event.qualifiers->'goalkeeper'->'type'->>'name' in ('Collected', 'Punch', 'Smother')
        ) as claims_and_punches,
        count(*) filter (
            where (event.event_type = 'Goal Keeper'
              and event.qualifiers->'goalkeeper'->'type'->>'name' = 'Keeper Sweeper')
              or event.event_type = 'Goalkeeper leaving line'
        ) as sweeper_actions,
        sum(
            {{ xt_value('event.normalized_end_x_m', 'event.normalized_end_y_m') }}
            - {{ xt_value('event.normalized_x_m', 'event.normalized_y_m') }}
        ) filter (
            where event.normalized_x_m is not null and event.normalized_end_x_m is not null
              and event.normalized_y_m is not null and event.normalized_end_y_m is not null
              and (
                event.event_type = 'Carry'
                or (event.event_type = 'Pass' and {{ completed_pass('event') }})
              )
        ) as xt_added,
        count(*) filter (
            where event.event_type = 'Pass'
              and event.normalized_end_x_m is not null
              and sqrt(power(event.normalized_end_x_m - event.normalized_x_m, 2)
                     + power(event.normalized_end_y_m - event.normalized_y_m, 2)) >= 35
        ) as long_passes,
        count(*) filter (
            where event.event_type = 'Pass'
              and event.normalized_end_x_m is not null
              and sqrt(power(event.normalized_end_x_m - event.normalized_x_m, 2)
                     + power(event.normalized_end_y_m - event.normalized_y_m, 2)) >= 35
              and {{ completed_pass('event') }}
        ) as long_passes_completed,
        max(event.data_as_of) as event_data_as_of
    from {{ source('canonical', 'fact_event') }} event
    join {{ source('canonical', 'dim_match') }} match using (match_id)
    where event.player_id is not null and event.team_id is not null
    group by 1, 2, 3, 4
)

select
    profile.*,
    coalesce(event.event_count, 0) as event_count,
    coalesce(event.located_event_count, 0) as located_event_count,
    coalesce(event.passes_attempted, 0) as passes_attempted,
    coalesce(event.passes_completed, 0) as passes_completed,
    case when event.passes_attempted > 0 then event.passes_completed * 100.0 / event.passes_attempted end as pass_completion_pct,
    case when event.pressured_passes > 0 then event.pressured_passes_completed * 100.0 / event.pressured_passes end as pressured_pass_completion_pct,
    event.progressive_passes * 90.0 / nullif(profile.minutes_played, 0) as progressive_passes_per_90,
    event.passes_into_final_third * 90.0 / nullif(profile.minutes_played, 0) as passes_into_final_third_per_90,
    event.box_entries * 90.0 / nullif(profile.minutes_played, 0) as box_entries_per_90,
    case when event.has_statsbomb_events then event.carries * 90.0 / nullif(profile.minutes_played, 0) end as carries_per_90,
    case when event.has_statsbomb_events then event.progressive_carries * 90.0 / nullif(profile.minutes_played, 0) end as progressive_carries_per_90,
    case when event.has_statsbomb_events and event.dribbles_attempted > 0 then event.dribbles_completed * 100.0 / event.dribbles_attempted end as dribble_success_pct,
    case when event.has_statsbomb_events then event.dribbles_completed * 90.0 / nullif(profile.minutes_played, 0) end as successful_dribbles_per_90,
    case when event.has_statsbomb_events then event.pressures * 90.0 / nullif(profile.minutes_played, 0) end as pressures_per_90,
    case when event.has_statsbomb_events then event.recoveries * 90.0 / nullif(profile.minutes_played, 0) end as recoveries_per_90,
    case when event.has_statsbomb_events then event.event_interceptions * 90.0 / nullif(profile.minutes_played, 0) end as event_interceptions_per_90,
    (profile.tackles + profile.interceptions) * 90.0 / nullif(profile.minutes_played, 0) as defensive_actions_per_90,
    event.defensive_duels * 90.0 / nullif(profile.minutes_played, 0) as defensive_duels_per_90,
    case when event.has_statsbomb_events then event.turnovers * 90.0 / nullif(profile.minutes_played, 0) end as turnovers_per_90,
    event.xt_added * 90.0 / nullif(profile.minutes_played, 0) as xt_added_per_90,
    case when event.xg_shot_count > 0 then event.shot_xg * 90.0 / nullif(profile.minutes_played, 0) end as xg_per_90,
    case when event.xg_shot_count > 0 then event.shot_xg / event.xg_shot_count end as average_shot_xg,
    case when event.goalkeeper_detail_events + event.save_attempt_events > 0
      then event.goalkeeper_saves * 90.0 / nullif(profile.minutes_played, 0) end as goalkeeper_saves_per_90,
    case when event.goalkeeper_detail_events > 0
      then event.goals_conceded * 90.0 / nullif(profile.minutes_played, 0) end as goals_conceded_per_90,
    case when event.goalkeeper_detail_events > 0
      then event.claims_and_punches * 90.0 / nullif(profile.minutes_played, 0) end as claims_and_punches_per_90,
    case when event.goalkeeper_detail_events > 0 and event.goalkeeper_saves + event.goals_conceded > 0
      then event.goalkeeper_saves * 100.0 / (event.goalkeeper_saves + event.goals_conceded) end as goalkeeper_save_pct,
    case when event.long_passes >= 20 then event.long_passes_completed * 100.0 / event.long_passes end as goalkeeper_long_pass_pct,
    case when event.goalkeeper_detail_events + event.leaving_line_events > 0
      then event.sweeper_actions * 90.0 / nullif(profile.minutes_played, 0) end as sweeper_actions_per_90,
    event.xg_shot_count,
    coalesce(event.has_statsbomb_events, false) as has_statsbomb_events,
    coalesce(event.has_wyscout_events, false) as has_wyscout_events,
    greatest(profile.data_as_of, event.event_data_as_of) as intelligence_data_as_of,
    'event_intelligence_v1'::text as feature_set_version
from {{ ref('mart_player_season_profile') }} profile
left join event_profile event using (player_id, team_id, competition_id, season_id)
