{# Versioned location-value baseline (xt_location_baseline_v1), mirrored from expected_threat.py. #}
{% macro xt_value(x, y) -%}
(power(({{ x }}) / 105.0, 3) * (0.65 + 0.35 * (1 - abs(({{ y }}) - 34) / 34.0)))
{%- endmacro %}

{% macro completed_pass(event) -%}
(({{ event }}.provider = 'statsbomb_open' and {{ event }}.outcome is null)
 or ({{ event }}.provider = 'wyscout_open' and {{ event }}.qualifiers @> '{"tags":[{"id":1801}]}'::jsonb))
{%- endmacro %}
