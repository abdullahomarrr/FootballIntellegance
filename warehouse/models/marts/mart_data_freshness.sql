{{ config(materialized='view') }}

select
    'fact_event'::text as relation_name,
    max(data_as_of) as data_as_of,
    count(*) as row_count,
    case when max(data_as_of) is null then 'NO_DATA' else 'AVAILABLE' end as freshness_status
from {{ source('canonical', 'fact_event') }}
union all
select
    'fact_player_match'::text,
    max(data_as_of),
    count(*),
    case when max(data_as_of) is null then 'NO_DATA' else 'AVAILABLE' end
from {{ source('canonical', 'fact_player_match') }}
