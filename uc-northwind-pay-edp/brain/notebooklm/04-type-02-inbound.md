# Pack 04 — Type 02 inbound (instant payment / PIX)

What we mailed for Type `02`. Pipes, escapes, offsets. Same shape of lie as Type 01.
The raw samples and expected/ oracles are not in this pack.



---

## Source: `spec/type-02-instant-payment-events/README.md`

# Instant Payment Events — inbound pack

**Type `02` · `PIX_EVENTS01` · `.txt` · UTF-8 pipes, escapes, offsets**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `173.45` |
| `valid-boundary` | Boundary | accepted |
| `escaped-content` | Type edge | accepted |
| `malformed` | Grammar | `INVALID_FIELD_COUNT` |
| `df-source-002` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `173.44` vs `173.45` |

Estate: [`../estate/`](../estate/README.md).


---

## Source: `spec/type-02-instant-payment-events/inbound/2026-07-01-pipes-never-escaped.md`

# pipes

**From:** Rafael Costa  
**Date:** 2026-07-01

For what it is worth — we do not escape pipes. If someone put a `|`
in a description they would have broken the old importer years ago.

(Helena’s folder still has a file named `escaped-content`. I have not
opened it.)


---

## Source: `spec/type-02-instant-payment-events/inbound/instant-payment-layout.md`

# Instant Payment Events — layout (PIX-like)

**Code:** `PIX_EVENTS01` · layout `001`  
**Filename:** `NW_INSTANT_PAYMENT_YYYYMMDD_B###############.txt`  
**Encoding:** UTF-8 · **EOL:** LF · no BOM

Delimiter `|`. Legal escapes: `\|` and `\\` only. Header / events /
trailer.

Header fields (pipe-separated): record type `H`, file date, batch id,
`PIX_EVENTS01`, `001`, timezone context `America/Sao_Paulo`.

Event: type `E`, event id, direction `C`/`D`, amount (positive in the
file; sign is applied from direction), payer document, payee document,
timestamp with explicit offset, status, optional return code, NFC
description ≤ 80 code points.

Trailer: type `T`, event count, credit total, debit total, **net**,
returned count.

Documents are CPF (11) or CNPJ (14). Tokenize. Amounts exact decimal.
Timestamps must land on the header date in São Paulo.


---

## Source: `spec/type-02-instant-payment-events/inbound/instant-payment-table-definitions.txt`

-- staging.instant_payment_event   dump 2026-06-19
CREATE TABLE staging.instant_payment_event (
    batch_id             char(16)       NOT NULL,
    source_record_number int            NOT NULL,
    event_id             varchar(32)    NOT NULL,
    direction            char(1)        NOT NULL,
    amount_brl           decimal(18,2)  NOT NULL,
    payer_doc_token      varchar(40)    NOT NULL,
    payer_doc_masked     varchar(20)    NOT NULL,
    payee_doc_token      varchar(40)    NOT NULL,
    payee_doc_masked     varchar(20)    NOT NULL,
    event_ts             datetimeoffset NOT NULL,
    status               varchar(16)    NOT NULL,
    return_code          varchar(16)    NULL,
    description          nvarchar(80)   NOT NULL,
    -- requested by ops for a memo report that never shipped
    event_memo           nvarchar(200)  NULL,
    PRIMARY KEY (batch_id, source_record_number)
)
GO


---

## Source: `spec/type-02-instant-payment-events/inbound/usp_apply_instant_payment.sql`

-- legacy.apply_instant_payment_batch
-- dump 2026-06-21. Does not touch event_memo.
CREATE PROCEDURE legacy.apply_instant_payment_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.instant_payment_event
    SELECT batch_id, source_record_number, event_id, direction, amount_brl,
           payer_doc_token, payer_doc_masked, payee_doc_token, payee_doc_masked,
           event_ts, status, return_code, description
    FROM staging.instant_payment_event
    WHERE batch_id = @batch_id
END
GO
