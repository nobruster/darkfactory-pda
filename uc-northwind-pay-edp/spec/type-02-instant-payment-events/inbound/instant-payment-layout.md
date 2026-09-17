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
