{{ config(tags=['type_01']) }}

select *
from {{ ref('bronze_card_settlement') }}
where regexp_matches(card_token, '^[0-9]{16}$')
   or regexp_matches(card_last4, '^[0-9]{5,}$')
   or not regexp_matches(card_token, '^tok_[0-9a-f]{24}$')
   or not regexp_matches(cpf_masked, '^\*{7}[0-9]{4}$')
