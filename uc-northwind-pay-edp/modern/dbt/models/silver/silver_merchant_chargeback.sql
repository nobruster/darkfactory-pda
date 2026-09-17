{{ config(tags=['type_06']) }}

-- Silver: same grain as Bronze. Changes no monetary value. Does not re-round.

select
    batch_id,
    source_record_number,
    chargeback_id,
    merchant_id,
    merchant_tax_id_masked,
    reason_code,
    description,
    original_amount_brl,
    rate_percent,
    chargeback_amount_brl,
    calculated_amount_brl,
    business_date,
    rounding_mode,
    source_file
from {{ ref('bronze_merchant_chargeback') }}
