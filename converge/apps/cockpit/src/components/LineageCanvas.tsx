import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  Background,
  BackgroundVariant,
  ControlButton,
  Controls,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
  type Edge,
  type FitViewOptions,
} from "@xyflow/react";
import {
  Crosshair,
  SquaresFour,
  Target,
} from "@phosphor-icons/react";
import type {
  EntityRef,
  PassState,
  WorkspaceSnapshot,
} from "../types";
import {
  CinematicEdge,
  type CinematicFlowEdge,
  type EdgeTone,
} from "./CinematicEdge";
import { PassNode, type PassFlowNode } from "./PassNode";
import { MobilePassList } from "./MobilePassList";

interface LineageCanvasProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

const nodeTypes = { pass: PassNode };
const edgeTypes = { cinematic: CinematicEdge };

const FIT_OPTIONS: FitViewOptions = {
  padding: 0.15,
  minZoom: 0.38,
  maxZoom: 1.03,
  duration: 420,
};

function arrangedPosition(order: number) {
  if (order <= 4) return { x: order * 264, y: 70 };
  if (order === 5) return { x: 1056, y: 358 };
  if (order === 6) return { x: 792, y: 516 };
  if (order === 7) return { x: 528, y: 358 };
  return { x: 264, y: 516 };
}

function issueCount(snapshot: WorkspaceSnapshot, passId: string) {
  return snapshot.issues.filter(
    (issue) => issue.entity?.kind === "pass" && issue.entity.id === passId,
  ).length;
}

function buildNodes(
  snapshot: WorkspaceSnapshot,
  selected: EntityRef | null,
): PassFlowNode[] {
  return snapshot.method.passes.map((pass) => {
    const lower = pass.order >= 5;
    const isSelected = selected?.kind === "pass" && selected.id === pass.id;
    return {
      id: pass.id,
      type: "pass",
      position: arrangedPosition(pass.order),
      sourcePosition:
        pass.order === 4 ? Position.Bottom : lower ? Position.Left : Position.Right,
      targetPosition:
        pass.order === 5 ? Position.Top : lower ? Position.Right : Position.Left,
      data: {
        pass,
        isSelected,
        issueCount: issueCount(snapshot, pass.id),
      },
      draggable: true,
      selectable: true,
      focusable: true,
      ariaRole: "button",
      domAttributes: {
        "aria-pressed": isSelected,
        "aria-current": pass.status === "active" ? "step" : undefined,
      },
      zIndex: isSelected ? 5 : 1,
      ariaLabel: `${pass.label}, ${pass.status}. Select to inspect or drag to reposition.`,
    };
  });
}

function edgeTone(pass: PassState | undefined, optional: boolean): EdgeTone {
  if (optional) return "optional";
  if (pass?.status === "complete") return "complete";
  if (pass?.status === "active") return "active";
  if (pass?.status === "blocked") return "blocked";
  return "waiting";
}

function Flow({
  snapshot,
  selected,
  onSelect,
}: LineageCanvasProps) {
  const didFit = useRef(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<PassFlowNode>(
    buildNodes(snapshot, selected),
  );
  const { fitView, getNode, getZoom, setCenter } =
    useReactFlow<PassFlowNode, CinematicFlowEdge>();

  useEffect(() => {
    setNodes((current) => {
      const positions = new Map(
        current.map((node) => [node.id, node.position] as const),
      );
      return buildNodes(snapshot, selected).map((node) => ({
        ...node,
        position: positions.get(node.id) ?? node.position,
      }));
    });
  }, [selected, setNodes, snapshot]);

  const edges = useMemo<CinematicFlowEdge[]>(
    () =>
      snapshot.method.edges.map((edge) => {
        const source = snapshot.method.passes.find(
          (pass) => pass.id === edge.source,
        );
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: "cinematic",
          data: {
            tone: edgeTone(source, edge.kind === "optional"),
            label:
              edge.kind === "bypass"
                ? "direct"
                : edge.kind === "optional"
                  ? "optional"
                  : undefined,
          },
          selectable: false,
          focusable: false,
        } as Edge as CinematicFlowEdge;
      }),
    [snapshot.method.edges, snapshot.method.passes],
  );

  const arrangeNodes = useCallback(() => {
    setNodes((current) =>
      current.map((node) => ({
        ...node,
        position: arrangedPosition(node.data.pass.order),
      })),
    );
    window.requestAnimationFrame(() => void fitView(FIT_OPTIONS));
  }, [fitView, setNodes]);

  const centerSelected = useCallback(() => {
    if (selected?.kind !== "pass") return;
    const node = getNode(selected.id);
    if (!node) return;
    const width = node.measured?.width ?? 224;
    const height = node.measured?.height ?? 136;
    void setCenter(
      node.position.x + width / 2,
      node.position.y + height / 2,
      {
        zoom: getZoom(),
        duration: 320,
      },
    );
  }, [getNode, getZoom, selected, setCenter]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onNodeClick={(_, node) => onSelect({ kind: "pass", id: node.id })}
      onSelectionChange={({ nodes: selectedNodes }) => {
        if (selectedNodes.length === 1) {
          onSelect({ kind: "pass", id: selectedNodes[0].id });
        }
      }}
      onInit={(instance) => {
        if (!didFit.current) {
          void instance.fitView(FIT_OPTIONS);
          didFit.current = true;
        }
      }}
      minZoom={0.28}
      maxZoom={1.65}
      nodesConnectable={false}
      panOnScroll
      panOnDrag
      zoomOnScroll
      zoomOnPinch
      zoomOnDoubleClick={false}
      proOptions={{ hideAttribution: true }}
      colorMode="dark"
      aria-label="Converge method journey"
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={28}
        size={1}
        color="rgba(162, 177, 191, 0.13)"
      />
      <Controls
        className="lineage-controls"
        showInteractive={false}
        orientation="horizontal"
        fitViewOptions={FIT_OPTIONS}
        aria-label="Journey viewport controls"
      >
        <ControlButton
          onClick={arrangeNodes}
          aria-label="Arrange journey"
          title="Arrange journey"
        >
          <SquaresFour aria-hidden="true" />
        </ControlButton>
        <ControlButton
          onClick={centerSelected}
          disabled={selected?.kind !== "pass"}
          aria-label="Center selected pass"
          title="Center selected pass"
        >
          <Target aria-hidden="true" />
        </ControlButton>
      </Controls>
      <Panel position="top-left" className="canvas-context">
        <span>Journey</span>
        <strong>{snapshot.method.name}</strong>
      </Panel>
      <Panel position="bottom-right" className="canvas-instruction">
        <Crosshair size={15} aria-hidden="true" />
        Pan, zoom, drag
      </Panel>
    </ReactFlow>
  );
}

export function LineageCanvas(props: LineageCanvasProps) {
  return (
    <section className="lineage-surface" aria-label="Method journey">
      <div className="lineage-surface__desktop">
        <ReactFlowProvider>
          <Flow {...props} />
        </ReactFlowProvider>
      </div>
      <MobilePassList
        passes={props.snapshot.method.passes}
        selected={props.selected}
        onSelect={props.onSelect}
      />
    </section>
  );
}
