import type {
  DecompositionLeg,
  Swimlane,
} from "../types";

export interface DecompositionLayout {
  laneFrames: Array<{
    lane: Swimlane;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
  legPositions: Map<string, { x: number; y: number }>;
}

const LANE_GAP = 34;
const LANE_HEADER_WIDTH = 300;
const LEG_WIDTH = 276;
const LEG_GAP_X = 42;
const LEG_GAP_Y = 18;
const LEG_HEIGHT = 138;
const LANE_PADDING = 20;

function dependencyDepth(
  leg: DecompositionLeg,
  byId: ReadonlyMap<string, DecompositionLeg>,
  memo: Map<string, number>,
  laneLegIds: ReadonlySet<string>,
  visiting = new Set<string>(),
): number {
  const cached = memo.get(leg.id);
  if (cached !== undefined) return cached;
  const localDependencies = leg.dependsOn.filter((id) => laneLegIds.has(id));
  if (visiting.has(leg.id) || localDependencies.length === 0) {
    memo.set(leg.id, 0);
    return 0;
  }

  const nextVisiting = new Set(visiting);
  nextVisiting.add(leg.id);
  const depth =
    1 +
    Math.max(
      0,
      ...localDependencies.map((dependencyId) => {
        const dependency = byId.get(dependencyId);
        return dependency
          ? dependencyDepth(dependency, byId, memo, laneLegIds, nextVisiting)
          : 0;
      }),
    );
  memo.set(leg.id, depth);
  return depth;
}

export function buildDecompositionLayout(
  lanes: readonly Swimlane[],
  legs: readonly DecompositionLeg[],
): DecompositionLayout {
  const byId = new Map(legs.map((leg) => [leg.id, leg] as const));
  const depthMemo = new Map<string, number>();
  const legPositions = new Map<string, { x: number; y: number }>();
  const laneFrames: DecompositionLayout["laneFrames"] = [];
  let laneY = 24;

  for (const lane of lanes) {
    const laneLegs = lane.legIds
      .map((id) => byId.get(id))
      .filter((leg): leg is DecompositionLeg => Boolean(leg))
      .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
    const rowsAtDepth = new Map<number, number>();
    const laneLegIds = new Set(laneLegs.map((leg) => leg.id));
    let maxDepth = 0;
    let maxRows = 1;

    for (const leg of laneLegs) {
      const depth = dependencyDepth(leg, byId, depthMemo, laneLegIds);
      const row = rowsAtDepth.get(depth) ?? 0;
      rowsAtDepth.set(depth, row + 1);
      maxDepth = Math.max(maxDepth, depth);
      maxRows = Math.max(maxRows, row + 1);
      legPositions.set(leg.id, {
        x: LANE_HEADER_WIDTH + LANE_PADDING + depth * (LEG_WIDTH + LEG_GAP_X),
        y: LANE_PADDING + row * (LEG_HEIGHT + LEG_GAP_Y),
      });
    }

    const height = Math.max(
      196,
      LANE_PADDING * 2 + maxRows * LEG_HEIGHT + (maxRows - 1) * LEG_GAP_Y,
    );
    const width = Math.max(
      680,
      LANE_HEADER_WIDTH +
        LANE_PADDING * 2 +
        (maxDepth + 1) * LEG_WIDTH +
        maxDepth * LEG_GAP_X,
    );
    laneFrames.push({ lane, x: 24, y: laneY, width, height });
    laneY += height + LANE_GAP;
  }

  return { laneFrames, legPositions };
}
