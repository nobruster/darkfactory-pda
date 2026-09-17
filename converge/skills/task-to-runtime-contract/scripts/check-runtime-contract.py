#!/usr/bin/env python3
"""Deterministic readiness gate for a Pass 6 execution profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _runtime_contract import (
    CLOSURE_EVENTS,
    ContractError,
    SCHEMA,
    authority_epoch,
    do_not_touch,
    infer_primary_runtime,
    load_profile,
    parse_frontmatter,
    profile_task_path,
    relpath,
    resolve_inside_repo,
    resolve_repo,
    run_signoff_gate,
    verify_signoff_pure,
    sha256_file,
    task_paths,
    unresolved_placeholder,
    validate_topology,
    weakest_link,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a Pass 6 runtime contract.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--tool-home")
    parser.add_argument("--supervised", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    findings: list[str] = []
    try:
        repo = resolve_repo(args.repo)
        tool_home = resolve_repo(args.tool_home) if args.tool_home else Path(__file__).resolve().parents[3]
        profile_path = resolve_inside_repo(args.profile, repo)
        profile = load_profile(profile_path)
        if profile.get("schema") != SCHEMA:
            findings.append(f"unsupported schema: {profile.get('schema')!r}")
        if unresolved_placeholder(profile_path.read_text(encoding="utf-8")):
            findings.append("execution profile contains an unresolved placeholder")

        task = profile_task_path(profile, repo)
        expected = profile.get("task", {}).get("spec_ref", {}).get("sha256")
        actual = sha256_file(task)
        if expected != actual:
            findings.append(
                f"stale profile: Task-Spec hash mismatch ({expected} != {actual})"
            )
        authorization = profile.get("task", {}).get("authorization", {})
        supervised = bool(args.supervised or not authorization.get("requires_tier1", True))
        # WP2 — READ-ONLY. Recompute the HMAC directly instead of shelling out to
        # the delegation gate, which runs the task's evals and can write state. A
        # check that executes untrusted project code is not a check.
        tier, note = verify_signoff_pure(task, repo, tool_home)
        if tier == 3:
            findings.append(f"sign-off is not verifiable: {note}")
        elif tier != authorization.get("trust_tier"):
            findings.append(
                f"trust tier drift: profile={authorization.get('trust_tier')} "
                f"current={tier} ({note})"
            )
        elif tier == 2 and not supervised:
            findings.append(f"Tier 2 requires supervised dispatch: {note}")

        frontmatter, body = parse_frontmatter(task)
        allowed = task_paths(frontmatter)
        forbidden = do_not_touch(body)
        if not allowed:
            findings.append("Task-Spec has no writable scope")
        for rule in forbidden:
            if rule in allowed:
                findings.append(f"path appears in both allowed and forbidden scope: {rule}")

        context = profile.get("context", {})
        for group, key in (
            ("required file", "required_files"),
            ("approved knowledge", "approved_project_knowledge"),
        ):
            for entry in context.get(key, []):
                try:
                    path = resolve_inside_repo(str(entry["path"]), repo)
                    if sha256_file(path) != entry.get("sha256"):
                        findings.append(f"{group} hash mismatch: {entry.get('path')}")
                except (ContractError, KeyError, TypeError) as exc:
                    findings.append(f"invalid {group} entry: {exc}")
        for entry in context.get("external_docs", []):
            try:
                path = resolve_inside_repo(str(entry["cache_path"]), repo)
                if not str(entry.get("url", "")).startswith(("https://", "http://")):
                    findings.append(f"external doc has invalid URL: {entry.get('url')}")
                if sha256_file(path) != entry.get("sha256"):
                    findings.append(
                        f"external doc cache hash mismatch: {entry.get('cache_path')}"
                    )
            except (ContractError, KeyError, TypeError) as exc:
                findings.append(f"invalid external doc entry: {exc}")

        topology = profile.get("topology", {})
        findings.extend(
            validate_topology(
                str(topology.get("mode", "")),
                str(topology.get("justification", "")),
                topology.get("workers", [])
                if topology.get("mode") == "parallel"
                else [],
                allowed,
            )
        )

        enforcement = profile.get("enforcement", {})
        if enforcement.get("path_policy_source") != "task_spec":
            findings.append("path policy must resolve from the Task-Spec")
        if enforcement.get("portable_postflight_required") is not True:
            findings.append("portable postflight path guard is not mandatory")
        for key in ("candidate_guard", "tool_input_guard", "receipt_writer"):
            value = enforcement.get(key)
            if not value:
                findings.append(f"enforcement.{key} is missing")
                continue
            guard = tool_home / str(value)
            if not guard.is_file():
                findings.append(f"declared guard does not exist: {guard}")
        adapter_entries = enforcement.get("adapters", [])
        if not adapter_entries:
            findings.append("no runtime adapter manifest is declared")
        for entry in adapter_entries:
            try:
                adapter_path = resolve_inside_repo(str(entry["path"]), repo)
                adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
                if adapter.get("execution_profile") != relpath(profile_path, repo):
                    findings.append(f"adapter points at wrong profile: {entry.get('path')}")
                if not adapter.get("postflight_command"):
                    findings.append(f"adapter lacks postflight command: {entry.get('path')}")
                if unresolved_placeholder(adapter_path.read_text(encoding="utf-8")):
                    findings.append(f"adapter contains unresolved placeholder: {entry.get('path')}")
            except (ContractError, KeyError, OSError, json.JSONDecodeError) as exc:
                findings.append(f"invalid adapter entry: {exc}")

        # --- The capability envelope: authority must be epoch-bound and closed.
        authority = profile.get("authority", {})
        if not authority:
            findings.append("profile declares no capability envelope (authority block)")
        else:
            expected_epoch = authority_epoch(str(profile.get("task", {}).get("id", "")), actual)
            if authority.get("epoch") != expected_epoch:
                findings.append(
                    "authority epoch does not match the signed spec revision "
                    f"({authority.get('epoch')} != {expected_epoch}) — re-bind to mint a new epoch"
                )
            closure = authority.get("closure", {})
            if closure.get("revocation_is_mandatory") is not True:
                findings.append("capability closure is not mandatory — authority would linger")
            missing_events = sorted(set(CLOSURE_EVENTS) - set(closure.get("revoke_on", [])))
            if missing_events:
                findings.append(
                    f"closure does not revoke on: {', '.join(missing_events)}"
                )
            granted_write = next(
                (g for g in authority.get("grants", []) if g.get("capability") == "fs.write"),
                None,
            )
            if not granted_write:
                findings.append("capability envelope grants no fs.write scope")
            elif sorted(granted_write.get("scope", [])) != sorted(allowed):
                findings.append(
                    "fs.write grant drifted from the Task-Spec's declared scope — re-bind"
                )

        # --- The resolver manifest: no adapter may weaken a required control silently.
        needed = enforcement.get("required_controls") or []
        primary = enforcement.get("primary_runtime")
        inferred_runtime, inferred_source = infer_primary_runtime(frontmatter)
        selection = enforcement.get("runtime_selection")
        waived = set(enforcement.get("unenforced_waivers") or [])
        if not needed:
            findings.append("enforcement declares no required controls")
        if not primary:
            findings.append("enforcement declares no primary runtime")
        else:
            if selection is None:
                # Pre-provenance profiles remain readable, but may not
                # contradict the runtime selected by their sealed Task-Spec.
                if primary != inferred_runtime:
                    findings.append(
                        "primary runtime drift: legacy profile selects "
                        f"'{primary}', Task-Spec selects '{inferred_runtime}' "
                        f"via {inferred_source} — re-bind"
                    )
            elif not isinstance(selection, dict):
                findings.append("enforcement.runtime_selection must be an object")
            else:
                source = selection.get("source")
                if selection.get("inferred_runtime") != inferred_runtime:
                    findings.append(
                        "runtime selection inference drift: profile records "
                        f"'{selection.get('inferred_runtime')}', Task-Spec selects "
                        f"'{inferred_runtime}' — re-bind"
                    )
                if selection.get("inferred_source") != inferred_source:
                    findings.append(
                        "runtime selection source drift: profile records "
                        f"'{selection.get('inferred_source')}', expected "
                        f"'{inferred_source}' — re-bind"
                    )
                if source == "operator_override":
                    pass
                elif source != inferred_source or primary != inferred_runtime:
                    findings.append(
                        "primary runtime drift: profile selection "
                        f"'{primary}' via {source!r} does not match Task-Spec "
                        f"selection '{inferred_runtime}' via {inferred_source} "
                        "— re-bind or record an explicit operator override"
                    )
            resolution = next(
                (
                    e.get("resolution")
                    for e in adapter_entries
                    if e.get("runtime") == primary
                ),
                None,
            )
            if not resolution:
                findings.append(
                    f"primary runtime '{primary}' has no resolver manifest"
                )
            else:
                unenforced = [
                    cap
                    for cap in resolution.get("unenforced_required", [])
                    if cap not in waived
                ]
                if unenforced:
                    findings.append(
                        f"runtime '{primary}' cannot enforce required control(s): "
                        f"{', '.join(unenforced)} — select a runtime that can, drop the "
                        f"requirement, or waive it explicitly with --accept-unenforced"
                    )
                declared = enforcement.get("assurance")
                computed = weakest_link([resolution])
                if declared != computed:
                    findings.append(
                        f"assurance claim is dishonest: profile says '{declared}', "
                        f"resolver proves '{computed}'"
                    )
                for cap in waived:
                    print(
                        f"WAIVED: '{cap}' is required but unenforced on '{primary}' "
                        "— accepted by explicit operator approval",
                        file=sys.stderr,
                    )

        # --- 7B: the task brief must exist and belong to THIS epoch.
        brief_rel = enforcement.get("task_brief")
        if not brief_rel:
            findings.append("profile declares no task brief (7B)")
        else:
            try:
                brief_path = resolve_inside_repo(str(brief_rel), repo)
                brief_text = brief_path.read_text(encoding="utf-8")
                epoch = str(authority.get("epoch", ""))
                if epoch and epoch not in brief_text:
                    findings.append(
                        "task brief is stale: it does not carry the current epoch — re-bind"
                    )
                if unresolved_placeholder(brief_text):
                    findings.append("task brief contains an unresolved placeholder")
            except (ContractError, OSError) as exc:
                findings.append(f"task brief is missing or unreadable: {exc}")

        generated = profile.get("generated", {})
        if generated.get("by") != "task-to-runtime-contract":
            findings.append("profile generator identity is missing or stale")
        for label, value in (
            ("receipt.path", profile.get("receipt", {}).get("path")),
            (
                "knowledge.candidate_output",
                profile.get("knowledge", {}).get("candidate_output"),
            ),
        ):
            if not value:
                findings.append(f"{label} is missing")
                continue
            try:
                resolve_inside_repo(str(value), repo, must_exist=False)
            except ContractError as exc:
                findings.append(f"invalid {label}: {exc}")
    except ContractError as exc:
        findings.append(str(exc))

    if findings:
        print("Runtime contract is not ready:")
        for item in findings:
            print(f"  - {item}")
        print("CHECK_RUNTIME_CONTRACT=FAIL")
        return 1
    print("Runtime contract ready: task hash, evidence, topology, and guards verified.")
    print("CHECK_RUNTIME_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
