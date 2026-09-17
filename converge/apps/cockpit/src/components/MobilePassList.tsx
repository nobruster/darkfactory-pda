import { CaretRight } from "@phosphor-icons/react";
import type { EntityRef, PassState } from "../types";
import { StatusGlyph } from "./StatusGlyph";

interface MobilePassListProps {
  passes: PassState[];
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

export function MobilePassList({
  passes,
  selected,
  onSelect,
}: MobilePassListProps) {
  return (
    <ol className="mobile-pass-list" aria-label="Converge passes">
      {passes.map((pass) => {
        const isSelected = selected?.kind === "pass" && selected.id === pass.id;
        return (
          <li key={pass.id}>
            <button
              type="button"
              className={`mobile-pass ${isSelected ? "mobile-pass--selected" : ""}`}
              onClick={() => onSelect({ kind: "pass", id: pass.id })}
              aria-current={isSelected ? "step" : undefined}
            >
              <span className={`mobile-pass__glyph status-${pass.status}`}>
                <StatusGlyph status={pass.status} />
              </span>
              <span className="mobile-pass__order">{pass.order}</span>
              <span className="mobile-pass__copy">
                <strong>{pass.label}</strong>
                <span>{pass.gate.token ?? pass.summary}</span>
              </span>
              <CaretRight size={17} aria-hidden="true" />
            </button>
          </li>
        );
      })}
    </ol>
  );
}
