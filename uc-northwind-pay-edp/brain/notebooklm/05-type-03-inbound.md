# Pack 05 — Type 03 inbound (payment slips)

What we mailed for Type `03`. 240-byte pairs, lots. Same shape of lie as Type 01.
The raw samples and expected/ oracles are not in this pack.



---

## Source: `spec/type-03-payment-slip-settlement/README.md`

# Payment Slip Settlement — inbound pack

**Type `03` · `PAYSLIPSET03` · `.rem` · 240-byte pairs, lots**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `198.50` |
| `valid-boundary` | Boundary | accepted |
| `multi-lot` | Type edge | accepted |
| `malformed` | Grammar | `SEGMENT_PAIR_MISMATCH` |
| `df-source-003` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `198.49` vs `198.50` |

Estate: [`../estate/`](../estate/README.md).


---

## Source: `spec/type-03-payment-slip-settlement/inbound/2026-07-03-240-usually.md`

# record length

**From:** Rafael Costa  
**Date:** 2026-07-03

The slip file is 240. Usually. I have seen a bank pad to 242 once in
2019. If a record is short, I would just right-pad spaces — that is
what the old operator cheat-sheet said.

(Layout in this folder says exactly 240 + CRLF and names a rejection
for length. I have not reconciled the cheat-sheet.)


---

## Source: `spec/type-03-payment-slip-settlement/inbound/payment-slip-layout.md`

# Payment slip remittance — CNAB-ish

**Code:** `PAYSLIPSET03` · layout `001`  
**Filename:** `NW_PAYMENT_SLIP_YYYYMMDD_B###############.rem`  
**Encoding:** US-ASCII · every physical record **exactly 240 bytes** + CRLF

Sequence: `H (L (A B)+ T)+ Z`

- `H` file header · `Z` file trailer  
- `L` lot header · `T` lot trailer  
- `A` financial segment + immediately following `B` beneficiary segment  
  = one logical settlement

Controls (independently recomputed): lot count, physical count, logical
count, face, discount, fee, **net** = face − discount + fee.

File trailer net must match the sum of logical nets. The lie file
matches at every lot and misses by one cent on the file trailer.


---

## Source: `spec/type-03-payment-slip-settlement/inbound/payment-slip-table-definitions.txt`

-- staging.payment_slip_settlement  dump 2026-06-20
CREATE TABLE staging.payment_slip_settlement (
    batch_id             char(16)      NOT NULL,
    source_record_number int           NOT NULL,
    lot_number           int           NOT NULL,
    payment_ref_token    varchar(40)   NOT NULL,
    beneficiary_token    varchar(40)   NOT NULL,
    account_token        varchar(40)   NOT NULL,
    document_masked      varchar(20)   NOT NULL,
    face_amount          decimal(18,2) NOT NULL,
    discount_amount      decimal(18,2) NOT NULL,
    fee_amount           decimal(18,2) NOT NULL,
    net_amount           decimal(18,2) NOT NULL,
    -- "we used to print lot remarks on a courier sheet"
    lot_remark           varchar(80)   NULL,
    PRIMARY KEY (batch_id, source_record_number)
)
GO


---

## Source: `spec/type-03-payment-slip-settlement/inbound/usp_apply_payment_slip.sql`

-- legacy.apply_payment_slip_batch  dump 2026-06-22
-- does not write lot_remark
CREATE PROCEDURE legacy.apply_payment_slip_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.payment_slip_settlement
    SELECT batch_id, source_record_number, lot_number,
           payment_ref_token, beneficiary_token, account_token,
           document_masked, face_amount, discount_amount, fee_amount, net_amount
    FROM staging.payment_slip_settlement
    WHERE batch_id = @batch_id
END
GO
