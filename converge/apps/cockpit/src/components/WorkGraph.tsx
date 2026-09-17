import { useEffect, useMemo, useRef } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { CheckCircle, LockKey, RocketLaunch } from "@phosphor-icons/react";
import type { EntityRef, WorkTask } from "../types";

export interface WorkPresentation {
  engine: string;
  topology: string;
  depth: number;
}

type WorkFlowNode = Node<
  {
    task: WorkTask;
    selected: boolean;
    frontier: boolean;
    presentation: WorkPresentation;
  },
  "work"
>;

interface WorkGraphProps {
  tasks: WorkTask[];
  frontierIds: string[];
  presentation: Record<string, WorkPresentation>;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function WorkNode({ data }: NodeProps<WorkFlowNode>) {
  const { task, selected, frontier, presentation } = data;
  return (
    <div
      className={`work-node work-node--${task.status} ${
        selected ? "work-node--selected" : ""
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="work-node__handle"
        isConnectable={false}
      />
      <div className="work-node__meta">
        <span>{String(task.priority ?? "No priority")}</span>
        <span>{String(task.effort ?? "No effort")}</span>
      </div>
      <strong>{task.title}</strong>
      <div className="work-node__attributes">
        <span>{presentation.topology}</span>
        <span>engine: {presentation.engine}</span>
        <span>agent: {task.agent ?? "unassigned"}</span>
      </div>
      <div className="work-node__state">
        {task.status === "done" ? (
          <CheckCircle weight="fill" aria-hidden="true" />
        ) : frontier ? (
          <RocketLaunch weight="fill" aria-hidden="true" />
        ) : (
          <LockKey weight="fill" aria-hidden="true" />
        )}
        {frontier ? "frontier" : task.status.replaceAll("_", " ")}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="work-node__handle"
        isConnectable={false}
      />
    </div>
  );
}

const nodeTypes = { work: WorkNode };

function depthFor(
  task: WorkTask,
  byId: ReadonlyMap<string, WorkTask>,
  visiting = new Set<string>(),
): number {
  if (task.dependsOn.length === 0 || visiting.has(task.id)) return 0;
  const nextVisiting = new Set(visiting);
  nextVisiting.add(task.id);
  return (
    1 +
    Math.max(
      0,
      ...task.dependsOn.map((id) => {
        const dependency = byId.get(id);
        return dependency ? depthFor(dependency, byId, nextVisiting) : 0;
      }),
    )
  );
}

function buildNodes(
  tasks: WorkTask[],
  frontier: ReadonlySet<string>,
  selected: EntityRef | null,
  presentation: Record<string, WorkPresentation>,
): WorkFlowNode[] {
  const byId = new Map(tasks.map((task) => [task.id, task] as const));
  const rowsByDepth = new Map<number, number>();
  return tasks.map((task) => {
    const depth = depthFor(task, byId);
    const row = rowsByDepth.get(depth) ?? 0;
    rowsByDepth.set(depth, row + 1);
    return {
      id: task.id,
      type: "work",
      position: { x: depth * 298 + 54, y: row * 186 + 66 },
      data: {
        task,
        frontier: frontier.has(task.id),
        selected: selected?.kind === "task" && selected.id === task.id,
        presentation: presentation[task.id] ?? {
          engine: "unassigned",
          topology: "not recorded",
          depth,
        },
      },
      draggable: true,
      focusable: true,
      ariaRole: "button",
      ariaLabel: `${task.id}, ${task.title}, ${task.status}`,
      zIndex: selected?.kind === "task" && selected.id === task.id ? 2 : 1,
    };
  });
}

function Graph(props: WorkGraphProps) {
  const didFit = useRef(false);
  const frontier = useMemo(
    () => new Set(props.frontierIds),
    [props.frontierIds],
  );
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkFlowNode>(
    buildNodes(props.tasks, frontier, props.selected, props.presentation),
  );

  useEffect(() => {
    setNodes((current) => {
      const positions = new Map(
        current.map((node) => [node.id, node.position] as const),
      );
      return buildNodes(props.tasks, frontier, props.selected, props.presentation).map((node) => ({
        ...node,
        position: positions.get(node.id) ?? node.position,
      }));
    });
  }, [frontier, props.presentation, props.selected, props.tasks, setNodes]);

  const edges = useMemo<Edge[]>(
    () =>
      props.tasks.flatMap((task) =>
        task.dependsOn.map((dependency) => ({
          id: `${dependency}-${task.id}`,
          source: dependency,
          target: task.id,
          type: "smoothstep",
          animated: frontier.has(task.id),
          className: frontier.has(task.id)
            ? "work-edge work-edge--frontier"
            : "work-edge",
          selectable: false,
          focusable: false,
        })),
      ),
    [frontier, props.tasks],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onNodeClick={(_, node) =>
        props.onSelect({ kind: "task", id: node.id })
      }
      onInit={(instance) => {
        if (!didFit.current) {
          void instance.fitView({
            padding: 0.18,
            minZoom: 0.45,
            maxZoom: 1,
            duration: 360,
          });
          didFit.current = true;
        }
      }}
      nodesConnectable={false}
      minZoom={0.35}
      maxZoom={1.5}
      panOnScroll
      fitView
      proOptions={{ hideAttribution: true }}
      colorMode="dark"
      aria-label="Work dependency graph"
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={28}
        size={1}
        color="rgba(162, 177, 191, 0.11)"
      />
      <Controls
        className="lineage-controls"
        showInteractive={false}
        orientation="horizontal"
        aria-label="Work graph viewport controls"
      />
    </ReactFlow>
  );
}

export function WorkGraph(props: WorkGraphProps) {
  return (
    <div className="work-graph">
      <ReactFlowProvider>
        <Graph {...props} />
      </ReactFlowProvider>
    </div>
  );
}
