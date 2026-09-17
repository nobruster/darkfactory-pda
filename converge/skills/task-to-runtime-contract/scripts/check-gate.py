#!/usr/bin/env python3
"""Inspect the one repository-root write fence, or test candidate paths."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_policy import (  # noqa: E402
    GatePolicyError,
    find_git_root,
    load_gate,
    normalize_repo_path,
)


def _candidate_roots(
    value: str,
    project_root: Path,
    git_root: Path,
) -> tuple[str, str]:
    raw = Path(value).expanduser()
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        canonical = normalize_repo_path(value)
        resolved = (project_root / canonical).resolve()
    try:
        project_relative = resolved.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise GatePolicyError(
            f"candidate escapes the consuming project: {value!r}"
        ) from exc
    try:
        git_relative = resolved.relative_to(git_root).as_posix()
    except ValueError as exc:
        raise GatePolicyError(
            f"candidate escapes the Git repository: {value!r}"
        ) from exc
    return normalize_repo_path(project_relative), normalize_repo_path(git_relative)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or query the repository-root write fence."
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="test a project-relative path (repeatable)",
    )
    parser.add_argument("--repo", default=".", help="consuming project root")
    args = parser.parse_args()

    project_root = Path(args.repo).expanduser().resolve()
    if not project_root.is_dir():
        print(f"Gate error: project does not exist: {project_root}")
        print("CHECK_GATE=ERROR")
        return 2
    try:
        git_root = find_git_root(project_root)
        project_root.relative_to(git_root)
        gate = load_gate(git_root)
    except (GatePolicyError, ValueError) as exc:
        print(f"Gate policy unreadable: {exc}")
        print("CHECK_GATE=ERROR")
        return 2

    if not gate.active and not args.path:
        print("No repository-root gate. The per-task contract is the only path fence.")
        print(f"Create {git_root / '.cvg/gate.yaml'} to add standing policy.")
        print("CHECK_GATE=ABSENT")
        return 0

    if gate.active:
        print(f"Repository write fence: {gate.source}")
        if project_root != git_root:
            print(f"  inherited by: {project_root.relative_to(git_root).as_posix()}")
        print(f"  schema_version   : {gate.schema_version}")
        print(
            f"  protected_paths  : {len(gate.protected_paths)} rule(s) "
            "— no Task-Spec may widen these"
        )
        for rule in gate.protected_paths:
            print(f"      {rule}")
        cap = (
            gate.max_changed_files
            if gate.max_changed_files is not None
            else "(no cap)"
        )
        print(f"  max_changed_files: {cap}")
    else:
        print(
            "No configured repository-root gate; built-in policy still protects "
            ".cvg/gate.yaml from task writes."
        )

    if args.path:
        print()
        forbidden = False
        normalized: list[str] = []
        try:
            for value in args.path:
                shown, git_path = _candidate_roots(value, project_root, git_root)
                normalized.append(git_path)
                rule = gate.forbids(git_path)
                if rule:
                    print(f"  REFUSED  {shown}  (rule: {rule})")
                    forbidden = True
                else:
                    print(f"  allowed  {shown}")
        except GatePolicyError as exc:
            print(f"  REFUSED  invalid path ({exc})")
            print("CHECK_GATE=FORBIDDEN")
            return 1
        if gate.active and gate.exceeds_blast_radius(len(set(normalized))):
            print(
                f"  REFUSED  {len(set(normalized))} unique paths exceed "
                f"max_changed_files={gate.max_changed_files}"
            )
            forbidden = True
        if forbidden:
            print("CHECK_GATE=FORBIDDEN")
            return 1

    print("CHECK_GATE=OK" if gate.active else "CHECK_GATE=ABSENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
