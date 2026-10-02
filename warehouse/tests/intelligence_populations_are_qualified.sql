select player_id, competition_id, season_id, position_group, metric_name, comparison_population
from {{ ref('mart_player_intelligence_metric_percentile') }}
where comparison_population < 15
