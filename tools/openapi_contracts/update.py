"""Explicit OpenAPI contract version updates and TOML persistence."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import tomlkit
from tomlkit.exceptions import TOMLKitError

from .config import Configuration, Contract
from .sync import download_contract, sha256_file


class ContractUpdateError(RuntimeError):
    """Raised when a contract version update cannot complete safely."""


def require_contract(configuration: Configuration, name: str) -> Contract:
    """Return a configured contract by name.

    Args:
        configuration: Resolved toolkit configuration.
        name: Contract identifier.

    Returns:
        The configured contract.

    Raises:
        ContractUpdateError: If no contract is configured with ``name``.
    """
    try:
        return configuration.contracts[name]
    except KeyError as error:
        raise ContractUpdateError(f"Unknown contract '{name}'") from error


def update_contract_config(
    pyproject: Path,
    contract_name: str,
    version: str,
    sha256: str,
) -> None:
    """Atomically update a contract version and checksum in a TOML document.

    Args:
        pyproject: Path to the project configuration file.
        contract_name: Contract table to update.
        version: New explicitly selected contract version.
        sha256: SHA-256 checksum calculated from the downloaded artifact.

    Raises:
        ContractUpdateError: If the contract table cannot be updated or persisted.
    """
    try:
        document = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
        contract_table = document["tool"]["openapi-contracts"]["contracts"][
            contract_name
        ]
        contract_table["version"] = version
        contract_table["sha256"] = sha256
    except (KeyError, TOMLKitError) as error:
        raise ContractUpdateError(
            f"Unable to update contract '{contract_name}' in {pyproject}"
        ) from error

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=pyproject.parent,
            prefix=f".{pyproject.name}.",
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(tomlkit.dumps(document))
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(pyproject)
        temporary_path = None
    except OSError as error:
        raise ContractUpdateError(f"Unable to write {pyproject}") from error
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)


def update_contract(
    configuration: Configuration,
    pyproject: str | Path,
    contract_name: str,
    version: str,
    dry_run: bool = False,
) -> None:
    """Download and pin a new explicit version of a configured contract.

    Args:
        configuration: Resolved toolkit configuration.
        pyproject: Path to the project configuration file to update.
        contract_name: Name of the configured contract to update.
        version: Explicit version to download and pin.
        dry_run: Whether to print the planned update without modifying files.

    Raises:
        ContractSyncError: If the release artifact cannot be downloaded.
        ContractUpdateError: If the requested update is invalid or cannot be persisted.
    """
    if not version.strip():
        raise ContractUpdateError("Version must not be empty")

    contract = require_contract(configuration, contract_name)
    candidate = contract.with_version(version)
    if dry_run:
        print(
            f"{contract.name}: {contract.version} -> {candidate.version}; "
            f"{candidate.url} -> {candidate.output}"
        )
        return

    temporary_path: Path | None = None
    try:
        temporary_path = download_contract(candidate)
        actual_sha256 = sha256_file(temporary_path)
        update_contract_config(
            Path(pyproject).resolve(),
            contract.name,
            candidate.version,
            actual_sha256,
        )
        temporary_path.replace(contract.output)
        temporary_path = None
        print(f"{contract.name}: updated {candidate.version} -> {contract.output}")
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
