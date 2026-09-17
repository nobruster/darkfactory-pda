{{ config(tags=['type_06']) }}

select batch_id, currency, count(*) as n
from {{ ref('gold_merchant_chargeback_reconciliation') }}
group by batch_id, currency
having count(*) > 1
