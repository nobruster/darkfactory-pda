# Pack 06 — Type 04 inbound (TED)

What we mailed for Type `04`. Mixed widths, inherited returns, two dated procs.
The raw samples and expected/ oracles are not in this pack.



---

## Source: `spec/type-04-ted-transfer-settlement/README.md`

# TED Transfer Settlement — inbound pack

**Type `04` · `TED_SETTLE04` · `.dat` · mixed widths, inherited returns**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `1000.00` |
| `valid-boundary` | Boundary | accepted |
| `all-returned-zero-net` | Type edge | accepted · net `0.00` |
| `malformed` | Grammar | `INVALID_TRANSPORT` |
| `df-source-004` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `999.99` vs `1000.00` |

Estate: [`../estate/`](../estate/README.md).


---

## Source: `spec/type-04-ted-transfer-settlement/inbound/2026-07-05-returns-optional.md`

# RT records

**From:** Rafael Costa  
**Date:** 2026-07-05

If a transfer is `RT` and the return line is missing I used to just
skip it and post the transfer. Optional, basically.

(Layout in this folder says `RT` requires the next record to be `R`.
The April proc also drops returns on apply. June proc keeps them.
I would not ship the April one.)


---

## Source: `spec/type-04-ted-transfer-settlement/inbound/ted-layout.md`

# TED settlement — mixed record lengths

**Code:** `TED_SETTLE04` · layout `001`  
**Filename:** `NW_TED_SETTLEMENT_YYYYMMDD_B###############.dat`  
**Encoding:** US-ASCII · **EOL:** exact CRLF after every record

Lengths **excluding** CRLF: `H=56` · `D=162` · `R=91` · `T=82`

Sequence: `H (D | D R)+ T`  
`D.status_code = OK` forbids a following `R`.  
`D.status_code = RT` **requires** the next record to be the matching
full return. Amount sign and magnitude are separate fields.

Trailer declares transfer count, return count, gross, returned, net.
The lie file gets counts and gross/returned right and misses net by
one cent (`999.99` vs `1000.00`).


---

## Source: `spec/type-04-ted-transfer-settlement/inbound/ted-table-definitions.txt`

-- staging.ted_transfer_movement  dump 2026-06-20
CREATE TABLE staging.ted_transfer_movement (
    batch_id             char(16)      NOT NULL,
    source_record_number int           NOT NULL,
    movement_kind        varchar(8)    NOT NULL, -- TRANSFER | RETURN
    status_code          char(2)       NOT NULL,
    amount_brl           decimal(18,2) NOT NULL,
    payer_account_token  varchar(40)   NOT NULL,
    bene_account_token   varchar(40)   NOT NULL,
    tax_id_masked        varchar(20)   NOT NULL,
    occurred_ts          datetimeoffset NOT NULL,
    return_of            varchar(32)   NULL,
    PRIMARY KEY (batch_id, source_record_number)
)
GO


---

## Source: `spec/type-04-ted-transfer-settlement/inbound/usp_apply_ted_20260418.sql`

-- dump 2026-04-18  — transfers only, ignored returns
CREATE PROCEDURE legacy.apply_ted_transfer_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.ted_transfer_movement
    SELECT * FROM staging.ted_transfer_movement
    WHERE batch_id = @batch_id
      AND movement_kind = 'TRANSFER'
END
GO


---

## Source: `spec/type-04-ted-transfer-settlement/inbound/usp_apply_ted_20260620.sql`

-- dump 2026-06-20  — Rafael: current. April script drops returns.
CREATE PROCEDURE legacy.apply_ted_transfer_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.ted_transfer_movement
    SELECT * FROM staging.ted_transfer_movement
    WHERE batch_id = @batch_id
END
GO
