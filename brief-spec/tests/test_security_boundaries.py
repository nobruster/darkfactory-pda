from __future__ import annotations

import hashlib
import json
import socket
import stat
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from briefspec import renderers, verification
from briefspec.delivery import canonical_json_bytes, new_delivery
from briefspec.models import VerificationLevel


def _delivery_with_url(locator: str = "https://example.com/evidence") -> dict[str, object]:
    return new_delivery(
        {
            "schema_version": "1.0",
            "kind": "outcome-brief",
            "status": "DONE",
            "outcome": "Security boundaries are under test.",
            "human_action": None,
            "proof": [
                {
                    "kind": "url",
                    "label": f"declared URL {locator}",
                    "locator": locator,
                    "basis": "direct",
                    "result": "pass",
                }
            ],
            "gaps": [],
            "next": [],
            "open": [],
        },
        harness="test",
        created_at="2026-08-13T12:00:00Z",
    )


def test_resolved_verification_performs_zero_requests_without_consent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(_delivery_with_url()))

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network helper must not be called")

    monkeypatch.setattr(verification, "_network_request", forbidden)
    result = verification.verify_target(
        source,
        level=VerificationLevel.RESOLVED,
        workspace=tmp_path,
    )
    assert result["network_consent"] is False
    assert result["status"] == "WARN"
    assert "network consent not granted" in result["checks"][-1]["detail"]


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "::ffff:127.0.0.1",
    ],
)
def test_network_policy_rejects_every_non_global_address_form(
    address: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(
        verification.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(family, socket.SOCK_STREAM, 6, "", (address, 443))],
    )
    with pytest.raises(ValueError, match="not globally routable"):
        verification._public_addresses("2130706433", 443)


def test_mixed_public_private_dns_answer_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        verification.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(ValueError, match="not globally routable"):
        verification._public_addresses("rebind.example", 443)


class _FakeSocket:
    def __init__(self) -> None:
        self.requests: list[bytes] = []
        self.closed = False

    def sendall(self, content: bytes) -> None:
        self.requests.append(content)

    def close(self) -> None:
        self.closed = True


class _FakeResponse:
    def __init__(
        self,
        status: int,
        *,
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self.headers = headers or []
        self.body = body

    def begin(self) -> None:
        return None

    def getheaders(self) -> list[tuple[str, str]]:
        return self.headers

    def getheader(self, name: str) -> str | None:
        return next((value for key, value in self.headers if key.lower() == name.lower()), None)

    def read(self, _limit: int) -> bytes:
        return self.body


def test_consented_network_request_pins_public_address_follows_redirect_and_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sockets: list[_FakeSocket] = []
    responses = [
        _FakeResponse(302, headers=[("Location", "/final")]),
        _FakeResponse(200, body=b"verified body"),
    ]
    monkeypatch.setattr(verification, "_public_addresses", lambda *_args: ["93.184.216.34"])
    monkeypatch.setattr(
        verification.socket,
        "create_connection",
        lambda *_args, **_kwargs: sockets.append(_FakeSocket()) or sockets[-1],
    )
    monkeypatch.setattr(
        verification.http.client,
        "HTTPResponse",
        lambda _connection: responses.pop(0),
    )
    expected = hashlib.sha256(b"verified body").hexdigest()
    status, final_url, actual = verification._network_request(
        "http://example.com:8080/start",
        expected_sha256=expected,
        request_budget=[0],
    )
    assert (status, final_url, actual) == (200, "http://example.com:8080/final", expected)
    assert all(sock.closed for sock in sockets)
    assert sockets[0].requests[0].startswith(b"GET /start HTTP/1.1")
    assert b"Host: example.com:8080" in sockets[0].requests[0]


@pytest.mark.parametrize(
    ("locator", "budget", "message"),
    [
        ("ftp://example.com/file", [0], "absolute HTTP"),
        ("http://user:pass@example.com/", [0], "credentials"),
        ("http://example.com/", [verification.MAX_NETWORK_REQUESTS], "request limit"),
    ],
)
def test_network_request_rejects_invalid_input_before_connection(
    locator: str,
    budget: list[int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        verification._network_request(locator, expected_sha256=None, request_budget=budget)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_FakeResponse(302), "omitted Location"),
        (_FakeResponse(503), "HTTP status 503"),
        (
            _FakeResponse(
                200,
                headers=[("X-Large", "x" * verification.MAX_RESPONSE_HEADERS_BYTES)],
            ),
            "headers exceed",
        ),
    ],
)
def test_network_response_limits_and_status_fail_closed(
    response: _FakeResponse,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verification, "_public_addresses", lambda *_args: ["93.184.216.34"])
    monkeypatch.setattr(
        verification.socket,
        "create_connection",
        lambda *_args, **_kwargs: _FakeSocket(),
    )
    monkeypatch.setattr(
        verification.http.client,
        "HTTPResponse",
        lambda _connection: response,
    )
    with pytest.raises(ValueError, match=message):
        verification._network_request(
            "http://example.com/",
            expected_sha256=None,
            request_budget=[0],
        )


def _write_manifest_bundle(path: Path, members: list[tuple[zipfile.ZipInfo | str, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)


@pytest.mark.parametrize("case", ["traversal", "duplicate", "symlink", "members", "ratio"])
def test_archive_preflight_rejects_unsafe_bundles(case: str, tmp_path: Path) -> None:
    bundle = tmp_path / f"{case}.zip"
    manifest = json.dumps({"files": []}).encode()
    if case == "traversal":
        members: list[tuple[zipfile.ZipInfo | str, bytes]] = [
            ("../escape", b"x"),
            ("manifest.json", manifest),
        ]
    elif case == "duplicate":
        members = [("manifest.json", manifest), ("manifest.json", manifest)]
    elif case == "symlink":
        link = zipfile.ZipInfo("link")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        members = [(link, b"target"), ("manifest.json", manifest)]
    elif case == "members":
        members = [(f"member-{index}", b"x") for index in range(128)]
        members.append(("manifest.json", manifest))
    else:
        members = [("compressed", b"0" * (1024 * 1024)), ("manifest.json", manifest)]
    if case == "duplicate":
        with pytest.warns(UserWarning, match="Duplicate name"):
            _write_manifest_bundle(bundle, members)
    else:
        _write_manifest_bundle(bundle, members)
    result = verification.verify_target(bundle, level=VerificationLevel.RENDERED)
    assert result["status"] == "FAIL"
    assert result["checks"][0]["name"] == "bundle manifest"


def test_large_local_artifact_fails_before_hashing(tmp_path: Path) -> None:
    artifact = tmp_path / "large.bin"
    with artifact.open("wb") as handle:
        handle.truncate(verification.MAX_LOCAL_ARTIFACT_BYTES + 1)
    delivery = _delivery_with_url()
    delivery["brief"]["proof"] = [  # type: ignore[index]
        {
            "kind": "file",
            "label": "large file `large.bin`",
            "locator": "large.bin",
            "basis": "direct",
            "result": "pass",
        }
    ]
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(delivery))
    result = verification.verify_target(
        source,
        level=VerificationLevel.RESOLVED,
        workspace=tmp_path,
    )
    assert result["status"] == "FAIL"
    assert "verification limit" in result["checks"][-1]["detail"]


def test_core_verification_never_loads_renderer_entry_points(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "untrusted.pdf"
    artifact.write_bytes(b"%PDF-1.4\n")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("plugin discovery must not run")

    monkeypatch.setattr(verification, "available_renderers", forbidden)
    result = verification.verify_target(artifact, level=VerificationLevel.RENDERED)
    assert result["status"] == "FAIL"
    assert "disabled" in result["checks"][0]["detail"]


def test_official_renderer_filter_does_not_load_unrecognized_entry_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = False

    def hostile_load() -> object:
        nonlocal loaded
        loaded = True
        raise AssertionError("hostile entry point loaded")

    entry_point = SimpleNamespace(name="evil", load=hostile_load)
    entry_points = SimpleNamespace(select=lambda **_kwargs: [entry_point])
    monkeypatch.setattr(renderers.metadata, "entry_points", lambda: entry_points)
    assert renderers.available_renderers({"pdf"}, official_only=True) == {}
    assert loaded is False
