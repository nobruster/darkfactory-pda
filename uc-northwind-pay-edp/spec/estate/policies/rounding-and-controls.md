# Rounding and controls

Ops note. Not a substitute for each type’s layout.

- Money is exact decimal. Two fractional digits unless a layout says
  otherwise.
- **Do not** use binary float. **Do not** use a language default
  rounding unless the type says so.
- Type 05 is percentage fees. The fee schedule (in that pack) is
  `HALF_UP` at the cent. Ops mail that says “normal rounding” is
  **not** a contract.
- Source-owned trailers and manifests are declarations. Independently
  recompute. A one-cent miss is quarantine.
- Tolerances are zero.

If two documents disagree, write down which one you believed. Do not
average them.
