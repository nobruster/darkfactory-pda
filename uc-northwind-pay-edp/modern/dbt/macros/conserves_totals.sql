{% macro conserves_totals(bronze_relation, silver_relation, amount_columns) %}

{%- set aggregates -%}
count(*) as row_count
{%- for column in amount_columns -%}
, sum({{ column }}) as sum_{{ column }}
{%- endfor -%}
{%- endset -%}

with bronze as (
    select batch_id, {{ aggregates }}
    from {{ bronze_relation }}
    group by batch_id
),

silver as (
    select batch_id, {{ aggregates }}
    from {{ silver_relation }}
    group by batch_id
)

select coalesce(bronze.batch_id, silver.batch_id) as batch_id
from bronze
full outer join silver on silver.batch_id = bronze.batch_id
where bronze.row_count is distinct from silver.row_count
{%- for column in amount_columns %}
   or bronze.sum_{{ column }} is distinct from silver.sum_{{ column }}
{%- endfor %}

{% endmacro %}
