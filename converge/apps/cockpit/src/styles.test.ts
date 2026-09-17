import { describe, expect, it } from "vitest";
import stylesheet from "./styles.css?raw";

function mediaBlock(query: string) {
  const start = stylesheet.indexOf(`@media (${query})`);
  if (start < 0) return "";
  const next = stylesheet.indexOf("@media", start + 1);
  return stylesheet.slice(start, next < 0 ? undefined : next);
}

describe("Cockpit accessibility preferences", () => {
  it("removes motion without hiding the semantic surface", () => {
    const reducedMotion = mediaBlock("prefers-reduced-motion: reduce");

    expect(reducedMotion).toBeTruthy();
    expect(reducedMotion).toContain("animation-duration: 0.001ms");
    expect(reducedMotion).toContain(".cinematic-edge__flow");
    expect(reducedMotion).toContain("display: none");
  });

  it("removes blur and restores opaque operational panels", () => {
    const reducedTransparency = mediaBlock(
      "prefers-reduced-transparency: reduce",
    );

    expect(reducedTransparency).toBeTruthy();
    expect(reducedTransparency).toContain("backdrop-filter: none");
    expect(reducedTransparency).toContain("background: var(--panel)");
  });
});
