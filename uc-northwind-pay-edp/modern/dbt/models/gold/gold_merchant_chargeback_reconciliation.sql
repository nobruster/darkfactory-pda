{{ config(tags=['type_06']) }}

-- Gold: governed reconciliation, one row per (batch_id, currency).
-- source_* is the declaration. staged_* is Bronze. applied_* is Silver.
-- Legacy warehouse state is observation only, never an input.

with control as (
    select * from {{ ref('bronze_merchant_chargeback_control') }}
),

staged as (
    select
        batch_id,
        count(*)                                              as staged_count,
        coalesce(sum(original_amount_brl), 0.00)             as staged_original_amount,
        coalesce(sum(chargeback_amount_brl), 0.00)           as staged_chargeback_amount,
        coalesce(sum(calculated_amount_brl), 0.00)           as staged_calculated_amount
    from {{ ref('bronze_merchant_chargeback') }}
    group by batch_id
),

applied as (
    select
        batch_id,
        count(*)                                              as applied_count,
        coalesce(sum(original_amount_brl), 0.00)             as applied_original_amount,
        coalesce(sum(chargeback_amount_brl), 0.00)           as applied_chargeback_amount,
        coalesce(sum(calculated_amount_brl), 0.00)           as applied_calculated_amount
    from {{ ref('silver_merchant_chargeback') }}
    group by batch_id
)

select
    control.batch_id,
    control.currency,
    control.declared_detail_count                                          as source_count,
    staged.staged_count,
    applied.applied_count,
    control.declared_original_amount                                       as source_original_amount,
    cast(staged.staged_original_amount as decimal(18, 2))                  as staged_original_amount,
    cast(applied.applied_original_amount as decimal(18, 2))                as applied_original_amount,
    control.declared_chargeback_amount                                     as source_chargeback_amount,
    cast(staged.staged_chargeback_amount as decimal(18, 2))                as staged_chargeback_amount,
    cast(applied.applied_chargeback_amount as decimal(18, 2))              as applied_chargeback_amount,
    control.declared_calculated_amount                                     as source_calculated_amount,
    cast(staged.staged_calculated_amount as decimal(18, 2))                as staged_calculated_amount,
    cast(applied.applied_calculated_amount as decimal(18, 2))              as applied_calculated_amount,
    applied.applied_count - control.declared_detail_count                  as count_delta,
    cast(
        applied.applied_original_amount - control.declared_original_amount
        as decimal(18, 2)
    )                                                                      as original_amount_delta,
    cast(
        applied.applied_chargeback_amount - control.declared_chargeback_amount
        as decimal(18, 2)
    )                                                                      as chargeback_amount_delta,
    cast(
        applied.applied_calculated_amount - control.declared_calculated_amount
        as decimal(18, 2)
    )                                                                      as calculated_amount_delta,
    0                                                                      as reject_count,
    case
        when applied.applied_count = control.declared_detail_count
         and applied.applied_original_amount = control.declared_original_amount
         and applied.applied_chargeback_amount = control.declared_chargeback_amount
         and applied.applied_calculated_amount = control.declared_calculated_amount
         and staged.staged_count = control.declared_detail_count
         and staged.staged_original_amount = control.declared_original_amount
         and staged.staged_chargeback_amount = control.declared_chargeback_amount
         and staged.staged_calculated_amount = control.declared_calculated_amount
        then 'MATCHED'
        else 'MISMATCHED'
    end                                                                    as status
from control
join staged   on staged.batch_id   = control.batch_id
join applied  on applied.batch_id  = control.batch_id
