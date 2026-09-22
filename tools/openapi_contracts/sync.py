"""Contract downloading, checksum validation, and local storage."""

from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
from .config import Contract

class ContractSyncError(RuntimeError):
    """Raised when synchronizing or validating a contract fails."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file as a hexadecimal string.

    Args:
        path: Path to the file to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(value: str, contract_name: str) -> None:
    """Ensure that a checksum is a lowercase hexadecimal SHA-256 value.

    Args:
        value: Checksum value to validate.
        contract_name: Contract name used in an error message.

    Raises:
        ContractSyncError: If the checksum is not a valid SHA-256 value.
    """
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContractSyncError(f"Invalid SHA-256 for '{contract_name}'")


def build_request(contract: Contract) -> urllib.request.Request:
    """Build an authenticated HTTP request for a contract artifact.

    Args:
        contract: Contract whose artifact will be requested.

    Returns:
        Request configured for the artifact URL.
    """
    request = urllib.request.Request(
        contract.url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "openapi-contract-toolkit/1",
        },
    )
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    return request


def download_contract(contract: Contract) -> Path:
    """Download a contract artifact to a temporary file beside its destination.

    Args:
        contract: Contract whose artifact will be downloaded.

    Returns:
        Path to the downloaded temporary file. The caller owns its cleanup.

    Raises:
        ContractSyncError: If the artifact cannot be downloaded.
    """
    contract.output.parent.mkdir(parents=True, exist_ok=True)
    request = build_request(contract)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=contract.output.parent,
            prefix=f".{contract.output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    while chunk := response.read(1024 * 1024):
                        temporary_file.write(chunk)
            except urllib.error.HTTPError as error:
                raise ContractSyncError(
                    f"HTTP {error.code} downloading '{contract.name}'"
                ) from error
            except urllib.error.URLError as error:
                raise ContractSyncError(
                    f"Download failed for '{contract.name}': {error.reason}"
                ) from error
        return temporary_path
    except BaseException:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
        raise


def verify_contract(contract: Contract) -> None:
    """Verify that a local contract exists and matches its configured digest.

    Args:
        contract: Contract whose local artifact is verified.

    Raises:
        ContractSyncError: If the artifact is missing or has an invalid checksum.
    """
    if not contract.output.is_file():
        raise ContractSyncError(
            f"Contract '{contract.name}' not found: {contract.output}. "
            "Run contract-sync first."
        )
    actual = sha256_file(contract.output)
    if actual != contract.sha256:
        raise ContractSyncError(
            f"SHA-256 mismatch for '{contract.name}': "
            f"expected {contract.sha256}, got {actual}"
        )

def sync_contract(contract: Contract, dry_run: bool = False) -> None:
    """Download, validate, and atomically store a configured contract artifact.

    Args:
        contract: Contract definition identifying the artifact to synchronize.
        dry_run: Whether to print the planned synchronization without downloading.

    Raises:
        ContractSyncError: If the configured checksum is invalid or download fails.
    """
    validate_sha256(contract.sha256, contract.name)

    if dry_run:
        print(f"{contract.name}: {contract.url} -> {contract.output}")
        return

    temporary_path: Path | None = None
    try:
        temporary_path = download_contract(contract)
        actual = sha256_file(temporary_path)
        if actual != contract.sha256:
            raise ContractSyncError(
                f"SHA-256 mismatch for '{contract.name}': "
                f"expected {contract.sha256}, got {actual}"
            )
        temporary_path.replace(contract.output)
        temporary_path = None
        print(f"{contract.name}: synchronized {contract.version} -> {contract.output}")
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
