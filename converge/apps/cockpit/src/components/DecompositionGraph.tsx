import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  Background,
  BackgroundVariant,
  ControlButton,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useNodesInitialized,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import {
  CheckCircle,
  Circle,
  SquaresFour,
  Target,
} from "@phosphor-icons/react";
import { useReducedMotion } from "motion/react";
import type {
  DecompositionLeg,
  EntityRef,
  Swimlane,
  WorkspaceSnapshot,
} from "../types";
import { buildDecompositionLayout } from "../lib/decomposition-layout";

function readable(value: string) {
  return value.replaceAll("—", "-").replaceAll("–", "-").replaceAll(" · ", " / ");
}

function laneName(value: string) {
  return readable(value.replace(/^Swimlane\s*[·:]\s*/i, ""));
}

type LaneFlowNode = Node<
  {
    lane: Swimlane;
    selected: boolean;
    width: number;
    height: number;
    onSelect: (selection: EntityRef) => void;
  },
  "lane"
>;

type LegFlowNode = Node<
  {
    leg: DecompositionLeg;
    selected: boolean;
    onSelect: (selection: EntityRef) => void;
  },
  "leg"
>;

type DecompositionNode = LaneFlowNode | LegFlowNode;

interface DecompositionGraphProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function LaneNode({ data }: NodeProps<LaneFlowNode>) {
  const { lane, selected, width, height, onSelect } = data;
  return (
    <button
      type="button"
      className={`decomposition-lane-node ${
        selected ? "decomposition-lane-node--selected" : ""
      }`}
      style={{ width, height }}
      aria-label={`${lane.label}, ${lane.risk} risk, ${lane.legIds.length} legs`}
      aria-pressed={selected}
      onClick={() => onSelect({ kind: "swimlane", id: lane.id })}
    >
      <div className="decomposition-lane-node__identity">
        <span>Swimlane</span>
        <strong>{laneName(lane.label)}</strong>
        <small>{lane.thread ? "Steel thread" : `${lane.legIds.length} delivery legs`}</small>
      </div>
      <div className="decomposition-lane-node__meta">
        <span className={`risk-chip risk-chip--${lane.risk}`}>
          {lane.risk} risk
        </span>
        <span>{lane.owner}</span>
      </div>
      <div className="decomposition-seam">
        <span>Why this seam</span>
        <p>{readable(lane.seam.rationale ?? lane.purpose ?? "No rationale recorded.")}</p>
      </div>
      <div className="decomposition-contract">
        <span>
          <small>Consumes</small>
          {readable(lane.seam.inputContract ?? lane.seam.consumedInterface ?? "Not recorded")}
        </span>
        <span>
          <small>Produces</small>
          {readable(lane.seam.outputContract ?? "Not recorded")}
        </span>
      </div>
    </button>
  );
}

function statusIcon(status: DecompositionLeg["status"]) {
  if (status === "done" || status === "accepted") {
    return <CheckCircle weight="fill" aria-hidden="true" />;
  }
  return <Circle weight={status === "in_progress" ? "fill" : "regular"} aria-hidden="true" />;
}

function LegNode({ data }: NodeProps<LegFlowNode>) {
  const { leg, selected, onSelect } = data;
  return (
    <button
      type="button"
      className={`decomposition-leg-node decomposition-leg-node--${leg.status} ${
        selected ? "decomposition-leg-node--selected" : ""
      }`}
      aria-label={`${leg.title}, ${leg.status}, ${leg.dependsOn.length} dependencies`}
      aria-pressed={selected}
      onClick={() => onSelect({ kind: "leg", id: leg.id })}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="decomposition-leg-node__handle"
        isConnectable={false}
      />
      <div className="decomposition-leg-node__eyebrow">
        <span>Leg {String(leg.order).padStart(2, "0")}</span>
        <span>{leg.tech ?? "technology open"}</span>
      </div>
      <strong>{leg.title}</strong>
      <p>{readable(leg.responsibility ?? "Responsibility is not recorded.")}</p>
      <div className="decomposition-leg-node__status">
        {statusIcon(leg.status)}
        <span>{leg.status.replaceAll("_", " ")}</span>
        <small>{leg.dependsOn.length} dependencies</small>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="decomposition-leg-node__handle"
        isConnectable={false}
      />
    </button>
  );
}

const nodeTypes = {
  lane: LaneNode,
  leg: LegNode,
};

function buildNodes(
  snapshot: WorkspaceSnapshot,
  selected: EntityRef | null,
  onSelect: (selection: EntityRef) => void,
): DecompositionNode[] {
  const layout = buildDecompositionLayout(
    snapshot.decomposition.swimlanes,
    snapshot.decomposition.legs,
  );
  const laneNodes: LaneFlowNode[] = layout.laneFrames.map((frame) => ({
    id: frame.lane.id,
    type: "lane",
    position: { x: frame.x, y: frame.y },
    data: {
      lane: frame.lane,
      selected: selected?.kind === "swimlane" && selected.id === frame.lane.id,
      width: frame.width,
      height: frame.height,
      onSelect,
    },
    style: { width: frame.width, height: frame.height },
    draggable: false,
    selectable: true,
    focusable: false,
    zIndex: 0,
  }));
  const lanePositions = new Map(
    layout.laneFrames.map((frame) => [frame.lane.id, frame] as const),
  );
  const legNodes: LegFlowNode[] = snapshot.decomposition.legs.map((leg) => {
    const relative = layout.legPositions.get(leg.id) ?? { x: 400, y: 24 };
    const parent = lanePositions.get(leg.swimlaneId);
    return {
      id: leg.id,
      type: "leg",
      position: {
        x: (parent?.x ?? 24) + relative.x,
        y: (parent?.y ?? 24) + relative.y,
      },
      data: {
        leg,
        selected: selected?.kind === "leg" && selected.id === leg.id,
        onSelect,
      },
      draggable: false,
      selectable: true,
      focusable: false,
      zIndex: selected?.kind === "leg" && selected.id === leg.id ? 4 : 2,
    };
  });
  return [...laneNodes, ...legNodes];
}

function Graph(props: DecompositionGraphProps) {
  const reduceMotion = useReducedMotion();
  const didFit = useRef(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<DecompositionNode>(
    buildNodes(props.snapshot, props.selected, props.onSelect),
  );
  const nodesInitialized = useNodesInitialized();
  const { fitView, getNode, getZoom, setCenter } =
    useReactFlow<DecompositionNode, Edge>();

  useEffect(() => {
    setNodes(buildNodes(props.snapshot, props.selected, props.onSelect));
  }, [props.onSelect, props.selected, props.snapshot, setNodes]);

  useEffect(() => {
    if (!nodesInitialized || didFit.current) return;
    const timer = window.setTimeout(() => {
      void fitView({
        padding: 0.08,
        minZoom: 0.62,
        maxZoom: 1.12,
        duration: reduceMotion ? 0 : 420,
      });
      didFit.current = true;
    }, 100);
    return () => window.clearTimeout(timer);
  }, [fitView, nodesInitialized, reduceMotion]);

  const edges = useMemo<Edge[]>(
    () =>
      props.snapshot.decomposition.edges.map((edge) => {
        const selected =
          props.selected?.id === edge.source || props.selected?.id === edge.target;
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: "default",
          className: `decomposition-edge ${
            selected ? "decomposition-edge--selected" : ""
          }`,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: selected ? "#f3b64c" : "#697887",
          },
          selectable: false,
          focusable: false,
        };
      }),
    [props.selected, props.snapshot.decomposition.edges],
  );

  const arrange = useCallback(() => {
    setNodes(buildNodes(props.snapshot, props.selected, props.onSelect));
    window.requestAnimationFrame(() =>
      void fitView({
        padding: 0.08,
        minZoom: 0.62,
        maxZoom: 1.12,
        duration: reduceMotion ? 0 : 380,
      }),
    );
  }, [fitView, props.onSelect, props.selected, props.snapshot, reduceMotion, setNodes]);

  const centerSelected = useCallback(() => {
    if (!props.selected || !["swimlane", "leg"].includes(props.selected.kind)) return;
    const node = getNode(props.selected.id);
    if (!node) return;
    const width = node.measured?.width ?? (node.type === "lane" ? 420 : 320);
    const height = node.measured?.height ?? (node.type === "lane" ? 232 : 184);
    void setCenter(node.position.x + width / 2, node.position.y + height / 2, {
      zoom: getZoom(),
      duration: reduceMotion ? 0 : 320,
    });
  }, [getNode, getZoom, props.selected, reduceMotion, setCenter]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      nodesConnectable={false}
      minZoom={0.22}
      maxZoom={1.5}
      panOnScroll
      panOnDrag
      zoomOnDoubleClick={false}
      proOptions={{ hideAttribution: true }}
      colorMode="dark"
      aria-label="Swimlane decomposition graph"
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={32}
        size={1}
        color="rgba(162, 177, 191, 0.11)"
      />
      <Controls
        className="lineage-controls"
        showInteractive={false}
        orientation="horizontal"
        aria-label="Decomposition viewport controls"
      >
        <ControlButton onClick={arrange} aria-label="Arrange decomposition">
          <SquaresFour aria-hidden="true" />
        </ControlButton>
        <ControlButton
          onClick={centerSelected}
          disabled={!props.selected || !["swimlane", "leg"].includes(props.selected.kind)}
          aria-label="Center selected lane or leg"
        >
          <Target aria-hidden="true" />
        </ControlButton>
      </Controls>
    </ReactFlow>
  );
}

export function DecompositionGraph(props: DecompositionGraphProps) {
  return (
    <div className="decomposition-graph">
      <ReactFlowProvider>
        <Graph {...props} />
      </ReactFlowProvider>
    </div>
  );
}
