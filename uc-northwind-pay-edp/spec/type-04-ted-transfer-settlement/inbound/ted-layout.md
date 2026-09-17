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
