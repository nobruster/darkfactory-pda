{{ config(tags=['type_06']) }}

{{ release_gate(
    ref('gold_merchant_chargeback_reconciliation'),
    ['count_delta', 'original_amount_delta', 'chargeback_amount_delta', 'calculated_amount_delta']
) }}
