{{ config(tags=['type_01']) }}

{{ release_gate(ref('gold_card_settlement_reconciliation'), ['count_delta', 'amount_delta']) }}
