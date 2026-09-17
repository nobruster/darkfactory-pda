{{ config(tags=['type_06']) }}

-- Bronze controls: source-owned declaration plus independently computed totals.

select
    batch_id,
    type_number,
    contract_code,
    currency,
    cast(declared_detail_count as integer)                 as declared_detail_count,
    cast(computed_detail_count as integer)                 as computed_detail_count,
    cast(declared_original_amount as decimal(18, 2))       as declared_original_amount,
    cast(computed_original_amount as decimal(18, 2))       as computed_original_amount,
    cast(declared_chargeback_amount as decimal(18, 2))     as declared_chargeback_amount,
    cast(computed_chargeback_amount as decimal(18, 2))     as computed_chargeback_amount,
    cast(declared_calculated_amount as decimal(18, 2))     as declared_calculated_amount,
    cast(computed_calculated_amount as decimal(18, 2))     as computed_calculated_amount,
    rounding_mode,
    cast(record_count as integer)                          as record_count,
    raw_sha256,
    parquet_sha256,
    source_file
from {{ source('landing', 'merchant_chargeback_control') }}
