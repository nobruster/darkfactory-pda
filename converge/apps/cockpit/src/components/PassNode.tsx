import { FileText, ShieldWarning } from "@phosphor-icons/react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { motion, useReducedMotion } from "motion/react";
import type { PassState } from "../types";
import { StatusGlyph } from "./StatusGlyph";

export type PassFlowNode = Node<
  {
    pass: PassState;
    isSelected: boolean;
    issueCount: number;
  },
  "pass"
>;

export function PassNode({
  data,
  sourcePosition = Position.Right,
  targetPosition = Position.Left,
}: NodeProps<PassFlowNode>) {
  const reduceMotion = useReducedMotion();
  const { pass, isSelected, issueCount } = data;

  return (
    <motion.div
      layout={!reduceMotion}
      className={`pass-node pass-node--${pass.status} ${
        isSelected ? "pass-node--selected" : ""
      }`}
      transition={{ type: "spring", stiffness: 340, damping: 32, mass: 0.75 }}
    >
      <Handle
        type="target"
        position={targetPosition}
        className="pass-node__handle"
        isConnectable={false}
      />
      <div className="pass-node__header">
        <span className="pass-node__order">{pass.order}</span>
        <span className="pass-node__title">{pass.label}</span>
        <span className={`pass-node__status status-${pass.status}`}>
          <StatusGlyph status={pass.status} />
        </span>
      </div>

      <p className="pass-node__summary">{pass.summary}</p>

      <div className="pass-node__footer">
        <span>
          <FileText size={14} aria-hidden="true" />
          {pass.artifactIds.length}
        </span>
        {issueCount > 0 ? (
          <span className="pass-node__issues">
            <ShieldWarning size={14} aria-hidden="true" />
            {issueCount}
          </span>
        ) : (
          <span className="pass-node__token">
            {pass.gate.verdict ?? (pass.optional ? "OPTIONAL" : "WAITING")}
          </span>
        )}
      </div>

      {isSelected ? (
        <motion.div
          className="pass-node__expanded"
          initial={reduceMotion ? false : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18 }}
        >
          <span>Gate token</span>
          <strong>{pass.gate.token ?? "Not emitted"}</strong>
        </motion.div>
      ) : null}

      <Handle
        type="source"
        position={sourcePosition}
        className="pass-node__handle"
        isConnectable={false}
      />
    </motion.div>
  );
}
