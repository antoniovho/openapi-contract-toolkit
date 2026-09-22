from pathlib import Path
import tempfile
import unittest
from tools.openapi_contracts.config import load_config

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

if __name__ == "__main__":
    unittest.main()
