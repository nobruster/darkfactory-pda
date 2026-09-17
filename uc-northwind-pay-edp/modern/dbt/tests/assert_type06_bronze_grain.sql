{{ config(tags=['type_06']) }}

select batch_id, source_record_number, count(*) as n
from {{ ref('bronze_merchant_chargeback') }}
group by batch_id, source_record_number
having count(*) > 1
