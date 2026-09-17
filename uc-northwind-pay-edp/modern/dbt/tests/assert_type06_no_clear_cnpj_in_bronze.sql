{{ config(tags=['type_06']) }}

select *
from {{ ref('bronze_merchant_chargeback') }}
where regexp_matches(merchant_tax_id_masked, '^[0-9]{14}$')
   or not regexp_matches(merchant_tax_id_masked, '^\*{10}[0-9]{4}$')
   or rounding_mode <> 'HALF_UP'
