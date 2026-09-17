from __future__ import annotations

import errno
import json
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import paramiko

from config import RuntimeConfiguration, SftpRole


class SftpBoundaryError(Exception):
    """An SFTP boundary operation could not be completed safely."""


@contextmanager
def connect_sftp(
    configuration: RuntimeConfiguration,
    role: SftpRole,
) -> Iterator[paramiko.SFTPClient]:
    if not configuration.known_hosts.is_file():
        raise SftpBoundaryError(
            "Verified SFTP host keys are unavailable; run make deploy"
        )

    client = paramiko.SSHClient()
    client.load_host_keys(str(configuration.known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            hostname=configuration.sftp_host,
            port=configuration.sftp_port,
            username=role.username,
            password=role.password,
            allow_agent=False,
            look_for_keys=False,
            timeout=10,
            auth_timeout=10,
            banner_timeout=10,
        )
        with client.open_sftp() as sftp:
            yield sftp
    except (OSError, paramiko.SSHException) as exc:
        raise SftpBoundaryError(
            f"Verified SFTP operation failed for role: {role.username}"
        ) from exc
    finally:
        client.close()


def exists(sftp: paramiko.SFTPClient, path: str) -> bool:
    try:
        sftp.stat(path)
        return True
    except OSError as exc:
        if exc.errno in {errno.ENOENT, 2}:
            return False
        raise


def mkdir_exact(sftp: paramiko.SFTPClient, path: str) -> None:
    if exists(sftp, path):
        raise SftpBoundaryError(
            f"Immutable SFTP batch path already exists: {PurePosixPath(path).name}"
        )
    try:
        sftp.mkdir(path, mode=0o770)
        sftp.chmod(path, 0o770)
    except OSError as exc:
        raise SftpBoundaryError(
            f"Cannot create immutable SFTP batch path: {PurePosixPath(path).name}"
        ) from exc


def upload_manifest_last(
    sftp: paramiko.SFTPClient,
    remote_directory: str,
    artifacts: Iterable[tuple[str, Path]],
    *,
    manifest_name: str,
) -> None:
    ordered = list(artifacts)
    if [name for name, _ in ordered].count(manifest_name) != 1:
        raise SftpBoundaryError("Publication must contain one readiness manifest")

    publication_paths = [
        f"{remote_directory}/{name}{suffix}"
        for name, _ in ordered
        for suffix in (".part", "")
    ]
    try:
        for name, local_path in ordered:
            remote_part = f"{remote_directory}/{name}.part"
            sftp.put(str(local_path), remote_part, confirm=True)
        for name, _ in ordered:
            if name != manifest_name:
                sftp.posix_rename(
                    f"{remote_directory}/{name}.part",
                    f"{remote_directory}/{name}",
                )
        sftp.posix_rename(
            f"{remote_directory}/{manifest_name}.part",
            f"{remote_directory}/{manifest_name}",
        )
    except OSError as exc:
        for path in publication_paths:
            try:
                sftp.remove(path)
            except OSError:
                pass
        raise SftpBoundaryError(
            f"Manifest-last publication failed: {PurePosixPath(remote_directory).name}"
        ) from exc


def move_batch(
    sftp: paramiko.SFTPClient,
    batch_id: str,
    *,
    source_zone: str,
    target_zone: str,
) -> None:
    source = f"{source_zone}/{batch_id}"
    target = f"{target_zone}/{batch_id}"
    if exists(sftp, target):
        raise SftpBoundaryError(
            f"Target SFTP batch path already exists: {batch_id}"
        )
    try:
        sftp.posix_rename(source, target)
    except OSError as exc:
        raise SftpBoundaryError(
            f"Cannot move SFTP batch between zones: {batch_id}"
        ) from exc


def write_safe_json(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    value: object,
) -> None:
    content = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")
    if exists(sftp, remote_path):
        raise SftpBoundaryError("Safe SFTP diagnostic metadata already exists")
    temporary_path = f"{remote_path}.part"
    if exists(sftp, temporary_path):
        raise SftpBoundaryError(
            "Safe SFTP diagnostic metadata has a stale temporary artifact"
        )
    try:
        with sftp.file(temporary_path, "w") as stream:
            stream.write(content)
            stream.flush()
        if sftp.stat(temporary_path).st_size != len(content):
            raise OSError("diagnostic metadata size mismatch")
        sftp.posix_rename(temporary_path, remote_path)
    except OSError as exc:
        try:
            sftp.remove(temporary_path)
        except OSError:
            pass
        raise SftpBoundaryError("Cannot write safe SFTP diagnostic metadata") from exc
