{{ config(tags=['type_01']) }}

{{ conserves_totals(
    ref('bronze_card_settlement'),
    ref('silver_card_settlement'),
    ['amount_brl']
) }}
