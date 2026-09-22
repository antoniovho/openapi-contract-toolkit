from pathlib import Path
import sys
import unittest
from unittest.mock import call, patch

from tools.openapi_contracts.cli import contract_sync_main, contract_update_main
from tools.openapi_contracts.config import Configuration, Contract


class CliTest(unittest.TestCase):
    def setUp(self):
        root = Path("/project")
        self.contracts = {
            name: Contract(name, "1.0.0", "org/contracts", "v{version}", f"{name}.yaml", "a" * 64, root / f"{name}.yaml")
            for name in ("catalog", "orders")
        }
        self.configuration = Configuration(root, self.contracts, {})

    def test_when_no_contract_is_selected_expect_all_contracts_synchronized(self):
        with patch("tools.openapi_contracts.cli.load_config", return_value=self.configuration), patch("tools.openapi_contracts.cli.sync_contract") as sync, patch.object(sys, "argv", ["contract-sync"]):
            contract_sync_main()

        self.assertEqual(sync.call_args_list, [call(self.contracts["catalog"], False), call(self.contracts["orders"], False)])

    def test_when_contract_is_selected_expect_only_selected_contract_synchronized(self):
        with patch("tools.openapi_contracts.cli.load_config", return_value=self.configuration), patch("tools.openapi_contracts.cli.sync_contract") as sync, patch.object(sys, "argv", ["contract-sync", "orders", "--dry-run"]):
            contract_sync_main()

        sync.assert_called_once_with(self.contracts["orders"], True)

    def test_when_update_arguments_are_valid_expect_update_service_called(self):
        with patch("tools.openapi_contracts.cli.load_config", return_value=self.configuration), patch("tools.openapi_contracts.cli.update_contract") as update, patch.object(sys, "argv", ["contract-update", "catalog", "--version", "1.1.0", "--dry-run"]):
            contract_update_main()

        update.assert_called_once_with(self.configuration, "pyproject.toml", "catalog", "1.1.0", True)
