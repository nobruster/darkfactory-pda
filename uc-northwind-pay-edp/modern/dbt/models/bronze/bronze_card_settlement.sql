{{ config(tags=['type_01']) }}

-- Bronze: typed and source-aligned. Grain: (batch_id, source_record_number).
-- Does not re-parse. Privacy already applied at the parser.

select
    batch_id,
    source_file,
    cast(source_record_number as integer)      as source_record_number,
    transaction_id,
    merchant_id,
    card_token,
    card_last4,
    cpf_masked,
    transaction_ts,
    cast(amount_brl as decimal(18, 2))         as amount_brl,
    movement_code,
    authorization_code,
    nsu,
    terminal_id
from {{ source('landing', 'card_settlement') }}
