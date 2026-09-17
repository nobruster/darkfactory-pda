# Merchant chargeback adjustments — layout

**Code:** `MER_CHGBK06` · layout `001`  
**Filename:** `NW_MERCHANT_CHARGEBACK_YYYYMMDD_B###############.csv`  
**Encoding:** UTF-8 NFC · **EOL:** LF · delimiter `;` · decimal comma  
**Dates:** `dd/MM/yyyy` · description always quoted

Chargeback = `original × rate ÷ 100`, then round **once** to two
decimals with **HALF_UP** (0.005 → 0.01). Not banker’s rounding.

Header (exact):

```
chargeback_id;batch_id;merchant_id;merchant_tax_id;reason_code;description;original_amount_brl;rate_percent;chargeback_amount_brl;business_date
```

Source manifest carries row count, original amount, chargeback amount,
and independently calculated amount. Sanitized output is comma CSV with
period decimals, masked CNPJ, and `rounding_mode`.
