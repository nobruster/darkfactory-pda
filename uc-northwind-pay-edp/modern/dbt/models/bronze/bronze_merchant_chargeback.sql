{{ config(tags=['type_06']) }}

-- Bronze: typed and source-aligned. Grain: (batch_id, source_record_number).
-- Does not re-parse. Privacy and HALF_UP already applied at the parser.

select
    batch_id,
    source_file,
    cast(source_record_number as integer)              as source_record_number,
    chargeback_id,
    merchant_id,
    merchant_tax_id_masked,
    reason_code,
    description,
    cast(original_amount_brl as decimal(18, 2))        as original_amount_brl,
    cast(rate_percent as decimal(9, 3))                as rate_percent,
    cast(chargeback_amount_brl as decimal(18, 2))      as chargeback_amount_brl,
    cast(calculated_amount_brl as decimal(18, 2))      as calculated_amount_brl,
    business_date,
    rounding_mode
from {{ source('landing', 'merchant_chargeback') }}
