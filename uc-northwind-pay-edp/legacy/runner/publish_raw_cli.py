from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
):
    sys.path.insert(0, str(module_directory))

from config import (  # noqa: E402
    RuntimeConfiguration,
    RuntimeConfigurationError,
)
from raw_publisher import RawPublicationError, publish_bundle  # noqa: E402
from sftp_client import SftpBoundaryError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish one generated raw bundle through SFTP.",
    )
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        configuration = RuntimeConfiguration.load()
        published = publish_bundle(
            args.bundle.resolve(),
            configuration=configuration,
        )
    except (
        RawPublicationError,
        RuntimeConfigurationError,
        SftpBoundaryError,
    ) as exc:
        print(f"raw publication failed: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "batch_id": published.batch_id,
                "sha256": published.sha256,
                "status": "published",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
