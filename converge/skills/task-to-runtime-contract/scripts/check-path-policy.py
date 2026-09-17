#!/usr/bin/env python3
"""Enforce the trusted repository gate and one Task-Spec write scope."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from _gate_policy import (
    GatePolicyError,
    find_git_root,
    load_gate,
    load_gate_from_git,
    normalize_repo_path,
)
from _runtime_contract import (
    ContractError,
    do_not_touch,
    load_profile,
    parse_frontmatter,
    path_allowed,
    profile_task_path,
    resolve_inside_repo,
    resolve_repo,
    task_paths,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check repository changes against standing and task policy."
    )
    parser.add_argument("--profile")
    parser.add_argument("--repo")
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument(
        "--base",
        help="trusted starting commit; defaults to HEAD for a worktree diff",
    )
    parser.add_argument("--paths-from-stdin", action="store_true")
    parser.add_argument(
        "--gate-only",
        action="store_true",
        help="enforce the repository gate without a Task-Spec profile",
    )
    args = parser.parse_args()
    if not args.gate_only and not args.profile:
        parser.error("--profile is required unless --gate-only is used")
    return args


def _git_z(repo: Path, args: list[str], failure: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        message = os.fsdecode(proc.stderr).strip()
        raise ContractError(message or failure)
    values = []
    for raw in proc.stdout.split(b"\0"):
        if raw:
            values.append(os.fsdecode(raw))
    return values


def diff_paths(git_root: Path, base: str | None) -> list[str]:
    """Return every Git-visible changed endpoint, repository-root-relative."""
    changed: list[str] = []
    if base:
        changed.extend(
            _git_z(
                git_root,
                ["diff", "--no-renames", "--name-only", "-z", f"{base}...HEAD"],
                "git base diff failed",
            )
        )
    changed.extend(
        _git_z(
            git_root,
            ["diff", "--no-renames", "--name-only", "-z", "HEAD"],
            "git worktree diff failed",
        )
    )
    changed.extend(
        _git_z(
            git_root,
            ["ls-files", "--others", "--exclude-standard", "-z"],
            "git untracked-file scan failed",
        )
    )
    return sorted({normalize_repo_path(path) for path in changed})


def _candidate_paths(
    value: str,
    workspace: Path,
    git_root: Path,
) -> tuple[str | None, str | None]:
    """Return ``(workspace_relative, git_relative)`` for one candidate."""
    raw = Path(value).expanduser()
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        canonical = normalize_repo_path(value)
        resolved = (workspace / canonical).resolve()

    workspace_relative: str | None
    git_relative: str | None
    try:
        workspace_relative = normalize_repo_path(
            resolved.relative_to(workspace).as_posix()
        )
    except ValueError:
        workspace_relative = None
    try:
        git_relative = normalize_repo_path(
            resolved.relative_to(git_root).as_posix()
        )
    except ValueError:
        git_relative = None
    return workspace_relative, git_relative


def _workspace_path(
    git_path: str,
    workspace_prefix: str,
) -> str | None:
    if not workspace_prefix:
        return git_path
    prefix = workspace_prefix + "/"
    if git_path.startswith(prefix):
        return git_path[len(prefix) :]
    return None


def _is_framework_path(path: str, profile: dict) -> bool:
    receipt_value = str(profile.get("receipt", {}).get("path", ""))
    framework_paths = {receipt_value} if receipt_value else set()
    enforcement = profile.get("enforcement", {})
    profile_path = str(profile.get("_profile_path", ""))
    if profile_path:
        framework_paths.add(profile_path)
    brief_path = str(enforcement.get("task_brief", ""))
    if brief_path:
        framework_paths.add(brief_path)
    for entry in enforcement.get("adapters", []):
        if isinstance(entry, dict) and entry.get("path"):
            framework_paths.add(str(entry["path"]))
    task_id = str(profile.get("task", {}).get("id", "")).strip()
    if task_id:
        framework_paths.add(f"cvg/execution/{task_id}/task-handoff.json")
    task_dir = Path(profile["task"]["spec_ref"]["path"]).parent
    framework_paths.update(
        {
            (task_dir / "_state.yaml").as_posix(),
            (task_dir / "_metrics.jsonl").as_posix(),
            "cvg/STATE.md",
        }
    )
    if path in framework_paths:
        return True
    loop_prefixes = ["cvg/loop/"]
    if task_id:
        loop_prefixes.append(f"cvg/loop/{task_id}/")
    if any(path.startswith(prefix) for prefix in loop_prefixes):
        return True
    if receipt_value:
        receipt = Path(receipt_value)
        candidate = Path(path)
        if (
            candidate.parent == receipt.parent
            and candidate.name.startswith(receipt.stem + ".attempt-")
            and candidate.suffix == receipt.suffix
        ):
            return True
    return False


def _fail_gate(gate, root_paths: list[str]) -> int | None:
    hits = gate.violations(root_paths)
    if hits:
        source = gate.source or "<built-in policy self-protection>"
        print(
            f"Repository gate ({source}) forbids these paths "
            "— no spec may widen this:"
        )
        for path, rule in hits:
            print(f"  - {path}  (protected_paths rule: {rule})")
        print("CHECK_PATH_POLICY=FAIL")
        return 1
    if gate.active and gate.exceeds_blast_radius(len(root_paths)):
        print(
            f"Repository gate ({gate.source}): {len(root_paths)} changed paths "
            f"exceeds max_changed_files={gate.max_changed_files}. Every path may "
            "be in task scope and the settlement blast radius is still too large."
        )
        print("CHECK_PATH_POLICY=FAIL")
        return 1
    return None


def main() -> int:
    args = arguments()
    try:
        workspace = resolve_repo(args.repo)
        git_root = find_git_root(workspace)
        try:
            workspace_prefix = workspace.relative_to(git_root).as_posix()
        except ValueError as exc:
            raise ContractError(
                f"consuming project is outside its Git repository: {workspace}"
            ) from exc
        if workspace_prefix == ".":
            workspace_prefix = ""

        supplied = list(args.candidate)
        if args.paths_from_stdin:
            supplied.extend(line.rstrip("\r\n") for line in sys.stdin if line.strip())
        diff_mode = not supplied and not args.paths_from_stdin

        workspace_paths: list[str] = []
        root_paths: list[str] = []
        outside_workspace: list[str] = []
        outside_git: list[str] = []

        if diff_mode:
            trusted_ref = args.base or "HEAD"
            root_paths = diff_paths(git_root, args.base)
            gate = load_gate_from_git(git_root, trusted_ref)
            for path in root_paths:
                local = _workspace_path(path, workspace_prefix)
                if local is None:
                    outside_workspace.append(path)
                else:
                    workspace_paths.append(local)
        else:
            gate = load_gate(git_root)
            for value in supplied:
                local, root_path = _candidate_paths(value, workspace, git_root)
                if root_path is None:
                    outside_git.append(value)
                else:
                    root_paths.append(root_path)
                if local is None:
                    outside_workspace.append(value)
                else:
                    workspace_paths.append(local)
            root_paths = sorted(set(root_paths))

        gate_failure = _fail_gate(gate, root_paths)
        if gate_failure is not None:
            return gate_failure

        if outside_git:
            print("Paths outside the Git repository:")
            for path in outside_git:
                print(f"  - {path}")
            print("CHECK_PATH_POLICY=FAIL")
            return 1
        if outside_workspace:
            print("Changes outside the consuming project:")
            for path in sorted(set(outside_workspace)):
                print(f"  - {path}")
            print("CHECK_PATH_POLICY=FAIL")
            return 1

        if args.gate_only:
            source = f" ({gate.source})" if gate.active else ""
            print(
                f"Repository gate ready: {len(root_paths)} path(s) checked{source}."
            )
            print("CHECK_PATH_POLICY=PASS")
            return 0

        profile_path = resolve_inside_repo(str(args.profile), workspace)
        profile = load_profile(profile_path)
        profile["_profile_path"] = normalize_repo_path(
            profile_path.relative_to(workspace).as_posix()
        )
        task = profile_task_path(profile, workspace)
        frontmatter, body = parse_frontmatter(task)
        allowed = task_paths(frontmatter)
        forbidden = do_not_touch(body)

        # Framework evidence is exempt only from the task's scope. It was
        # already evaluated by the standing gate and blast-radius cap above.
        if diff_mode:
            workspace_paths = [
                path
                for path in workspace_paths
                if not _is_framework_path(path, profile)
            ]

        if not workspace_paths:
            print("No task-owned changed paths.")
            print("CHECK_PATH_POLICY=PASS")
            return 0

        violations = [
            path
            for path in sorted(set(workspace_paths))
            if not path_allowed(path, allowed, forbidden)
        ]
        if violations:
            print("Out-of-scope paths:")
            for path in violations:
                print(f"  - {path}")
            print("CHECK_PATH_POLICY=FAIL")
            return 1

        fence = f" · repository gate {gate.source}" if gate.active else ""
        print(
            f"Path policy ready: {len(set(workspace_paths))} path(s) inside "
            f"Task-Spec scope{fence}."
        )
        print("CHECK_PATH_POLICY=PASS")
        return 0
    except (ContractError, GatePolicyError) as exc:
        print(f"Path policy error: {exc}")
        print("CHECK_PATH_POLICY=FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
