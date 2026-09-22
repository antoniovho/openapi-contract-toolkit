"""Configuration loading and validation for OpenAPI contract tooling."""

from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
import tomllib

class ConfigError(ValueError):
    """Raised when the OpenAPI contracts configuration is invalid."""

@dataclass(frozen=True)
class Contract:
    """Describe a downloadable OpenAPI contract and its local destination.

    Attributes:
        name: Contract identifier.
        version: Version of the contract artifact.
        repository: GitHub repository that publishes the artifact.
        tag_template: Release tag template accepting ``version``.
        artifact_template: Artifact filename template accepting ``version``.
        sha256: Expected SHA-256 checksum in lowercase hexadecimal.
        output: Local path where the downloaded artifact is stored.
        explicit_url: Optional artifact URL template.
    """

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
        """Return the release tag rendered with the configured version.

        Returns:
            The configured release tag.
        """
        return self.tag_template.format(version=self.version)

    @property
    def artifact(self) -> str:
        """Return the artifact filename rendered with the configured version.

        Returns:
            The configured artifact filename.
        """
        return self.artifact_template.format(version=self.version)

    @property
    def url(self) -> str:
        """Return the URL from which to download the contract artifact.

        Returns:
            The explicit URL or the GitHub releases URL for the artifact.
        """
        if self.explicit_url:
            return self.explicit_url.format(
                version=self.version, tag=self.tag, artifact=self.artifact
            )
        return (
            f"https://github.com/{self.repository}/releases/download/"
            f"{self.tag}/{self.artifact}"
        )

    def with_version(self, version: str) -> Contract:
        """Return this contract configured for an explicit candidate version.

        Args:
            version: Version to apply when rendering the release metadata.

        Returns:
            A copy of this contract using ``version``.
        """
        return replace(self, version=version)

@dataclass(frozen=True)
class Generator:
    """Describe an OpenAPI generator invocation configured for a contract.

    Attributes:
        protocol: API protocol handled by the generator.
        role: Generator role, either ``server`` or ``client``.
        name: Generator identifier within its protocol and role.
        contract: Name of the source contract.
        generator_name: OpenAPI Generator implementation name.
        output: Directory where generated source is written.
        package_name: Optional package name passed to the generator.
        additional_properties: Additional generator-specific properties.
    """

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
    """Contain the resolved contract and generator configuration.

    Attributes:
        root: Directory containing the configuration file.
        contracts: Configured contracts keyed by name.
        generators: Configured generators keyed by protocol, role, and name.
    """

    root: Path
    contracts: dict[str, Contract]
    generators: dict[tuple[str, str, str], Generator]

def required(data: dict[str, Any], key: str, where: str) -> Any:
    """Return a required mapping value or raise a contextual configuration error.

    Args:
        data: Mapping that contains the configuration value.
        key: Required configuration key.
        where: Description of the configuration scope for error reporting.

    Returns:
        The value associated with ``key``.

    Raises:
        ConfigError: If ``key`` is absent from ``data``.
    """
    if key not in data:
        raise ConfigError(f"Missing '{key}' in {where}")
    return data[key]


def load_openapi_contracts_section(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the OpenAPI contracts section from parsed project data.

    Args:
        data: Parsed TOML document.

    Returns:
        The ``tool.openapi-contracts`` configuration mapping.

    Raises:
        ConfigError: If the configuration section is absent.
    """
    try:
        return data["tool"]["openapi-contracts"]
    except KeyError as error:
        raise ConfigError("Missing [tool.openapi-contracts] in pyproject.toml") from error


def load_contracts(raw_contracts: dict[str, Any], root: Path) -> dict[str, Contract]:
    """Build configured contracts keyed by their names.

    Args:
        raw_contracts: Raw contract definitions from the TOML configuration.
        root: Directory against which output paths are resolved.

    Returns:
        Validated contracts keyed by name.

    Raises:
        ConfigError: If no contracts are configured or a definition is invalid.
    """
    if not raw_contracts:
        raise ConfigError("No OpenAPI contracts configured")

    return {
        name: build_contract(name, raw_contract, root)
        for name, raw_contract in raw_contracts.items()
    }


def build_contract(name: str, raw_contract: dict[str, Any], root: Path) -> Contract:
    """Build one validated contract from its raw configuration mapping.

    Args:
        name: Contract identifier.
        raw_contract: Raw configuration for the contract.
        root: Directory against which the output path is resolved.

    Returns:
        The validated contract definition.

    Raises:
        ConfigError: If a required configuration key is missing.
    """
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
    """Build configured generators keyed by protocol, role, and name.

    Args:
        raw_generators: Raw generator definitions from the TOML configuration.
        contracts: Available contracts keyed by name.
        root: Directory against which output paths are resolved.

    Returns:
        Validated generators keyed by protocol, role, and name.

    Raises:
        ConfigError: If a role, contract reference, or definition is invalid.
    """
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
    """Ensure that a generator role is supported by the toolkit.

    Args:
        role: Generator role to validate.

    Raises:
        ConfigError: If the role is not ``server`` or ``client``.
    """
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
    """Build one validated generator from its raw configuration mapping.

    Args:
        protocol: API protocol for the generator.
        role: Generator role.
        name: Generator identifier.
        raw_generator: Raw configuration for the generator.
        contracts: Available contracts keyed by name.
        root: Directory against which the output path is resolved.

    Returns:
        The validated generator definition.

    Raises:
        ConfigError: If the contract reference or required keys are invalid.
    """
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
    """Load and resolve OpenAPI contracts configuration from a TOML file.

    Args:
        pyproject: Path to the TOML configuration file.

    Returns:
        The resolved toolkit configuration.

    Raises:
        ConfigError: If the file or required configuration is invalid.
    """
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
