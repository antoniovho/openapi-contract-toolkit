from pathlib import Path
import tempfile
import unittest
from tools.openapi_contracts.config import ConfigError, load_config

class ConfigTest(unittest.TestCase):
    def test_multiple_contracts(self):
        toml = """
[tool.openapi-contracts.contracts.a]
version = "1.2.3"
repository = "org/contracts"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
output = "contracts/a.yml"

[tool.openapi-contracts.contracts.b]
version = "2.0.0"
repository = "org/contracts"
artifact = "custom-{version}.yaml"
tag = "release-{version}"
sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
output = "contracts/b.yml"

[tool.openapi-contracts.generators.rest.server.api-rest]
contract = "a"
generator = "python-fastapi"
output = "generated/server"
package-name = "example_api"

[tool.openapi-contracts.generators.rest.client.client-api]
contract = "b"
generator = "python"
output = "generated/client"
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pyproject.toml"
            p.write_text(toml)
            cfg = load_config(p)
            self.assertEqual(cfg.contracts["a"].tag, "a-api-v1.2.3")
            self.assertEqual(cfg.contracts["b"].artifact, "custom-2.0.0.yaml")
            self.assertEqual(
                cfg.generators[("rest", "server", "api-rest")].contract, "a"
            )
            self.assertEqual(
                cfg.generators[("rest", "client", "client-api")].contract, "b"
            )

    def test_when_contract_has_explicit_url_expect_rendered_release_metadata(self):
        toml = """
[tool.openapi-contracts.contracts.catalog]
version = "1.2.3"
repository = "org/contracts"
tag = "release-{version}"
artifact = "catalog-{version}.yaml"
url = "https://example.test/{tag}/{artifact}"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
output = "contracts/catalog.yaml"
"""
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(toml)

            contract = load_config(pyproject).contracts["catalog"]

            self.assertEqual(contract.tag, "release-1.2.3")
            self.assertEqual(contract.artifact, "catalog-1.2.3.yaml")
            self.assertEqual(contract.url, "https://example.test/release-1.2.3/catalog-1.2.3.yaml")
            self.assertEqual(contract.output, Path(directory) / "contracts/catalog.yaml")
            self.assertEqual(contract.with_version("2.0.0").tag, "release-2.0.0")

    def test_when_generator_references_missing_contract_expect_config_error(self):
        toml = """
[tool.openapi-contracts.contracts.catalog]
version = "1.2.3"
repository = "org/contracts"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
output = "contracts/catalog.yaml"

[tool.openapi-contracts.generators.rest.client.catalog]
contract = "missing"
generator = "python"
output = "generated/client"
"""
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(toml)

            with self.assertRaisesRegex(ConfigError, "unknown contract 'missing'"):
                load_config(pyproject)

    def test_when_required_contract_value_is_missing_expect_config_error(self):
        toml = """
[tool.openapi-contracts.contracts.catalog]
version = "1.2.3"
repository = "org/contracts"
output = "contracts/catalog.yaml"
"""
        with tempfile.TemporaryDirectory() as directory:
            pyproject = Path(directory) / "pyproject.toml"
            pyproject.write_text(toml)

            with self.assertRaisesRegex(ConfigError, "Missing 'sha256'"):
                load_config(pyproject)

if __name__ == "__main__":
    unittest.main()
