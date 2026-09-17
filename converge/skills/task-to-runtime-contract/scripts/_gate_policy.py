"""Strict repository-root write-fence policy.

The Task-Spec says where one task may write. The repository gate says where no
unattended task may write and how many changed paths one settlement may carry.
The latter is standing repository policy, so it is loaded from the Git root and,
during settlement, from the captured base commit rather than the mutable
working-tree copy.

The file is intentionally a small, dependency-free YAML subset:

    version: 2
    protected_paths:
      - "auth/**"
      - "**/.env"
    max_changed_files: 12

Version 1 (`denylist` / `max_files`) remains read-compatible so a policy pinned
in the settlement base cannot disappear during migration. Version 2 is the only
canonical write format. Duplicate keys, aliases, tags, flow collections, tabs,
malformed quoting, empty rules, traversal, and unknown fields fail closed.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import re
import subprocess
from pathlib import Path

GATE_FILENAME = "gate.yaml"
GATE_RELPATH = ".cvg/gate.yaml"
MAX_POLICY_BYTES = 64 * 1024
MAX_RULES = 256
MAX_PATH_BYTES = 4096
MAX_PATH_SEGMENTS = 256
MAX_CHANGED_FILES_LIMIT = 10_000


class GatePolicyError(Exception):
    """The policy or a candidate path is unsafe or ambiguous."""


class GatePolicy:
    def __init__(
        self,
        source: str | Path | None = None,
        protected_paths: list[str] | None = None,
        max_changed_files: int | None = None,
        schema_version: int | None = None,
    ) -> None:
        self.source = source
        self.protected_paths = protected_paths or []
        self.max_changed_files = max_changed_files
        self.schema_version = schema_version

    @property
    def active(self) -> bool:
        return self.source is not None

    def forbids(self, path: str) -> str | None:
        """Return the matching protected-path rule, or ``None``."""
        candidate = normalize_repo_path(path)
        # Policy self-protection is structural, not optional configuration.
        if candidate == GATE_RELPATH:
            return "<policy-self>"
        for rule in self.protected_paths:
            if _matches(candidate, rule):
                return rule
        return None

    def violations(self, paths: list[str]) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for path in paths:
            rule = self.forbids(path)
            if rule:
                found.append((path, rule))
        return found

    def exceeds_blast_radius(self, count: int) -> bool:
        return (
            self.max_changed_files is not None
            and count > self.max_changed_files
        )


def normalize_repo_path(value: str) -> str:
    """Return one canonical repository-relative POSIX path.

    Backslashes and traversal are rejected rather than reinterpreted. That
    keeps one spelling per path and prevents ``a/../auth/x`` from evading a
    policy written for ``auth/**``.
    """
    if not isinstance(value, str):
        raise GatePolicyError("path must be text")
    if not value or len(value.encode("utf-8")) > MAX_PATH_BYTES:
        raise GatePolicyError("path is empty or too long")
    if any(ch in value for ch in ("\x00", "\r", "\n", "\\")):
        raise GatePolicyError(f"path contains a forbidden character: {value!r}")
    while value.startswith("./"):
        value = value[2:]
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise GatePolicyError(f"path must be repository-relative: {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise GatePolicyError(f"path is not canonical: {value!r}")
    if len(parts) > MAX_PATH_SEGMENTS:
        raise GatePolicyError(
            f"path exceeds {MAX_PATH_SEGMENTS} segments: {value!r}"
        )
    return "/".join(parts)


def _validate_rule(rule: str) -> str:
    if not rule:
        raise GatePolicyError("protected_paths contains an empty rule")
    if rule.startswith("./") or rule.endswith("/"):
        raise GatePolicyError(
            f"protected path must be canonical (use '<dir>/**' for a tree): {rule!r}"
        )
    normalized = normalize_repo_path(rule)
    for segment in normalized.split("/"):
        if "**" in segment and segment != "**":
            raise GatePolicyError(
                f"'**' must occupy a whole path segment: {rule!r}"
            )
        if not re.fullmatch(r"[A-Za-z0-9._@+*?!-]+", segment):
            raise GatePolicyError(
                f"protected path uses unsupported glob syntax: {rule!r}"
            )
    return normalized


def _matches(path: str, rule: str) -> bool:
    """Segment-aware glob matching.

    ``*`` and ``?`` never cross ``/``. A whole ``**`` segment matches zero or
    more path segments. Matching is case-sensitive on every platform.
    """
    path_parts = path.split("/")
    rule_parts = rule.split("/")

    @functools.lru_cache(maxsize=None)
    def visit(pi: int, ri: int) -> bool:
        if ri == len(rule_parts):
            return pi == len(path_parts)
        token = rule_parts[ri]
        if token == "**":
            if visit(pi, ri + 1):
                return True
            return pi < len(path_parts) and visit(pi + 1, ri)
        return (
            pi < len(path_parts)
            and fnmatch.fnmatchcase(path_parts[pi], token)
            and visit(pi + 1, ri + 1)
        )

    return visit(0, 0)


def _strip_comment(raw: str, line_number: int) -> str:
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for char in raw:
        if quote == '"' and escaped:
            out.append(char)
            escaped = False
            continue
        if quote == '"' and char == "\\":
            out.append(char)
            escaped = True
            continue
        if quote:
            out.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            out.append(char)
        elif char == "#":
            break
        else:
            out.append(char)
    if quote or escaped:
        raise GatePolicyError(f"line {line_number}: unterminated quoted scalar")
    return "".join(out).rstrip()


def _scalar(value: str, line_number: int) -> str:
    value = value.strip()
    if not value:
        raise GatePolicyError(f"line {line_number}: empty scalar")
    if value.startswith('"') or value.endswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise GatePolicyError(
                f"line {line_number}: malformed double-quoted scalar"
            ) from exc
        if not isinstance(parsed, str):
            raise GatePolicyError(f"line {line_number}: scalar must be text")
        return parsed
    if value.startswith("'") or value.endswith("'"):
        if len(value) < 2 or not (value.startswith("'") and value.endswith("'")):
            raise GatePolicyError(
                f"line {line_number}: malformed single-quoted scalar"
            )
        return value[1:-1].replace("''", "'")
    if any(token in value for token in ("[", "]", "{", "}", "&", "!", "|", ">")):
        raise GatePolicyError(
            f"line {line_number}: YAML aliases, tags, collections, and blocks are unsupported"
        )
    return value


def parse_gate(text: str, source: str | Path | None = None) -> GatePolicy:
    """Parse and validate the complete v1 policy schema."""
    if len(text.encode("utf-8")) > MAX_POLICY_BYTES:
        raise GatePolicyError(
            f"policy exceeds {MAX_POLICY_BYTES} bytes"
        )

    seen: set[str] = set()
    protected: list[str] = []
    legacy_protected: list[str] = []
    version: str | None = None
    max_changed: int | None = None
    legacy_max: int | None = None
    current_list: str | None = None

    for line_number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise GatePolicyError(f"line {line_number}: tabs are forbidden")
        line = _strip_comment(raw, line_number)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            match = re.fullmatch(r"([a-z][a-z0-9_]*):(?:[ ]*(.*))?", stripped)
            if not match:
                raise GatePolicyError(
                    f"line {line_number}: expected a top-level key"
                )
            key, raw_value = match.group(1), match.group(2) or ""
            if key in seen:
                raise GatePolicyError(
                    f"line {line_number}: duplicate key {key!r}"
                )
            seen.add(key)
            current_list = None

            if key == "version":
                version = _scalar(raw_value, line_number)
            elif key in ("protected_paths", "denylist"):
                if raw_value:
                    raise GatePolicyError(
                        f"line {line_number}: {key} must be a block list"
                    )
                current_list = key
            elif key in ("max_changed_files", "max_files"):
                value = _scalar(raw_value, line_number)
                if not re.fullmatch(r"[0-9]+", value):
                    raise GatePolicyError(
                        f"line {line_number}: {key} must be a positive integer"
                    )
                parsed_max = int(value)
                if not 1 <= parsed_max <= MAX_CHANGED_FILES_LIMIT:
                    raise GatePolicyError(
                        f"line {line_number}: {key} must be between 1 and "
                        f"{MAX_CHANGED_FILES_LIMIT}"
                    )
                if key == "max_changed_files":
                    max_changed = parsed_max
                else:
                    legacy_max = parsed_max
            else:
                raise GatePolicyError(
                    f"line {line_number}: unknown gate key {key!r}"
                )
            continue

        if indent == 2 and current_list in ("protected_paths", "denylist"):
            if not stripped.startswith("- "):
                raise GatePolicyError(
                    f"line {line_number}: expected '- <protected path>'"
                )
            target = protected if current_list == "protected_paths" else legacy_protected
            target.append(_validate_rule(_scalar(stripped[2:], line_number)))
            if len(target) > MAX_RULES:
                raise GatePolicyError(
                    f"{current_list} exceeds {MAX_RULES} rules"
                )
            continue

        raise GatePolicyError(
            f"line {line_number}: invalid indentation or list placement"
        )

    if version is None:
        raise GatePolicyError("missing required key 'version'")
    if version not in ("1", "2"):
        raise GatePolicyError(f"unsupported gate version: {version!r}")
    if version == "1":
        unexpected = seen.intersection({"protected_paths", "max_changed_files"})
        if unexpected:
            raise GatePolicyError(
                f"version 1 may not use version 2 keys: {sorted(unexpected)!r}"
            )
        if "denylist" not in seen or not legacy_protected:
            raise GatePolicyError("version 1 denylist must contain at least one rule")
        protected = legacy_protected
        max_changed = legacy_max
    else:
        unexpected = seen.intersection({"denylist", "max_files"})
        if unexpected:
            raise GatePolicyError(
                f"version 2 may not use legacy keys: {sorted(unexpected)!r}"
            )
        if "protected_paths" not in seen or not protected:
            raise GatePolicyError(
                "version 2 protected_paths must contain at least one rule"
            )
    if len(set(protected)) != len(protected):
        raise GatePolicyError("protected path list contains a duplicate rule")

    return GatePolicy(
        source=source,
        protected_paths=protected,
        max_changed_files=max_changed,
        schema_version=int(version),
    )


def load_gate(repo_root: Path) -> GatePolicy:
    """Load the one allowed policy: ``<git-root>/.cvg/gate.yaml``."""
    candidate = Path(repo_root).resolve() / GATE_RELPATH
    if not candidate.exists():
        return GatePolicy()
    if not candidate.is_file() or candidate.is_symlink():
        raise GatePolicyError(
            f"{candidate}: policy must be a regular, non-symlink file"
        )
    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GatePolicyError(f"{candidate}: cannot read UTF-8 policy: {exc}") from exc
    try:
        return parse_gate(text, source=candidate)
    except GatePolicyError as exc:
        raise GatePolicyError(f"{candidate}: {exc}") from exc


def load_gate_from_git(repo_root: Path, ref: str) -> GatePolicy:
    """Load policy bytes from a trusted commit, never the mutable worktree."""
    root = Path(repo_root).resolve()
    resolved = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", f"{ref}^{{commit}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if resolved.returncode != 0:
        raise GatePolicyError(
            resolved.stderr.strip() or f"cannot resolve trusted gate base {ref!r}"
        )
    sha = resolved.stdout.strip()
    exists = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{sha}:{GATE_RELPATH}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if exists.returncode != 0:
        return GatePolicy()
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{sha}:{GATE_RELPATH}"],
        capture_output=True,
        check=False,
    )
    if shown.returncode != 0:
        raise GatePolicyError(
            shown.stderr.decode("utf-8", errors="replace").strip()
            or f"cannot read {GATE_RELPATH} from {sha}"
        )
    try:
        text = shown.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GatePolicyError(
            f"{sha}:{GATE_RELPATH}: policy is not valid UTF-8"
        ) from exc
    try:
        return parse_gate(
            text,
            source=f"{sha}:{GATE_RELPATH}",
        )
    except GatePolicyError as exc:
        raise GatePolicyError(f"{sha}:{GATE_RELPATH}: {exc}") from exc


def find_git_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(Path(start).resolve()), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GatePolicyError(
            proc.stderr.strip() or f"not inside a Git repository: {start}"
        )
    return Path(proc.stdout.strip()).resolve()
