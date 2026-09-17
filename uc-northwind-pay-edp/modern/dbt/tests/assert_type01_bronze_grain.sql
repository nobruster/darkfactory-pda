{{ config(tags=['type_01']) }}

select batch_id, source_record_number, count(*) as n
from {{ ref('bronze_card_settlement') }}
group by batch_id, source_record_number
having count(*) > 1
