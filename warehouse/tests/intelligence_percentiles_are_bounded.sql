select player_id, competition_id, season_id, position_group, metric_name, percentile
from {{ ref('mart_player_intelligence_metric_percentile') }}
where percentile < 0 or percentile > 100
