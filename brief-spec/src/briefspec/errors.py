from __future__ import annotations


class BriefSpecError(Exception):
    """Base error for expected Brief-Spec failures."""


class ContractError(BriefSpecError):
    """A brief does not satisfy its presentation contract."""


class InstallConflict(BriefSpecError):
    """Installation would overwrite data not owned by Brief-Spec."""


class HostUnavailable(BriefSpecError):
    """A requested host executable or integration surface is unavailable."""
