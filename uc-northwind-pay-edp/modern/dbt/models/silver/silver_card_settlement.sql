{{ config(tags=['type_01']) }}

-- Silver: conformed entity at the same grain as Bronze. Changes no monetary value.

select
    batch_id,
    source_record_number,
    transaction_id,
    merchant_id,
    card_token,
    card_last4,
    cpf_masked,
    transaction_ts,
    amount_brl,
    movement_code,
    case movement_code
        when 'P' then 'PURCHASE'
        when 'R' then 'REFUND'
    end                                                as movement_direction,
    authorization_code,
    nsu,
    terminal_id,
    source_file
from {{ ref('bronze_card_settlement') }}
