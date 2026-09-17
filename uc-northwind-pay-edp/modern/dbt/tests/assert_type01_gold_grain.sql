{{ config(tags=['type_01']) }}

select batch_id, currency, count(*) as n
from {{ ref('gold_card_settlement_reconciliation') }}
group by batch_id, currency
having count(*) > 1
