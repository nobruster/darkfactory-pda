# Cover — NorthWind Pay settlement modernization

**From:** Helena Dias, Partner Integration  
**To:** the modernization team  
**Date:** 2026-06-24  
**Request:** rebuild the five live settlement files beside the current Java
line. Do not replace Java. Do not “fix” source totals.

NorthWind Pay already runs five file types through SFTP → Java 21 →
sanitized CSV → PostgreSQL. We need a second, independent
implementation that reads **this drop**, not the Java, and still
reaches the same terminal outcomes.

## What we are sending

- This estate folder (how we work, what we decided, what we argue about)
- One inbound pack per live type: `01` card, `02` instant payment,
  `03` payment slip, `04` TED, `05` merchant fees
- Raw samples, what sanitized output must look like, and the refusals
- One source-owned lie per type. Keep the declaration. Compute the
  truth. Refuse the batch.

We are **not** sending a parser, a lakehouse model, or permission to
edit the live line.

## Done means

For every accepted sample: sanitized rows and reconciliation match the
oracle, privacy holds, tolerances are zero.  
For every refusal: stable code, no CSV, no business rows, peers
continue.  
For every source lie: classified as a source defect, never repaired.

Type `06` is out of scope for this drop. If a sixth file appears, it
will arrive as its own pack.
