# Pack 03 — Type 01 inbound (card settlement)

What we mailed for Type `01`. Day 1 steel thread. Capture starts here. Do not open Java for the answer.
The raw samples and expected/ oracles are not in this pack.



---

## Source: `spec/type-01-card-settlement/README.md`

# Card Settlement Detail — inbound pack

**Type `01` · `CRD_SETTLE01` · `.dat` · ISO-8859-1 fixed width, COBOL overpunch**

What we mailed. Start at `inbound/`, hash `samples/`, adjudicate with
`expected/`. Do not open Java for the answer.

| Folder | Contents |
|---|---|
| [`inbound/`](inbound/) | Layout rev 3, table dump, two dated procs, walk-through, ops noun |
| [`samples/`](samples/) | Five raw files + SHA-256 |
| [`expected/`](expected/) | Sanitized + recon for accepted; refusals for malformed and the lie |

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `173.45` |
| `valid-boundary` | Boundary | accepted |
| `negative-overpunch` | Type edge | accepted · net `-12.34` |
| `malformed` | Grammar | `INVALID_OVERPUNCH` |
| `df-source-001` | Source lie | `SOURCE_CONTROL_TOTAL_MISMATCH` · declared `173.44` · computed `173.45` |

Estate context: [`../estate/`](../estate/README.md).


---

## Source: `spec/type-01-card-settlement/inbound/2026-06-30-walkthrough.md`

# Card settlement walk-through

**Date:** 2026-06-30  
**Type:** Document Review  
**Attendees:** Rafael Costa · Helena Dias

Rafael walked the 124-byte detail and the overpunch table. He said the
May proc is still in the share “because SSMS dumps the object history
wrong.” Use the 1 Jul script.

`chargeback_flag` on the table is dead. Do not put it in Gold.

Open: Marina still calls trailer field 16–30 the **settlement total**.
The layout calls it **net amount**. Same number.


---

## Source: `spec/type-01-card-settlement/inbound/2026-07-02-settlement-total.md`

# Re: settlement total vs net

**From:** Marina Alves  
**Date:** 2026-07-02

Please put **settlement total** on the recon report. That is what the
ops dashboard has said for six years. I do not care what the layout
PDF calls bytes 16–30.

The lie file is the one where settlement total is 173.44 and the
details are 173.45. Do not “correct” the trailer.


---

## Source: `spec/type-01-card-settlement/inbound/card-settlement-layout-rev3.md`

# NW Card Settlement — File Layout Revision 3

**Issuer:** NorthWind Pay Acquiring  
**Code:** `CRD_SETTLE01` · layout `001`  
**Filename:** `NW_CARD_SETTLEMENT_YYYYMMDD_B###############.dat`  
**Encoding:** ISO-8859-1 · **EOL:** LF · blank lines not allowed

One header, one or more details, one trailer. Positions are **1-based**.

## Header — 40 bytes · `H`

| Pos | Len | Field |
|---:|---:|---|
| 1 | 1 | `H` |
| 2–9 | 8 | File date `yyyyMMdd` |
| 10–25 | 16 | Batch `B` + 15 digits |
| 26–37 | 12 | `CRD_SETTLE01` |
| 38–40 | 3 | `001` |

## Detail — 124 bytes · `D`

| Pos | Len | Field |
|---:|---:|---|
| 1 | 1 | `D` |
| 2–17 | 16 | Transaction id |
| 18–33 | 16 | Merchant id |
| 34–49 | 16 | PAN (clear in this file — tokenize) |
| 50–60 | 11 | CPF (clear — mask) |
| 61–68 | 8 | Tran date |
| 69–74 | 6 | Tran time `HHmmss` |
| 75–86 | 12 | Amount, COBOL overpunch, scale 2 |
| 87–89 | 3 | `BRL` |
| 90 | 1 | Movement `P` purchase / `R` refund |
| 91–96 | 6 | Auth code |
| 97–108 | 12 | NSU |
| 109–124 | 16 | Terminal |

Overpunch (last character): `{ABCDEFGHI` = +0..+9, `}JKLMNOPQR` = −0..−9.  
Example: `00000001234E` → `123.45`. `00000000123M` → `-12.34`.

`P` must be strictly positive. `R` must be strictly negative.

## Trailer — 46 bytes · `T`

| Pos | Len | Field |
|---:|---:|---|
| 1 | 1 | `T` |
| 2–9 | 8 | File date (must match header) |
| 10–15 | 6 | Detail count |
| 16–30 | 15 | **Net amount** overpunch (must equal sum of details) |
| 31–46 | 16 | Batch (must match header) |

Filename date, header date, trailer date, and the date inside the batch
id must agree.


---

## Source: `spec/type-01-card-settlement/inbound/card-settlement-table-definitions.txt`

-- SSMS dump 2026-06-18  Rafael Costa
-- staging.card_settlement  +  legacy.card_settlement

CREATE TABLE staging.card_settlement (
    batch_id              char(16)       NOT NULL,
    source_file           varchar(128)   NOT NULL,
    source_record_number  int            NOT NULL,
    transaction_id        char(16)       NOT NULL,
    merchant_id           char(16)       NOT NULL,
    card_token            varchar(32)    NOT NULL,
    card_last4            char(4)        NOT NULL,
    cpf_masked            char(11)       NOT NULL,
    transaction_ts        datetimeoffset NOT NULL,
    amount_brl            decimal(18,2)  NOT NULL,
    movement_code         char(1)        NOT NULL,
    authorization_code    char(6)        NOT NULL,
    nsu                   char(12)       NOT NULL,
    terminal_id           char(16)       NOT NULL,
    -- leftover from the 2024 chargeback report. proc does not write this.
    chargeback_flag       char(1)        NULL,
    CONSTRAINT pk_stg_card PRIMARY KEY (batch_id, source_record_number)
)
GO

-- reporting.card_settlement_reconciliation
-- source_count, staged_count, applied_count
-- source_net_amount, staged_net_amount, applied_net_amount
-- count_delta, amount_delta, reject_count, status
GO


---

## Source: `spec/type-01-card-settlement/inbound/usp_apply_card_settlement_20260512.sql`

-- usp_apply_card_settlement  -- dumped 2026-05-12
-- Rafael: "this is the one from before we had refunds on the same file"
CREATE PROCEDURE legacy.apply_card_settlement_batch @batch_id char(16)
AS
BEGIN
    -- copies staging rows where amount_brl > 0 only
    INSERT INTO legacy.card_settlement
    SELECT * FROM staging.card_settlement
    WHERE batch_id = @batch_id
      AND amount_brl > 0
END
GO
-- NOTE: negative-overpunch / refunds were not in this revision


---

## Source: `spec/type-01-card-settlement/inbound/usp_apply_card_settlement_20260701.sql`

-- usp_apply_card_settlement  -- dumped 2026-07-01
-- Rafael: "use this one. May dump still has the May script, ignore it."
CREATE PROCEDURE legacy.apply_card_settlement_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.card_settlement
    SELECT s.*
    FROM staging.card_settlement s
    WHERE s.batch_id = @batch_id
      AND NOT EXISTS (
          SELECT 1 FROM legacy.card_settlement l
          WHERE l.batch_id = s.batch_id
            AND l.source_record_number = s.source_record_number
      )
END
GO
-- refunds (R, negative overpunch) are first-class
-- chargeback_flag is not populated
