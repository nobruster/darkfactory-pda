import { resolveEntity } from "../lib/entities";
import type { EntityKind, EntityRef, WorkspaceSnapshot } from "../types";

export interface AskContextCandidate {
  ref: EntityRef;
  key: string;
  eyebrow: string;
  title: string;
  /** Lower-cased haystack used for filtering. */
  search: string;
}

/**
 * Kinds the Ask server accepts as an explicitly selected entity, in the order a
 * reader thinks about a workspace: method first, then decomposition, delivery,
 * and finally evidence.
 */
const CONTEXT_KINDS: ReadonlyArray<EntityKind> = [
  "pass",
  "swimlane",
  "leg",
  "task",
  "run",
  "receipt",
  "artifact",
  "issue",
  "signal",
  "health",
];

function collectionFor(
  snapshot: WorkspaceSnapshot,
  kind: EntityKind,
): ReadonlyArray<{ id: string }> {
  if (kind === "pass") return snapshot.method?.passes ?? [];
  if (kind === "task") return snapshot.work?.tasks ?? [];
  if (kind === "run") return snapshot.execution?.runs ?? [];
  if (kind === "receipt") return snapshot.receipts?.items ?? [];
  if (kind === "health") return snapshot.health?.checks ?? [];
  if (kind === "signal") return snapshot.signals ?? [];
  if (kind === "issue") return snapshot.issues ?? [];
  if (kind === "artifact") return snapshot.artifacts ?? [];
  if (kind === "swimlane") return snapshot.decomposition?.swimlanes ?? [];
  if (kind === "leg") return snapshot.decomposition?.legs ?? [];
  return [];
}

/**
 * Every entity in the current snapshot that Ask can be pointed at.
 *
 * Ask previously had no way to choose context from inside the surface: the
 * control only appeared when something had already been selected on another
 * surface, so landing on Ask directly meant the option was invisible. This
 * enumerates the real candidates so context can be chosen in place.
 */
export function askContextCandidates(
  snapshot: WorkspaceSnapshot,
): AskContextCandidate[] {
  const candidates: AskContextCandidate[] = [];
  for (const kind of CONTEXT_KINDS) {
    for (const item of collectionFor(snapshot, kind)) {
      if (typeof item?.id !== "string" || item.id.length === 0) continue;
      const ref: EntityRef = { kind, id: item.id };
      const resolved = resolveEntity(snapshot, ref);
      if (!resolved) continue;
      candidates.push({
        ref,
        key: `${kind}:${item.id}`,
        eyebrow: resolved.eyebrow,
        title: resolved.title,
        search: `${kind} ${resolved.eyebrow} ${resolved.title} ${item.id}`.toLowerCase(),
      });
    }
  }
  return candidates;
}

export function filterContextCandidates(
  candidates: AskContextCandidate[],
  query: string,
  limit = 40,
) {
  const terms = query.trim().toLowerCase().split(/\s+/u).filter(Boolean);
  if (terms.length === 0) return candidates.slice(0, limit);
  return candidates
    .filter((candidate) => terms.every((term) => candidate.search.includes(term)))
    .slice(0, limit);
}
