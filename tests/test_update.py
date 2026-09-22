import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.openapi_contracts.config import load_config
from tools.openapi_contracts.sync import ContractSyncError
from tools.openapi_contracts.update import ContractUpdateError, update_contract


CONFIG = """# preserved comment
[tool.openapi-contracts.contracts.catalog]
version = "1.0.0"
repository = "org/contracts"
tag = "catalog-v{version}"
artifact = "catalog-{version}.yaml"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
output = "contracts/catalog.yaml"

[unrelated]
setting = "keep"
"""


class UpdateTest(unittest.TestCase):
    def test_when_download_succeeds_expect_version_checksum_and_artifact_updated(self):
        content = b"openapi: 3.0.0\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pyproject = root / "pyproject.toml"
            pyproject.write_text(CONFIG)
            (root / "contracts").mkdir()
            downloaded = root / "downloaded.yaml"
            downloaded.write_bytes(content)
            configuration = load_config(pyproject)

            with patch("tools.openapi_contracts.update.download_contract", return_value=downloaded) as download:
                update_contract(configuration, pyproject, "catalog", "1.1.0")

            updated = pyproject.read_text()
            self.assertIn("# preserved comment", updated)
            self.assertIn('version = "1.1.0"', updated)
            self.assertIn(f'sha256 = "{hashlib.sha256(content).hexdigest()}"', updated)
            self.assertIn('setting = "keep"', updated)
            self.assertEqual((root / "contracts/catalog.yaml").read_bytes(), content)
            self.assertIn("catalog-v1.1.0", download.call_args.args[0].url)

    def test_when_download_fails_expect_configuration_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(CONFIG)
            configuration = load_config(pyproject)
            before = pyproject.read_text()

            with patch("tools.openapi_contracts.update.download_contract", side_effect=ContractSyncError("not found")):
                with self.assertRaisesRegex(ContractSyncError, "not found"):
                    update_contract(configuration, pyproject, "catalog", "1.1.0")

            self.assertEqual(pyproject.read_text(), before)

    def test_when_contract_is_unknown_expect_update_error(self):
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(CONFIG)
            configuration = load_config(pyproject)

            with self.assertRaisesRegex(ContractUpdateError, "Unknown contract"):
                update_contract(configuration, pyproject, "missing", "1.1.0")

    def test_when_dry_run_expect_no_download_or_configuration_change(self):
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(CONFIG)
            configuration = load_config(pyproject)
            before = pyproject.read_text()

            with patch("tools.openapi_contracts.update.download_contract") as download:
                update_contract(configuration, pyproject, "catalog", "1.1.0", dry_run=True)

            download.assert_not_called()
            self.assertEqual(pyproject.read_text(), before)
