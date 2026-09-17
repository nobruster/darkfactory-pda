from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import RuntimeConfiguration, RuntimeConfigurationError


def main() -> int:
    try:
        configuration = RuntimeConfiguration.load()
        result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "sftp",
                "cat",
                "/etc/ssh/ssh_host_ed25519_key.pub",
                "/etc/ssh/ssh_host_ecdsa_key.pub",
                "/etc/ssh/ssh_host_rsa_key.pub",
            ],
            cwd=configuration.root,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeConfigurationError(
                "Cannot read the local SFTP public host key"
            )
        keys: list[str] = []
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) < 2 or not fields[0].startswith(("ssh-", "ecdsa-")):
                raise RuntimeConfigurationError(
                    "Local SFTP host key has an unexpected format"
                )
            keys.append(f"{fields[0]} {fields[1]}")
        if not keys:
            raise RuntimeConfigurationError(
                "Local SFTP server exposed no public host keys"
            )
        known_hosts = "".join(
            f"sftp {key}\n"
            f"[{configuration.sftp_host}]:{configuration.sftp_port} {key}\n"
            for key in keys
        ).encode("ascii")

        runtime_root = configuration.root / ".runtime"
        runtime_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = runtime_root / ".known_hosts.part"
        with temporary.open("wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(known_hosts)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(configuration.known_hosts)
    except (OSError, RuntimeConfigurationError) as exc:
        print(f"runtime bootstrap failed: {exc}", file=sys.stderr)
        return 2

    print("verified SFTP host key captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
