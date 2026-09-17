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
