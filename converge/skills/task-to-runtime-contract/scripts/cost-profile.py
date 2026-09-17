#!/usr/bin/env python3
"""Resolve what ONE attempt is allowed to cost, from the lane and the effort.

WHY THIS EXISTS

The loop had exactly one setting for every task in every situation: bare
`claude -p` with no model, no effort, and a flat 900-second cap. A four-file
mechanical build and a greenfield service therefore drew the same engine at the
same reasoning effort. Measured on the first real run: 66 turns, 6,873,938
cache-read tokens, $7.91, for a deliverable of four files.

`cvg lane` already classified work as FAST | NORMAL | FULL, but it was advisory
and routed only WHICH PASSES RUN. Nothing carried the verdict into what an
attempt may spend, so the dial existed and was not connected to anything.

THE SHAPE

    attempt_seconds = lane_base x effort_multiplier

Two axes, because they answer different questions. The LANE says how much rigor
this change deserves — a typo fix and a payment path are not owed the same
scrutiny. The EFFORT says how much room the work needs — an L leaf spans more
ground than an XS one at any rigor. Collapsing them into one number gets a
long-horizon task guillotined on the cheap lane, or a typo fix handed a
15-minute budget.

IT ROUTES, IT NEVER WAIVES

The same invariant `cvg lane` already carries. This resolver emits DEFAULTS. The
spec's own declared budgets still apply through the kernel's `tighter()`, so a
lane can never RAISE a ceiling the spec set — only lower it. And tier 2 is
recommended here, never enforced: FULL asks for it because high blast radius
earns an independent opinion, and the operator can still decline.

Usage:
  cost-profile.py --effort L [--lane NORMAL] [--model M] [--attempt-seconds N]
  cost-profile.py --effort M --yaml        # the block Bind writes into a profile

Emits shell-sourceable KEY=VALUE lines (or --yaml). Deterministic and offline.
"""

from __future__ import annotations

import argparse
import sys

# Lane -> the engine class and rigor the change has earned.
#
# `model` is a FAMILY-NEUTRAL tier name, never a vendor string. The adapter
# translates it, because the kernel spells no vendor — the same reason engines
# are one file each.
LANES = {
    "FAST": {
        "model": "haiku",
        "effort": "low",
        "base_seconds": 300,
        "max_iterations": 3,
        # A small reversible change does not earn a second engine's opinion.
        "verify": False,
    },
    "NORMAL": {
        "model": "sonnet",
        "effort": "medium",
        "base_seconds": 600,
        "max_iterations": 5,
        "verify": False,
    },
    "FULL": {
        "model": "opus",
        "effort": "high",
        "base_seconds": 900,
        "max_iterations": 15,
        # High blast radius is exactly where a green eval is least sufficient.
        "verify": True,
    },
}

# Effort -> how much ROOM the work needs, independent of rigor.
#
# XL/XXL are decomposition nodes and are absent on purpose: a node is never
# dispatched, so asking what one attempt at it costs is a category error. The
# delegation gate already refuses them; this refuses to price them.
EFFORT_MULTIPLIER = {"XS": 0.5, "S": 0.75, "M": 1.0, "L": 1.5}

NODE_SIZES = {"XL", "XXL"}


def resolve(effort: str, lane: str) -> dict:
    effort = (effort or "M").strip().upper()
    lane = (lane or "NORMAL").strip().upper()

    if effort in NODE_SIZES:
        raise SystemExit(
            f"COST_PROFILE=USAGE_ERROR\n"
            f"# effort '{effort}' is a decomposition NODE, not a runnable leaf.\n"
            f"# Dispatch its children; a node has no attempt to price."
        )
    if lane not in LANES:
        raise SystemExit(f"COST_PROFILE=USAGE_ERROR\n# unknown lane '{lane}'")
    if effort not in EFFORT_MULTIPLIER:
        raise SystemExit(f"COST_PROFILE=USAGE_ERROR\n# unknown effort '{effort}'")

    spec = LANES[lane]
    seconds = int(round(spec["base_seconds"] * EFFORT_MULTIPLIER[effort]))
    return {
        "lane": lane,
        "effort_tier": effort,
        "model": spec["model"],
        "reasoning_effort": spec["effort"],
        "attempt_seconds": seconds,
        "max_iterations": spec["max_iterations"],
        "verify": spec["verify"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve the per-attempt cost profile.")
    ap.add_argument("--effort", required=True, help="XS|S|M|L (the spec's effort)")
    ap.add_argument("--lane", default="NORMAL", help="FAST|NORMAL|FULL")
    # Explicit overrides win, so an operator is never boxed in by the table.
    ap.add_argument("--model")
    ap.add_argument("--reasoning-effort")
    ap.add_argument("--attempt-seconds", type=int)
    ap.add_argument("--yaml", action="store_true")
    args = ap.parse_args()

    profile = resolve(args.effort, args.lane)
    if args.model:
        profile["model"] = args.model
    if args.reasoning_effort:
        profile["reasoning_effort"] = args.reasoning_effort
    if args.attempt_seconds:
        profile["attempt_seconds"] = args.attempt_seconds

    if args.yaml:
        print("cost:")
        for key, value in profile.items():
            rendered = str(value).lower() if isinstance(value, bool) else value
            print(f"  {key}: {rendered}")
        print("COST_PROFILE=OK")
        return 0

    print(f"COST_LANE={profile['lane']}")
    print(f"COST_EFFORT_TIER={profile['effort_tier']}")
    print(f"COST_MODEL={profile['model']}")
    print(f"COST_REASONING={profile['reasoning_effort']}")
    print(f"COST_ATTEMPT_SECONDS={profile['attempt_seconds']}")
    print(f"COST_MAX_ITERATIONS={profile['max_iterations']}")
    print(f"COST_VERIFY={str(profile['verify']).lower()}")
    print("COST_PROFILE=OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
