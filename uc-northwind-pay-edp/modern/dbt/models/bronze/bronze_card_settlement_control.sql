{{ config(tags=['type_01']) }}

-- Bronze controls: source-owned declaration plus independently computed totals.

select
    batch_id,
    type_number,
    contract_code,
    currency,
    cast(declared_detail_count as integer)          as declared_detail_count,
    cast(computed_detail_count as integer)          as computed_detail_count,
    cast(declared_net_amount as decimal(18, 2))     as declared_net_amount,
    cast(computed_net_amount as decimal(18, 2))     as computed_net_amount,
    cast(record_count as integer)                   as record_count,
    raw_sha256,
    parquet_sha256,
    source_file
from {{ source('landing', 'card_settlement_control') }}
