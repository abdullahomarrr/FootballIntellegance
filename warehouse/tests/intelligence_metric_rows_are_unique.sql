select player_id, team_id, competition_id, season_id, metric_name, count(*) as row_count
from {{ ref('mart_player_intelligence_metric_percentile') }}
group by player_id, team_id, competition_id, season_id, metric_name
having count(*) > 1
