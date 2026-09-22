import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.openapi_contracts.config import Configuration, Contract, Generator
from tools.openapi_contracts.generate import build_command, generate
from tools.openapi_contracts.sync import ContractSyncError


class GenerateTest(unittest.TestCase):
    def test_when_contract_is_valid_expect_generator_command_executed(self):
        content = b"openapi: 3.0.0\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog.yaml", hashlib.sha256(content).hexdigest(), root / "catalog.yaml")
            contract.output.write_bytes(content)
            definition = Generator("rest", "client", "catalog-client", "catalog", "python", root / "generated", "catalog_client", {"library": "urllib3"})
            configuration = Configuration(root, {"catalog": contract}, {("rest", "client", "catalog-client"): definition})

            with patch.dict(os.environ, {"OPENAPI_GENERATOR_CMD": "generator"}), patch("tools.openapi_contracts.generate.subprocess.run") as run:
                generate(configuration, definition)

            self.assertEqual(run.call_args.args[0][0], "generator")
            self.assertIn(
                "packageName=catalog_client",
                run.call_args.args[0][run.call_args.args[0].index("--additional-properties") + 1],
            )

    def test_when_contract_is_missing_expect_no_generator_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog.yaml", "a" * 64, root / "catalog.yaml")
            definition = Generator("rest", "client", "catalog-client", "catalog", "python", root / "generated", None, {})
            configuration = Configuration(root, {"catalog": contract}, {})

            with self.assertRaisesRegex(ContractSyncError, "Run contract-sync first"):
                build_command(configuration, definition)

    def test_when_contract_is_corrupt_expect_no_generator_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = Contract("catalog", "1.0.0", "org/contracts", "v{version}", "catalog.yaml", "a" * 64, root / "catalog.yaml")
            contract.output.write_bytes(b"corrupt")
            definition = Generator("rest", "client", "catalog-client", "catalog", "python", root / "generated", None, {})
            configuration = Configuration(root, {"catalog": contract}, {})

            with self.assertRaisesRegex(ContractSyncError, "SHA-256 mismatch"):
                build_command(configuration, definition)
