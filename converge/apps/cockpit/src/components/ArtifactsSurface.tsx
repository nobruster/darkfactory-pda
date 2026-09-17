import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Broadcast,
  CheckCircle,
  FileCode,
  FileText,
  FlowArrow,
  FolderOpen,
  GitBranch,
  LockKey,
  Pulse,
  ShieldCheck,
  Stack,
  WarningCircle,
} from "@phosphor-icons/react";
import type {
  ArtifactRef,
  EntityRef,
  PassState,
  WorkspaceSnapshot,
} from "../types";
import { StatusGlyph } from "./StatusGlyph";

interface ArtifactsSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
  onOpenArtifact: (artifact: ArtifactRef) => void;
}

function displayKind(kind: string) {
  return kind.replaceAll("_", " ");
}

function artifactIcon(kind: string) {
  if (["brief", "spec", "decision", "plan", "task"].includes(kind)) {
    return FileText;
  }
  if (["receipt", "contract", "policy"].includes(kind)) return ShieldCheck;
  return FileCode;
}

function artifactsForPass(snapshot: WorkspaceSnapshot, pass: PassState) {
  const ids = new Set(pass.artifactIds);
  for (const artifact of snapshot.artifacts) {
    if (artifact.entity?.kind === "pass" && artifact.entity.id === pass.id) {
      ids.add(artifact.id);
    }
  }
  return [...ids]
    .map((id) => snapshot.artifacts.find((artifact) => artifact.id === id))
    .filter((artifact): artifact is ArtifactRef => Boolean(artifact));
}

function relatedPasses(snapshot: WorkspaceSnapshot, passId: string) {
  const incoming = snapshot.method.edges
    .filter((edge) => edge.target === passId)
    .map((edge) => ({
      edge,
      pass: snapshot.method.passes.find((pass) => pass.id === edge.source),
    }))
    .filter((item): item is { edge: typeof item.edge; pass: PassState } => Boolean(item.pass));
  const outgoing = snapshot.method.edges
    .filter((edge) => edge.source === passId)
    .map((edge) => ({
      edge,
      pass: snapshot.method.passes.find((pass) => pass.id === edge.target),
    }))
    .filter((item): item is { edge: typeof item.edge; pass: PassState } => Boolean(item.pass));
  return { incoming, outgoing };
}

export function ArtifactsSurface({
  snapshot,
  selected,
  onSelect,
  onOpenArtifact,
}: ArtifactsSurfaceProps) {
  const firstPassId =
    snapshot.method.passes.find((pass) => pass.artifactIds.length > 0)?.id ??
    snapshot.method.passes[0]?.id ??
    "";
  const [passId, setPassId] = useState(
    selected?.kind === "pass" ? selected.id : firstPassId,
  );

  useEffect(() => {
    if (
      selected?.kind === "pass" &&
      snapshot.method.passes.some((pass) => pass.id === selected.id)
    ) {
      setPassId(selected.id);
    }
  }, [selected, snapshot.method.passes]);

  useEffect(() => {
    if (!snapshot.method.passes.some((pass) => pass.id === passId)) {
      setPassId(firstPassId);
    }
  }, [firstPassId, passId, snapshot.method.passes]);

  const pass =
    snapshot.method.passes.find((candidate) => candidate.id === passId) ??
    snapshot.method.passes[0];
  const artifacts = useMemo(
    () => (pass ? artifactsForPass(snapshot, pass) : []),
    [pass, snapshot],
  );
  const groups = useMemo(() => {
    const byKind = new Map<string, ArtifactRef[]>();
    for (const artifact of artifacts) {
      const current = byKind.get(artifact.kind) ?? [];
      current.push(artifact);
      byKind.set(artifact.kind, current);
    }
    return [...byKind.entries()].sort(([left], [right]) => left.localeCompare(right));
  }, [artifacts]);

  if (!pass) {
    return (
      <section className="surface surface--artifacts">
        <div className="surface-state">
          <LockKey size={28} weight="fill" aria-hidden="true" />
          <strong>No method passes observed</strong>
          <p>The snapshot cannot build a pass-to-artifact trace.</p>
        </div>
      </section>
    );
  }

  const relationships = relatedPasses(snapshot, pass.id);
  const signals = snapshot.signals.filter(
    (signal) => signal.entity?.kind === "pass" && signal.entity.id === pass.id,
  );
  const issues = snapshot.issues.filter(
    (issue) => issue.entity?.kind === "pass" && issue.entity.id === pass.id,
  );

  function selectPass(next: PassState) {
    setPassId(next.id);
    onSelect({ kind: "pass", id: next.id });
  }

  function openArtifact(artifact: ArtifactRef) {
    onSelect({ kind: "artifact", id: artifact.id });
    onOpenArtifact(artifact);
  }

  return (
    <section className="surface surface--artifacts" aria-labelledby="artifacts-title">
      <header className="surface-header artifacts-header">
        <div>
          <span>Pass evidence and relationships</span>
          <h1 id="artifacts-title">Artifacts</h1>
        </div>
        <div className="artifacts-header__summary">
          <Stack weight="fill" aria-hidden="true" />
          <span><strong>{snapshot.artifacts.length}</strong> observed records</span>
        </div>
      </header>

      <div className="artifact-pass-strip" role="tablist" aria-label="Choose a Converge pass">
        {snapshot.method.passes.map((candidate) => {
          const active = candidate.id === pass.id;
          return (
            <button
              type="button"
              role="tab"
              key={candidate.id}
              className={`artifact-pass-tab artifact-pass-tab--${candidate.status} ${active ? "is-active" : ""}`}
              onClick={() => selectPass(candidate)}
              aria-selected={active}
            >
              <span className="artifact-pass-tab__order">{candidate.order}</span>
              <span>
                <strong>{candidate.label}</strong>
                <small>{candidate.artifactIds.length} outputs</small>
              </span>
              <StatusGlyph status={candidate.status} />
            </button>
          );
        })}
      </div>

      <div className="artifact-explorer">
        <aside className="artifact-pass-record" aria-label={`${pass.label} pass record`}>
          <header>
            <span className={`artifact-pass-record__glyph status-${pass.status}`}>
              <StatusGlyph status={pass.status} />
            </span>
            <span>
              <small>Pass {pass.order}</small>
              <h2>{pass.label}</h2>
            </span>
          </header>
          <p>{pass.summary}</p>
          <dl>
            <div><dt>Status</dt><dd>{pass.status}</dd></div>
            <div><dt>Gate</dt><dd>{pass.gate.verdict ?? "Not emitted"}</dd></div>
            <div><dt>Command</dt><dd><code>{pass.gate.command ?? "Not recorded"}</code></dd></div>
            <div><dt>Token</dt><dd><code>{pass.gate.token ?? "Not emitted"}</code></dd></div>
          </dl>
          <section className="artifact-pass-record__boundary">
            <ShieldCheck weight="fill" aria-hidden="true" />
            <p>
              Cockpit shows produced files and bounded signals. Raw command-call traces are not exposed by this snapshot, so none are inferred.
            </p>
          </section>
        </aside>

        <section className="artifact-trace" aria-labelledby="artifact-trace-title">
          <header>
            <div>
              <span>Observed lineage</span>
              <h2 id="artifact-trace-title">What {pass.label} produced</h2>
            </div>
            <span className="artifact-trace__count">{artifacts.length} artifacts</span>
          </header>

          <div className="artifact-lineage" role="group" aria-label={`${pass.label} artifact relationship graph`}>
            <div className="artifact-lineage__source">
              <span className="artifact-node artifact-node--project">
                <GitBranch aria-hidden="true" />
                <span><small>Project</small><strong>{snapshot.project.name}</strong></span>
              </span>
              {relationships.incoming.map(({ edge, pass: incoming }) => (
                <button type="button" key={edge.id} className="artifact-node artifact-node--related" onClick={() => selectPass(incoming)}>
                  <FlowArrow aria-hidden="true" />
                  <span><small>{edge.kind} input</small><strong>{incoming.label}</strong></span>
                </button>
              ))}
            </div>

            <ArrowRight className="artifact-lineage__arrow" aria-hidden="true" />

            <button type="button" className={`artifact-node artifact-node--pass artifact-node--${pass.status}`} onClick={() => onSelect({ kind: "pass", id: pass.id })}>
              <span className="artifact-node__pass-order">{pass.order}</span>
              <span><small>Converge pass</small><strong>{pass.label}</strong><em>{pass.status}</em></span>
            </button>

            <ArrowRight className="artifact-lineage__arrow" aria-hidden="true" />

            <div className="artifact-lineage__outputs">
              {groups.length > 0 ? groups.map(([kind, items]) => (
                <section key={kind} className="artifact-output-group" aria-labelledby={`artifact-kind-${kind}`}>
                  <header>
                    <span id={`artifact-kind-${kind}`}>{displayKind(kind)}</span>
                    <strong>{items.length}</strong>
                  </header>
                  <div>
                    {items.map((artifact) => {
                      const Icon = artifactIcon(artifact.kind);
                      return (
                        <button
                          type="button"
                          key={artifact.id}
                          className={`artifact-output ${selected?.kind === "artifact" && selected.id === artifact.id ? "is-selected" : ""}`}
                          onClick={() => openArtifact(artifact)}
                          aria-label={`Open ${artifact.label}, ${artifact.path}`}
                        >
                          <Icon aria-hidden="true" />
                          <span>
                            <strong>{artifact.label}</strong>
                            <code>{artifact.path}</code>
                          </span>
                          <FolderOpen aria-hidden="true" />
                        </button>
                      );
                    })}
                  </div>
                </section>
              )) : (
                <div className="artifact-trace__empty">
                  <FileCode aria-hidden="true" />
                  <span><strong>No produced artifact recorded</strong><small>This pass remains part of the method graph.</small></span>
                </div>
              )}
            </div>
          </div>
        </section>

        <aside className="artifact-observations" aria-label="Pass observations">
          <section>
            <header><Pulse aria-hidden="true" /><h2>Observed events</h2><span>{signals.length}</span></header>
            {signals.length > 0 ? signals.map((signal) => (
              <button type="button" key={signal.id} onClick={() => onSelect({ kind: "signal", id: signal.id })}>
                <Broadcast weight="fill" aria-hidden="true" />
                <span><strong>{signal.summary}</strong><small>{signal.severity}</small></span>
              </button>
            )) : <p>No pass signal was recorded.</p>}
          </section>
          {issues.length > 0 ? (
            <section>
              <header><WarningCircle weight="fill" aria-hidden="true" /><h2>Attention</h2><span>{issues.length}</span></header>
              {issues.map((issue) => (
                <button type="button" key={issue.id} onClick={() => onSelect({ kind: "issue", id: issue.id })}>
                  <WarningCircle weight="fill" aria-hidden="true" />
                  <span><strong>{issue.message}</strong><small>{issue.severity}</small></span>
                </button>
              ))}
            </section>
          ) : null}
          <section>
            <header><FlowArrow aria-hidden="true" /><h2>Method relationship</h2><span>{relationships.outgoing.length}</span></header>
            {relationships.outgoing.length > 0 ? relationships.outgoing.map(({ edge, pass: outgoing }) => (
              <button type="button" key={edge.id} onClick={() => selectPass(outgoing)}>
                {outgoing.status === "complete" ? <CheckCircle weight="fill" aria-hidden="true" /> : <FlowArrow aria-hidden="true" />}
                <span><strong>{outgoing.label}</strong><small>{edge.kind} next pass</small></span>
              </button>
            )) : <p>No downstream method edge is recorded.</p>}
          </section>
        </aside>
      </div>
    </section>
  );
}
