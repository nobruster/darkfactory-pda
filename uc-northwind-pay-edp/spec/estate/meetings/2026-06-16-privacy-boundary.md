# Privacy boundary

**Date:** 2026-06-16  
**Type:** Decision Meeting  
**Confidence:** 0.93

## Attendees

Priya Shah · Rafael Costa · Helena Dias

## Executive Summary

Restricted values die at Java on the live line and must die at the
modern parser before any Parquet or Gold. Tokens are HMAC, fail-closed.
Clear PAN, CPF, CNPJ, and account numbers are prohibited in CSV, logs,
evidence, and the warehouse.

## Key Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Whole-output scan before publish | Approved |
| D2 | Type 01 PAN = token + last4; CPF = seven stars + last4 | Approved |
| D3 | Types 02–04 tokenize documents / accounts; Type 05 masks CNPJ | Approved |
| D4 | A privacy miss stalls the type. No waiver. | Approved |

## Implicit Signals

Priya will fail a demo that prints a “harmless” CPF in an exception.
Rafael asked whether the new plant can “just call our tokenizer.”
Denied — independence.
