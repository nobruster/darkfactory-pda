import {
  CheckCircle,
  Circle,
  CircleNotch,
  GitBranch,
  Warning,
  XCircle,
} from "@phosphor-icons/react";
import type { PassStatus } from "../types";

interface StatusGlyphProps {
  status: PassStatus;
  size?: number;
}

export function StatusGlyph({ status, size = 18 }: StatusGlyphProps) {
  switch (status) {
    case "complete":
      return <CheckCircle size={size} weight="fill" aria-hidden="true" />;
    case "active":
      return (
        <CircleNotch
          className="status-glyph--spin"
          size={size}
          weight="bold"
          aria-hidden="true"
        />
      );
    case "blocked":
      return (
        <span className="status-glyph__blocked" aria-hidden="true">
          <XCircle size={size} weight="fill" />
          <Warning size={Math.max(9, size - 8)} weight="fill" />
        </span>
      );
    case "optional":
    case "skipped":
      return <GitBranch size={size} weight="bold" aria-hidden="true" />;
    default:
      return <Circle size={size} weight="regular" aria-hidden="true" />;
  }
}
