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
