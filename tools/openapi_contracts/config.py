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
    generator_name: str
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


def load_openapi_contracts_section(data: dict[str, Any]) -> dict[str, Any]:
    try:
        return data["tool"]["openapi-contracts"]
    except KeyError as error:
        raise ConfigError("Missing [tool.openapi-contracts] in pyproject.toml") from error


def load_contracts(raw_contracts: dict[str, Any], root: Path) -> dict[str, Contract]:
    if not raw_contracts:
        raise ConfigError("No OpenAPI contracts configured")

    return {
        name: build_contract(name, raw_contract, root)
        for name, raw_contract in raw_contracts.items()
    }


def build_contract(name: str, raw_contract: dict[str, Any], root: Path) -> Contract:
    where = f"contract '{name}'"
    return Contract(
        name=name,
        version=str(required(raw_contract, "version", where)),
        repository=str(required(raw_contract, "repository", where)),
        tag_template=str(raw_contract.get("tag", f"{name}-api-v{{version}}")),
        artifact_template=str(raw_contract.get("artifact", f"{name}-api-{{version}}.yml")),
        sha256=str(required(raw_contract, "sha256", where)).lower(),
        output=root / str(required(raw_contract, "output", where)),
        explicit_url=raw_contract.get("url"),
    )


def load_generators(
    raw_generators: dict[str, Any],
    contracts: dict[str, Contract],
    root: Path,
) -> dict[tuple[str, str, str], Generator]:
    generators: dict[tuple[str, str, str], Generator] = {}
    for protocol, roles in raw_generators.items():
        for role, definitions in roles.items():
            validate_generator_role(role)
            for name, raw_generator in definitions.items():
                key = (protocol, role, name)
                generators[key] = build_generator(
                    protocol, role, name, raw_generator, contracts, root
                )
    return generators


def validate_generator_role(role: str) -> None:
    if role not in {"server", "client"}:
        raise ConfigError(f"Unsupported generator role: {role}")


def build_generator(
    protocol: str,
    role: str,
    name: str,
    raw_generator: dict[str, Any],
    contracts: dict[str, Contract],
    root: Path,
) -> Generator:
    where = f"generator '{protocol}.{role}.{name}'"
    contract = str(required(raw_generator, "contract", where))
    if contract not in contracts:
        raise ConfigError(f"{where} references unknown contract '{contract}'")

    reserved = {"contract", "generator", "output", "package-name"}
    return Generator(
        protocol=protocol,
        role=role,
        name=name,
        contract=contract,
        generator_name=str(required(raw_generator, "generator", where)),
        output=root / str(required(raw_generator, "output", where)),
        package_name=raw_generator.get("package-name"),
        additional_properties={
            key: value for key, value in raw_generator.items() if key not in reserved
        },
    )


def load_config(pyproject: str | Path = "pyproject.toml") -> Configuration:
    path = Path(pyproject).resolve()
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)

    root = path.parent
    section = load_openapi_contracts_section(data)
    contracts = load_contracts(section.get("contracts", {}), root)
    generators = load_generators(section.get("generators", {}), contracts, root)
    return Configuration(root, contracts, generators)
