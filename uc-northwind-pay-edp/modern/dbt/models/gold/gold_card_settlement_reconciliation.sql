{{ config(tags=['type_01']) }}

-- Gold: governed reconciliation, one row per (batch_id, currency).
-- source_* is the declaration. staged_* is Bronze. applied_* is Silver.
-- Legacy warehouse state is observation only, never an input.

with control as (
    select * from {{ ref('bronze_card_settlement_control') }}
),

staged as (
    select
        batch_id,
        count(*)                                as staged_count,
        coalesce(sum(amount_brl), 0.00)         as staged_net_amount
    from {{ ref('bronze_card_settlement') }}
    group by batch_id
),

applied as (
    select
        batch_id,
        count(*)                                as applied_count,
        coalesce(sum(amount_brl), 0.00)         as applied_net_amount
    from {{ ref('silver_card_settlement') }}
    group by batch_id
)

select
    control.batch_id,
    control.currency,
    control.declared_detail_count                                   as source_count,
    staged.staged_count,
    applied.applied_count,
    control.declared_net_amount                                     as source_net_amount,
    cast(staged.staged_net_amount as decimal(18, 2))                as staged_net_amount,
    cast(applied.applied_net_amount as decimal(18, 2))              as applied_net_amount,
    applied.applied_count - control.declared_detail_count           as count_delta,
    cast(
        applied.applied_net_amount - control.declared_net_amount
        as decimal(18, 2)
    )                                                               as amount_delta,
    0                                                               as reject_count,
    case
        when applied.applied_count = control.declared_detail_count
         and applied.applied_net_amount = control.declared_net_amount
         and staged.staged_count = control.declared_detail_count
         and staged.staged_net_amount = control.declared_net_amount
        then 'MATCHED'
        else 'MISMATCHED'
    end                                                             as status
from control
join staged   on staged.batch_id   = control.batch_id
join applied  on applied.batch_id  = control.batch_id
