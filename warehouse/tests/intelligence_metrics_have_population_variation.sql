select comparison_scope, competition_id, season_id, provider_pool::text, position_group, metric_name
from {{ ref('mart_player_intelligence_metric_percentile') }}
where comparison_scope = 'COMPETITION_SEASON'
group by comparison_scope, competition_id, season_id, provider_pool, position_group, metric_name
having max(metric_value) = min(metric_value)
union all
select comparison_scope, null::bigint, null::bigint, provider_pool::text, position_group, metric_name
from {{ ref('mart_player_intelligence_metric_percentile') }}
where comparison_scope = 'POOLED_PROVIDER_POSITION'
group by comparison_scope, provider_pool, position_group, metric_name
having max(metric_value) = min(metric_value)
