#!/usr/bin/env python3
"""Create a receipt-backed project-knowledge candidate without auto-promoting it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _runtime_contract import (
    ContractError,
    load_profile,
    relpath,
    resolve_inside_repo,
    resolve_repo,
    sha256_file,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Propose earned project knowledge.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--kind", required=True, choices=["failure", "pattern", "reference"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--out")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        repo = resolve_repo(args.repo)
        profile_path = resolve_inside_repo(args.profile, repo)
        receipt_path = resolve_inside_repo(args.receipt, repo)
        profile = load_profile(profile_path)
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractError(f"receipt is not JSON: {exc}") from exc
        if not isinstance(receipt, dict) or receipt.get("result") not in {
            "pass",
            "blocked",
        }:
            raise ContractError("receipt.result must be pass or blocked")
        task_id = str(profile.get("task", {}).get("id", ""))
        if not task_id:
            raise ContractError("profile has no task id")
        if str(receipt.get("task_id", "")) != task_id:
            raise ContractError("receipt task_id does not match the profile")
        summary = args.summary.strip()
        evidence = args.evidence.strip()
        if len(summary) < 20 or len(evidence) < 20:
            raise ContractError("summary and evidence must each be at least 20 characters")

        output = (
            resolve_inside_repo(args.out, repo, must_exist=False)
            if args.out
            else repo / str(profile["knowledge"]["candidate_output"])
        )
        spec_hash = profile["task"]["spec_ref"]["sha256"]
        rendered = (
            "---\n"
            "schema: cvg.knowledge-candidate.v1\n"
            f"task_id: {task_id}\n"
            f"task_spec_sha256: {spec_hash}\n"
            f"receipt_path: {relpath(receipt_path, repo)}\n"
            f"receipt_sha256: {sha256_file(receipt_path)}\n"
            f"kind: {args.kind}\n"
            "status: proposed\n"
            "generated_by: task-to-runtime-contract\n"
            "---\n\n"
            f"# {summary}\n\n"
            "## Evidence\n\n"
            f"{evidence}\n\n"
            "## Promotion boundary\n\n"
            "This candidate is not canonical project knowledge until an owner or "
            "designated reviewer approves and moves it into the appropriate "
            "`cvg/knowledge/` collection.\n"
        )
        target = output
        if output.exists() and output.read_text(encoding="utf-8") != rendered:
            target = output.with_name(output.stem + ".proposed" + output.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        print(f"Knowledge candidate written: {relpath(target, repo)}")
        print("KNOWLEDGE_CANDIDATE=PROPOSED")
        return 0
    except (ContractError, KeyError, TypeError) as exc:
        print(f"Knowledge candidate failed: {exc}")
        print("KNOWLEDGE_CANDIDATE=FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

