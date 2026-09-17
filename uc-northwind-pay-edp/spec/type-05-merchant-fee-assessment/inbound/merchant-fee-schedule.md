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
