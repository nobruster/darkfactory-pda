{% macro release_gate(relation, delta_columns) %}

select *
from {{ relation }}
where status <> 'MATCHED'
{%- for column in delta_columns %}
   or {{ column }} <> 0
{%- endfor %}

{% endmacro %}
