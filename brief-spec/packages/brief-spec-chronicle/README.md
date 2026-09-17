# Brief-Spec Chronicle

`brief-spec-chronicle` is the optional, explicitly activated project-history extension for
Brief-Spec. It records bounded material events, derives a rebuildable relation index, and renders
human review packs without storing raw prompts, transcripts, credentials, or tool output.

```bash
uv tool install --force --reinstall \
  --with ./packages/brief-spec-renderer-pdf \
  --with ./packages/brief-spec-renderer-audio \
  --with ./packages/brief-spec-chronicle \
  --with ./packages/brief-spec-renderer-video \
  --with-executables-from brief-spec-chronicle \
  .
brief-spec-chronicle init --project .
brief-spec-chronicle ingest event.json --project . --source brief-spec
brief-spec-chronicle snapshot --project . --output chronicle.json
brief-spec-chronicle export chronicle.json \
  --formats markdown,json,html,zip --output-dir output
brief-spec-chronicle verify output --level rendered --workspace . --offline
```

This is the source-candidate command from the repository root. Keep every desired optional package
in the same transaction because reinstalling a `uv` tool replaces its managed environment. A
published Chronicle installation will use the same shape with pinned distribution requirements.

Initialization writes only below `$BRIEF_SPEC_HOME/chronicles`. It does not modify the project.
The ledger records what Brief-Spec observed; it is not canonical project truth or an approval
engine.

Every export is staged and committed as one rollback-capable transaction. `manifest.json`
attests the rendered files; the external `chronicle-receipt.json` attests those files, the
manifest, and the ZIP without creating a self-referential hash. The canonical `chronicle.json`
anchor accompanies every selected presentation. Opaque evidence IDs produce an explicit
unresolved warning. `file:`, `commit:`, and public HTTP(S) locators can be resolved; `--offline`
leaves network locators unresolved without contacting them. Private and expired evidence remains
classified in the appendix and is never silently promoted to resolved proof.

`ingest` accepts the canonical `brief-spec-event/1.0` contract and bounded projections from
Brief-Spec delivery, Seamwise, Task-Spec, Converge, Exa, Tavily, Firecrawl, and RAFT sources. The
source adapters select fields rather than retaining provider payloads. A shared `correlation_id`
deduplicates the same material transition observed by multiple harnesses.

Archives are deterministic and non-destructive. Restore is explicit and can relocate a deleted
Chronicle registration without changing the archived event IDs:

```bash
brief-spec-chronicle archive --project . --output chronicle-archive.zip
brief-spec-chronicle restore chronicle-archive.zip --project /path/to/restored-project
```
