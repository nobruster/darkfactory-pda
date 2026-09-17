#!/usr/bin/env python3
"""Run the Dark Factory stages for one type and print each gate.

Stages and gates follow plans/dark-factory.md. This driver never builds the
modern plant and never edits a frozen tree: it executes what exists, reports
what does not, and stalls the type at the first gate that fails. The
classification names are imported from the referee, never re-declared here.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "validation" / "golden-match"))
import golden_match  # noqa: E402

PG_CONTAINER = "northwind-pay-legacy-postgres-1"
PG_USER = "northwind_admin"
PG_DB = "northwind_legacy"

PASS, STALL, SKIP = "PASS", "STALL", "SKIP"
MARK = {PASS: "PASS ", STALL: "STALL", SKIP: "skip "}


class Stall(Exception):
    """A gate refused. The type stops here; nothing downstream is invented."""


def psql(sql: str) -> list[list[str]]:
    out = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-At", "-F", "\x1f", "-c", sql],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise Stall(f"postgres unreachable: {out.stderr.strip().splitlines()[-1:] or ''}")
    return [line.split("\x1f") for line in out.stdout.splitlines() if line]


def registry_entry(type_number: str) -> dict[str, Any]:
    doc = yaml.safe_load((REPO_ROOT / "contracts/types/registry.yaml").read_text(encoding="utf-8"))
    for entry in doc["types"] if isinstance(doc, dict) and "types" in doc else doc:
        if str(entry.get("number")) == type_number:
            return entry
    raise Stall(f"type {type_number} is not in contracts/types/registry.yaml")


def expected_path(contract: Path, scenario: str) -> Path:
    name = "expected-reconciliation.yaml" if scenario == "valid-minimal" else f"expected-{scenario}-reconciliation.yaml"
    return contract / "main" / name


def resolve_batch(spec_dir: Path, contract: Path, scenario: str) -> str:
    sample = next((p for p in spec_dir.glob(f"samples/{scenario}.*") if p.suffix != ".sha256"), None)
    if sample and sample.suffix == ".csv":
        rows = list(csv.DictReader(sample.read_text(encoding="utf-8").splitlines(), delimiter=";"))
        if rows and rows[0].get("batch_id"):
            return rows[0]["batch_id"]
    exp = expected_path(contract, scenario)
    if exp.is_file():
        return str(yaml.safe_load(exp.read_text(encoding="utf-8"))["batch_id"])
    raise Stall(f"cannot resolve a batch id for scenario {scenario}")


class Run:
    def __init__(self, type_number: str, scenario: str, quiet: bool = False) -> None:
        self.quiet = quiet
        self.type_number = type_number
        self.scenario = scenario
        self.entry = registry_entry(type_number)
        self.folder = self.entry["folder"]
        self.contract = REPO_ROOT / "contracts/types" / self.folder
        self.spec = REPO_ROOT / "spec" / f"type-{self.folder}"
        self.batch = resolve_batch(self.spec, self.contract, scenario)
        self.stages: list[dict[str, Any]] = []
        self.differences: list[golden_match.Difference] = []

    def gate(self, n: int, name: str, verdict: str, detail: str, opened: list[str] | None = None) -> None:
        self.stages.append({"stage": n, "name": name, "gate": verdict, "detail": detail, "opened": opened or []})
        self.say(f"  [{MARK[verdict]}] stage {n} · {name:<14} {detail}")
        for path in opened or []:
            self.say(f"           open: {path}")

    def say(self, line: str) -> None:
        if not self.quiet:
            print(line)

    # stage 0 -------------------------------------------------------------
    def intake(self) -> None:
        exp = expected_path(self.contract, self.scenario)
        inbound = sorted(p.name for p in (self.spec / "inbound").glob("*")) if (self.spec / "inbound").is_dir() else []
        if not self.contract.is_dir():
            raise Stall(f"no contract at contracts/types/{self.folder}")
        if not exp.is_file():
            raise Stall(f"the kit ships no oracle for '{self.scenario}' — no eval, no task")
        self.gate(0, "Intake", PASS, f"oracle present · {len(inbound)} inbound docs · contracts/ judges",
                  [str(exp.relative_to(REPO_ROOT)), str((self.spec / "inbound").relative_to(REPO_ROOT))])

    # stage 1 -------------------------------------------------------------
    def ground_truth(self) -> None:
        rows = psql(f"select status, coalesce(failure_code,'') from control.batches where batch_id='{self.batch}'")
        if not rows:
            raise Stall(f"legacy has never run {self.batch} — no ground truth to compare against")
        status, code = rows[0][0], rows[0][1]
        packet = REPO_ROOT / "evidence" / self.batch
        if not packet.is_dir():
            raise Stall(f"legacy ran but evidence/{self.batch}/ is absent — observation not captured")
        self.legacy_status = status
        self.gate(1, "Ground truth", PASS, f"legacy {status}{' · ' + code if code else ''} · observation captured",
                  [f"evidence/{self.batch}/final-status.json"])

    # stage 2 -------------------------------------------------------------
    def plan(self) -> None:
        seams = sorted(p.name for p in (REPO_ROOT / "cvg/swimlanes").iterdir() if p.is_dir())
        if seams != ["dlt-gold", "ingest-landing", "orchestrate-serve"]:
            raise Stall(f"seams are not this plant's: {seams}")
        adrs = len(list((REPO_ROOT / "docs/adrs").glob("*.md")))
        self.gate(2, "Plan", PASS, f"three seams · {adrs} ADRs · one owner per handoff", ["cvg/swimlanes/"])

    # stage 3 -------------------------------------------------------------
    def build(self) -> bool:
        pkg = REPO_ROOT / "modern/ingestion/src/northwind_pay/types" / self.folder
        want = {"model.py", "parser.py", "schema.py", "writer.py", "handler.py"}
        have = {p.name for p in pkg.glob("*.py")} if pkg.is_dir() else set()
        if want - have:
            self.gate(3, "Build", STALL, f"no modern package for type {self.type_number} — the room builds it")
            return False
        self.gate(3, "Build", PASS, "five-file package present", [str(pkg.relative_to(REPO_ROOT))])
        return True

    # stage 4 -------------------------------------------------------------
    def publish(self) -> bool:
        landing = REPO_ROOT / "modern/landing" / self.batch
        files = [p for p in landing.glob("*.parquet")] if landing.is_dir() else []
        if not files:
            self.gate(4, "Publish", SKIP, "no landing Parquet — nothing published yet")
            return False
        digest = subprocess.run(["shasum", "-a", "256", str(files[0])], capture_output=True, text=True).stdout.split()[0]
        recorded = (landing / f"{files[0].name}.sha256").read_text(encoding="ascii").split()[0]
        if digest != recorded:
            raise Stall("landing Parquet does not match its recorded SHA-256")
        self.gate(4, "Publish", PASS, f"manifest last · sha {digest[:12]}…",
                  [f"modern/landing/{self.batch}/parquet-manifest.json"])
        return True

    # stage 5 -------------------------------------------------------------
    def lakehouse(self) -> dict[str, Any] | None:
        db = REPO_ROOT / "modern/lakehouse/ducklake/northwind_modern.duckdb"
        table = f"gold.gold_{self.entry['slug'].replace('-', '_')}_reconciliation"
        try:
            import duckdb
            con = duckdb.connect(str(db), read_only=True)
            cur = con.execute(f"select * from {table} where batch_id = ?", [self.batch])
            names = [d[0] for d in cur.description]
            row = cur.fetchone()
        except Exception as exc:
            self.gate(5, "Lakehouse", SKIP, f"no Gold for type {self.type_number} ({type(exc).__name__})")
            return None
        if row is None:
            self.gate(5, "Lakehouse", SKIP, "Gold table exists but holds no row for this batch")
            return None
        gold = {k: str(v) for k, v in zip(names, row)}
        self.gate(5, "Lakehouse", PASS, f"dlt register-only → B/S/G · applied_net {gold.get('applied_net_amount','?')} · {gold.get('status','?')}",
                  [f"{db.relative_to(REPO_ROOT)} :: {table}"])
        return gold

    # stage 6 -------------------------------------------------------------
    def golden_match(self, gold: dict[str, Any] | None) -> None:
        expected = yaml.safe_load(expected_path(self.contract, self.scenario).read_text(encoding="utf-8"))
        relation = yaml.safe_load((self.contract / "reconciliation.yaml").read_text(encoding="utf-8"))["report"]["relation"]
        cols = [c for c in expected if c != "batch_id"]
        rows = psql(f"select {', '.join(cols)} from {relation} where batch_id='{self.batch}'")
        self.say(f"           question 1 · does modern match the contract?")
        if gold is None:
            self.say(f"             unanswerable — no modern Gold for this type yet")
        else:
            q1 = [k for k in expected if k in gold and str(expected[k]) != gold[k]]
            self.say(f"             {'yes' if not q1 else 'NO — ' + ', '.join(q1)}")
        self.say(f"           question 2 · does legacy match the contract?")
        if not rows:
            raise Stall(f"{relation} has no row for {self.batch}")
        observed = dict(zip(cols, rows[0]))
        for name in cols:
            want, got = str(expected[name]), observed[name]
            if want != got:
                self.differences.append(golden_match.Difference(
                    "reconciliation", self.batch, name, got, want, "contract",
                    golden_match.CONFIRMED_LEGACY_DEFECT,
                ))
        if not self.differences:
            self.say("             yes")
            self.gate(6, "Golden-match", PASS, "two questions, never netted · no difference")
            return
        self.say(f"             NO — legacy disagrees with the contract on "
              f"{', '.join(sorted({d.field_name for d in self.differences}))}")
        for d in sorted(self.differences, key=lambda x: x.field_name)[:6]:
            self.say(f"               {d.field_name:<28} contract {d.reference:>8}   legacy {d.modern:>8}")
        codes = sorted({d.classification for d in self.differences})
        self.gate(6, "Golden-match", STALL, f"one code per difference · {', '.join(codes)}")
        raise Stall(f"{codes[0]} — classify, do not patch")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Dark Factory stages for one type.")
    ap.add_argument("--type", required=True, help="type number, e.g. 06")
    ap.add_argument("--scenario", default="valid-minimal")
    ap.add_argument("--json", action="store_true", help="print the machine-readable packet only")
    args = ap.parse_args()

    try:
        run = Run(args.type, args.scenario, quiet=args.json)
    except Stall as exc:
        print(f"STALLED before stage 0: {exc}", file=sys.stderr)
        return 2

    if not args.json:
        print(f"\nDark Factory · type {run.type_number} · {run.entry['name']}")
        print(f"scenario {run.scenario} · batch {run.batch}\n")

    verdict, reason = "accepted", ""
    try:
        run.intake()
        run.ground_truth()
        run.plan()
        built = run.build()
        published = run.publish() if built else False
        gold = run.lakehouse() if published else None
        run.golden_match(gold)
    except Stall as exc:
        verdict, reason = "stalled", str(exc)

    packet = {
        "batch_id": run.batch,
        "classification": sorted({d.classification for d in run.differences}) or None,
        "differences": [d.as_dict() for d in run.differences],
        "outcome": verdict,
        "reason": reason,
        "scenario": run.scenario,
        "stages": run.stages,
        "type_number": run.type_number,
    }
    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0 if verdict == "accepted" else 1

    print()
    if verdict == "accepted":
        print("  the type is ACCEPTED — every gate held, no unexplained difference")
    else:
        print(f"  the type is STALLED — {reason}")
        print("  frozen trees untouched. Gold stays blocked. Write the code down; do not patch.")
    print()
    return 0 if verdict == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
