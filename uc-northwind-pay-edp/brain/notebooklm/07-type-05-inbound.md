# Pack 07 — Type 05 inbound (merchant fees)

What we mailed for Type `05`. Semicolon CSV, decimal comma, HALF_UP. Ops mail that says “normal rounding” is not the contract. Day 4 lives here.
The raw samples and expected/ oracles are not in this pack.



---

## Source: `spec/type-05-merchant-fee-assessment/README.md`

# Merchant Fee Assessment — inbound pack

**Type `05` · `MER_FEESET05` · `.csv` · semicolon, decimal comma, `HALF_UP`**

Same shape as Types `01`–`04`. The old numbered `01-`…`07-` tree is
gone; this is the customer drop.

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · assessed `12.36` |
| `valid-boundary` | Boundary | accepted |
| `rounding-half-up` | Type edge | accepted · assessed `0.04` on `3.50` |
| `malformed` | Grammar | `INVALID_CSV_QUOTING` |
| `df-source-005` | Source lie | `SOURCE_CONTROL_ASSESSED_FEE_MISMATCH` · declared `0.99` · computed `1.00` |

**Small red pill.** Python default is `HALF_EVEN`. Ops mail says
“normal rounding.” This type is **`HALF_UP`**. `rounding-half-up`
(`0.04` on `3.50`) is the proof. Trust the schedule and `expected/`,
not the language default. That is a preview of Day 5: something you
already trusted can be wrong.

Estate: [`../estate/`](../estate/README.md).


---

## Source: `spec/type-05-merchant-fee-assessment/inbound/2026-07-08-normal-rounding.md`

# fee rounding

**From:** Marina Alves  
**Date:** 2026-07-08

Just use normal rounding on the fees. That is what finance says on
the call. I am not going to argue IEEE vs commercial with them.

The schedule PDF in this folder has a worked `3.50` example. If that
disagrees with “normal,” believe the schedule and tell me.


---

## Source: `spec/type-05-merchant-fee-assessment/inbound/merchant-fee-schedule.md`

# Merchant percentage fees — schedule

**Code:** `MER_FEESET05` · layout `001`  
**Filename:** `NW_MERCHANT_FEES_YYYYMMDD_B###############.csv`  
**Encoding:** UTF-8 NFC · **EOL:** LF · delimiter `;` · decimal comma  
**Dates:** `dd/MM/yyyy` · description always quoted

Fee = `gross × rate ÷ 100`, then round **once** to two decimals with
**HALF_UP** (0.005 → 0.01). Not banker’s rounding.

Source manifest carries row count, gross, **assessed** fee, calculated
fee. The lie file has a valid row whose assessed and calculated fee
are both `1.00`. Only the source declaration says assessed `0.99`.


---

## Source: `spec/type-05-merchant-fee-assessment/inbound/merchant-fee-table-definitions.txt`

-- staging.merchant_fee_assessment  dump 2026-06-22
CREATE TABLE staging.merchant_fee_assessment (
    batch_id             char(16)      NOT NULL,
    source_record_number int           NOT NULL,
    merchant_id          varchar(32)   NOT NULL,
    document_masked      varchar(20)   NOT NULL,
    gross_amount         decimal(18,2) NOT NULL,
    fee_rate             decimal(9,6)  NOT NULL,
    assessed_fee         decimal(18,2) NOT NULL,
    calculated_fee       decimal(18,2) NOT NULL,
    PRIMARY KEY (batch_id, source_record_number)
)
GO


---

## Source: `spec/type-05-merchant-fee-assessment/inbound/usp_apply_merchant_fee.sql`

-- legacy.apply_merchant_fee_batch  dump 2026-06-22
CREATE PROCEDURE legacy.apply_merchant_fee_batch @batch_id char(16)
AS
BEGIN
    INSERT INTO legacy.merchant_fee_assessment
    SELECT * FROM staging.merchant_fee_assessment
    WHERE batch_id = @batch_id
END
GO
