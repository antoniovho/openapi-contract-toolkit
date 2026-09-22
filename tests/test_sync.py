import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from tools.openapi_contracts.config import Contract
from tools.openapi_contracts.sync import ContractSyncError, sync_contract, verify_contract


class Response:
    def __init__(self, content: bytes):
        self._content = BytesIO(content)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self._content.read(size)


class SyncTest(unittest.TestCase):
    def test_when_download_checksum_matches_expect_contract_replaced(self):
        content = b"openapi: 3.0.0\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contracts" / "catalog.yaml"
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog-{version}.yaml", hashlib.sha256(content).hexdigest(), output)

            with patch("tools.openapi_contracts.sync.urllib.request.urlopen", return_value=Response(content)):
                sync_contract(contract)

            self.assertEqual(output.read_bytes(), content)

    def test_when_download_checksum_mismatches_expect_existing_contract_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.yaml"
            output.write_bytes(b"existing")
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog-{version}.yaml", "a" * 64, output)

            with patch("tools.openapi_contracts.sync.urllib.request.urlopen", return_value=Response(b"new")):
                with self.assertRaisesRegex(ContractSyncError, "SHA-256 mismatch"):
                    sync_contract(contract)

            self.assertEqual(output.read_bytes(), b"existing")

    def test_when_local_contract_is_missing_expect_sync_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing.yaml"
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog-{version}.yaml", "a" * 64, output)

            with self.assertRaisesRegex(ContractSyncError, "Run contract-sync first"):
                verify_contract(contract)

    def test_when_download_fails_expect_sync_error_and_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.yaml"
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog-{version}.yaml", "a" * 64, output)

            with patch("tools.openapi_contracts.sync.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
                with self.assertRaisesRegex(ContractSyncError, "Download failed"):
                    sync_contract(contract)

            self.assertFalse(output.exists())
