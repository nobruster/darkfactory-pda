import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";

export type EdgeTone = "complete" | "active" | "waiting" | "optional" | "blocked";

export type CinematicFlowEdge = Edge<
  {
    tone: EdgeTone;
    label?: string;
  },
  "cinematic"
>;

export function CinematicEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<CinematicFlowEdge>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: data?.tone === "optional" ? 0.5 : 0.3,
  });
  const tone = data?.tone ?? "waiting";

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        className={`cinematic-edge cinematic-edge--${tone}`}
      />
      {tone === "complete" || tone === "active" ? (
        <path
          d={edgePath}
          className={`cinematic-edge__flow cinematic-edge__flow--${tone}`}
          aria-hidden="true"
        />
      ) : null}
      {data?.label ? (
        <EdgeLabelRenderer>
          <span
            className="cinematic-edge__label"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {data.label}
          </span>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}
