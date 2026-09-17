#!/usr/bin/env python3
"""Write the latest immutable-evidence execution receipt and archive its predecessor."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from _runtime_contract import (
    ContractError,
    load_profile,
    profile_task_path,
    relpath,
    resolve_inside_repo,
    resolve_repo,
    sha256_file,
    verify_signoff_pure,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a Pass 8 execution receipt.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--result", required=True, choices=["pass", "blocked"])
    parser.add_argument("--eval-output", required=True)
    parser.add_argument(
        "--path-policy", required=True, choices=["pass", "fail", "not-run"]
    )
    parser.add_argument("--agent", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--out")
    parser.add_argument(
        "--post-hoc",
        action="store_true",
        help=(
            "accept a spec that finished after binding (moved into a status "
            "bucket, frontmatter stamped by the POST-gate); requires the "
            "sign-off HMAC to still verify, and marks the receipt post_hoc"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        repo = resolve_repo(args.repo)
        profile_path = resolve_inside_repo(args.profile, repo)
        eval_output = Path(args.eval_output).expanduser().resolve()
        if not eval_output.is_file():
            raise ContractError(f"eval output file does not exist: {eval_output}")
        profile = load_profile(profile_path)
        try:
            task = profile_task_path(profile, repo)
        except ContractError:
            if not args.post_hoc:
                raise
            # A finished spec lives in a status bucket, not at the path Pass 7
            # bound. Same defect class as the validate and register fixes:
            # done/ must stay KNOWN.
            bound = Path(str(profile["task"]["spec_ref"]["path"]))
            task = None
            for bucket in ("done", "parked", "queue"):
                candidate = resolve_inside_repo(
                    str(bound.parent / bucket / bound.name), repo, must_exist=False
                )
                if candidate.is_file():
                    task = candidate
                    break
            if task is None:
                raise
        task_id = str(profile.get("task", {}).get("id", ""))
        if not task_id:
            raise ContractError("profile has no task id")
        expected_spec_hash = profile["task"]["spec_ref"]["sha256"]
        spec_hash = sha256_file(task)
        post_hoc = False
        if spec_hash != expected_spec_hash:
            if not args.post_hoc:
                raise ContractError("Task-Spec changed after runtime binding")
            # The POST-gate legitimately mutates frontmatter (status move,
            # accepted stamps) after settlement, so the bind-time hash cannot
            # match. The honesty bar for a post-hoc receipt is the sign-off
            # envelope: the eval bodies must be exactly what was sealed.
            tool_home = Path(__file__).resolve().parents[3]
            tier, note = verify_signoff_pure(task, repo, tool_home)
            if tier != 1:
                raise ContractError(
                    f"post-hoc refused: sign-off not verified ({note})"
                )
            post_hoc = True
        output = (
            resolve_inside_repo(args.out, repo, must_exist=False)
            if args.out
            else resolve_inside_repo(
                str(profile.get("receipt", {}).get("path", "")),
                repo,
                must_exist=False,
            )
        )
        payload = {
            "schema": "cvg.execution-receipt.v1",
            "task_id": task_id,
            "result": args.result,
            "task_spec": {
                "path": relpath(task, repo),
                "sha256": spec_hash,
            },
            "execution_profile": {
                "path": relpath(profile_path, repo),
                "sha256": sha256_file(profile_path),
            },
            "evaluation": {
                "output_sha256": sha256_file(eval_output),
                "path_policy": args.path_policy,
            },
            "runtime": {"agent": args.agent, "branch": args.branch},
            "recorded_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "generated_by": (
                "write-execution-receipt --post-hoc" if post_hoc else "task-loop"
            ),
        }
        if post_hoc:
            payload["post_hoc"] = True
            payload["task_spec"]["sha256_at_bind"] = expected_spec_hash
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.read_text(encoding="utf-8") != rendered:
            previous = output.read_bytes()
            suffix = hashlib.sha256(previous).hexdigest()[:12]
            archive = output.with_name(
                f"{output.stem}.attempt-{suffix}{output.suffix}"
            )
            if not archive.exists():
                archive.write_bytes(previous)
        output.write_text(rendered, encoding="utf-8")
        print(f"Execution receipt written: {relpath(output, repo)}")
        print("EXECUTION_RECEIPT=PASS" if args.result == "pass" else "EXECUTION_RECEIPT=BLOCKED")
        return 0
    except (ContractError, KeyError, TypeError) as exc:
        print(f"Execution receipt failed: {exc}")
        print("EXECUTION_RECEIPT=FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
