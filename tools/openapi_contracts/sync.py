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

def verify_contract(contract: Contract) -> None:
    """Verify that a local contract exists and matches its configured digest.

    Args:
        contract: Contract whose local artifact is verified.

    Raises:
        ContractSyncError: If the artifact is missing or has an invalid checksum.
    """
    if not contract.output.is_file():
        raise ContractSyncError(
            f"Contract '{contract.name}' not found: {contract.output}"
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
    if len(contract.sha256) != 64 or any(
        c not in "0123456789abcdef" for c in contract.sha256
    ):
        raise ContractSyncError(f"Invalid SHA-256 for '{contract.name}'")

    if dry_run:
        print(f"{contract.name}: {contract.url} -> {contract.output}")
        return

    contract.output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        contract.url,
        headers={"Accept": "application/octet-stream",
                 "User-Agent": "openapi-contract-toolkit/1"},
    )
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=contract.output.parent,
            prefix=f".{contract.output.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    while chunk := response.read(1024 * 1024):
                        tmp.write(chunk)
            except urllib.error.HTTPError as e:
                raise ContractSyncError(
                    f"HTTP {e.code} downloading '{contract.name}'"
                ) from e
            except urllib.error.URLError as e:
                raise ContractSyncError(
                    f"Download failed for '{contract.name}': {e.reason}"
                ) from e

        actual = sha256_file(tmp_path)
        if actual != contract.sha256:
            raise ContractSyncError(
                f"SHA-256 mismatch for '{contract.name}': "
                f"expected {contract.sha256}, got {actual}"
            )
        tmp_path.replace(contract.output)
        tmp_path = None
        print(f"{contract.name}: synchronized {contract.version} -> {contract.output}")
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)
