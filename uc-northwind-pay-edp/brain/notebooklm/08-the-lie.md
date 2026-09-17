# Pack 08 — The lie (the whole drop)

This pack is inbound, not the contract. Raw samples are **not** here — NotebookLM cannot read signed overpunch. The numbers below are what the drop already says in prose.

The same shape of lie exists on every live type. Type `01` is the steel thread on Day 1. Types `02`–`05` keep the same rule: keep their number, refuse the batch.

## What the source declares vs what the rows add to

| Type | Sample | Declares | Rows add to | Finding |
|---|---|---|---|---|
| `01` card | `df-source-001` | **173.44** | **173.45** | `SOURCE_CONTROL_TOTAL_MISMATCH` |
| `02` PIX | `df-source-002` | **173.44** | **173.45** | `SOURCE_CONTROL_NET_MISMATCH` |
| `03` slips | `df-source-003` | **198.49** | **198.50** | `SOURCE_CONTROL_NET_MISMATCH` |
| `04` TED | `df-source-004` | **999.99** | **1000.00** | `SOURCE_CONTROL_NET_MISMATCH` |
| `05` fees | `df-source-005` | **0.99** | **1.00** | assessed-fee lie |

Keep their number. Refuse the batch. Do not quietly write the computed total into the trailer.



---

## Source: `spec/estate/mail/2026-07-14-the-cent-that-will-not-die.md`

# Re: that trailer again

**From:** Marina Alves `<marina.alves@northwindpay.example>`  
**Date:** 2026-07-14 09:12 −03  
**To:** Helena Dias  
**Cc:** Rafael Costa

Helena —

I am not sending another “corrected” file.

Card settlement `B202607230000004` still declares **173.44**. Our
details add to **173.45**. Same shape on PIX, slips, TED, and the fee
file (that one lies about the assessed fee: **0.99** vs **1.00**).

If your new plant quietly writes 173.45 into the trailer we will
have nothing to show the source. Keep their number. Refuse the
batch. That is the whole point.

Marina
