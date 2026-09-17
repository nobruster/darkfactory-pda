{{ config(tags=['type_06']) }}

{{ conserves_totals(
    ref('bronze_merchant_chargeback'),
    ref('silver_merchant_chargeback'),
    ['original_amount_brl', 'chargeback_amount_brl', 'calculated_amount_brl']
) }}
