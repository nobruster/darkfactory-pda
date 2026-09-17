# Intake — the raw zone authority

One file, 238 lines, and it owns every transition a raw batch can make:

> *Claim, archive, or quarantine ready raw batches through SFTP.*

```text
raw/incoming/    ──claim──▶   raw/processing/
                                    │
                    ┌───────────────┴───────────────┐
                 archive                        quarantine
                    ▼                                ▼
             raw/archive/                    raw/quarantine/
```

Those are the only three moves, and this is the only module that makes them.

## Why claiming is a move, not a flag

A batch is claimed by **relocating it** from `incoming` to `processing`, via
`sftp_client.move_batch`, which refuses if the target already exists and then
issues a single `posix_rename`. There is no status column and no lock file. The
consequences are worth stating:

- Two workers cannot claim the same batch — the target-exists check refuses the
  second one, and the rename itself is atomic on the server.
- A crashed run leaves the batch visibly in `processing`, which is exactly what
  `worker.py` looks for on restart before considering anything in `incoming`.
- The filesystem is the state machine, so state cannot disagree with reality.

A batch is considered ready only when `source-manifest.json` is present, which
`publisher/` writes last. See
[`../publisher/README.md`](../publisher/README.md).

## Quarantine is isolation, not failure

A quarantined batch is moved aside with a bounded, privacy-safe reason —
`lifecycle.py` caps it at 2 KB and requires the reason code to match
`[A-Z][A-Z0-9_]{2,63}`, so a refusal can never become an exfiltration channel.

**Unrelated batches stay eligible.** One bad batch never stops the line; that
is the property the modern platform must reproduce, and it is checked by the
end-to-end suites.

## Least privilege

Intake authenticates as the **`processor`** SFTP role. It can take from
`incoming`, move to `processing` or `quarantine`, and write sanitized CSV to
`outgoing` — but it **cannot archive**. Declaring a batch complete is the
`operator` role's decision, and no single role can both process a batch and
declare it done.

See [`../../infra/README.md`](../../infra/README.md) for the full matrix.

## Verification

Every claim re-verifies the raw file's SHA-256 against its sidecar and the
manifest before the batch proceeds. Transport is never trusted, even between
two zones of the same server.

## What must not change

- **Claim-by-rename.** Replacing it with a status flag reintroduces the
  possibility of state disagreeing with the filesystem.
- **The archive exclusion.** `processor` archiving its own work collapses two
  roles into one.
- **The quarantine reason bounds.** They are a privacy control, not
  tidiness.
