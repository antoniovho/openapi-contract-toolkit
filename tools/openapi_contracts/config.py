from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

class ConfigError(ValueError):
    pass

@dataclass(frozen=True)
class Contract:
    name: str
    version: str
    repository: str
    tag_template: str
    artifact_template: str
    sha256: str
    output: Path
    explicit_url: str | None = None

    @property
    def tag(self) -> str:
        return self.tag_template.format(version=self.version)

    @property
    def artifact(self) -> str:
        return self.artifact_template.format(version=self.version)

    @property
    def url(self) -> str:
        if self.explicit_url:
            return self.explicit_url.format(
                version=self.version, tag=self.tag, artifact=self.artifact
            )
        return (
            f"https://github.com/{self.repository}/releases/download/"
            f"{self.tag}/{self.artifact}"
        )

@dataclass(frozen=True)
class Generator:
    protocol: str
    role: str
    name: str
    contract: str
    generator: str
    output: Path
    package_name: str | None
    additional_properties: dict[str, Any]

@dataclass(frozen=True)
class Configuration:
    root: Path
    contracts: dict[str, Contract]
    generators: dict[tuple[str, str, str], Generator]

def required(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ConfigError(f"Missing '{key}' in {where}")
    return data[key]

def load_config(pyproject: str | Path = "pyproject.toml") -> Configuration:
    path = Path(pyproject).resolve()
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)
    try:
        section = data["tool"]["openapi-contracts"]
    except KeyError as e:
        raise ConfigError("Missing [tool.openapi-contracts] in pyproject.toml") from e

    root = path.parent
    raw_contracts = section.get("contracts", {})
    if not raw_contracts:
        raise ConfigError("No OpenAPI contracts configured")

    contracts = {}
    for name, raw in raw_contracts.items():
        where = f"contract '{name}'"
        contracts[name] = Contract(
            name=name,
            version=str(required(raw, "version", where)),
            repository=str(required(raw, "repository", where)),
            tag_template=str(raw.get("tag", f"{name}-api-v{{version}}")),
            artifact_template=str(raw.get("artifact", f"{name}-api-{{version}}.yml")),
            sha256=str(required(raw, "sha256", where)).lower(),
            output=root / str(required(raw, "output", where)),
            explicit_url=raw.get("url"),
        )

    generators = {}
    for protocol, roles in section.get("generators", {}).items():
        for role, definitions in roles.items():
            if role not in {"server", "client"}:
                raise ConfigError(f"Unsupported generator role: {role}")
            for name, raw in definitions.items():
                where = f"generator '{protocol}.{role}.{name}'"
                contract = str(required(raw, "contract", where))
                if contract not in contracts:
                    raise ConfigError(f"{where} references unknown contract '{contract}'")
                reserved = {"contract", "generator", "output", "package-name"}
                generators[(protocol, role, name)] = Generator(
                    protocol=protocol,
                    role=role,
                    name=name,
                    contract=contract,
                    generator=str(required(raw, "generator", where)),
                    output=root / str(required(raw, "output", where)),
                    package_name=raw.get("package-name"),
                    additional_properties={
                        k: v for k, v in raw.items() if k not in reserved
                    },
                )
    return Configuration(root, contracts, generators)
