"""OpenAPI Generator command construction and execution."""

from __future__ import annotations
import os
import shlex
import subprocess
from .config import Configuration, Generator
from .sync import verify_contract

class GenerationError(RuntimeError):
    """Raised when OpenAPI source generation cannot complete."""

def _value(value: object) -> str:
    """Convert a generator property value to its command-line representation.

    Args:
        value: Generator property value to serialize.

    Returns:
        The string representation expected by OpenAPI Generator.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)

def build_command(config: Configuration, definition: Generator) -> list[str]:
    """Build and validate the OpenAPI Generator command for a definition.

    Args:
        config: Resolved toolkit configuration.
        definition: Generator definition to invoke.

    Returns:
        Command arguments suitable for ``subprocess.run``.

    Raises:
        ContractSyncError: If the local contract is absent or has an invalid checksum.
        GenerationError: If the generator command is empty.
    """
    contract = config.contracts[definition.contract]
    verify_contract(contract)
    command = shlex.split(
        os.environ.get("OPENAPI_GENERATOR_CMD", config.generator_command)
    )
    if not command:
        raise GenerationError("OPENAPI_GENERATOR_CMD is empty")
    command += [
        "generate", "-i", str(contract.output),
        "-g", definition.generator_name,
        "-o", str(definition.output),
    ]
    properties = dict(definition.additional_properties)
    if definition.package_name:
        properties["packageName"] = definition.package_name
    if properties:
        command += [
            "--additional-properties",
            ",".join(f"{k}={_value(v)}" for k, v in properties.items()),
        ]
    return command


def generator_environment(config: Configuration) -> dict[str, str]:
    """Build the process environment for the configured OpenAPI Generator.

    An explicit environment value overrides the reproducible project default to
    support temporary diagnostics without changing project configuration.
    """
    environment = os.environ.copy()
    if config.generator_version and "OPENAPI_GENERATOR_VERSION" not in environment:
        environment["OPENAPI_GENERATOR_VERSION"] = config.generator_version
    return environment

def generate(config: Configuration, definition: Generator, dry_run: bool = False) -> None:
    """Generate source code for a configured contract definition.

    Args:
        config: Resolved toolkit configuration.
        definition: Generator definition to invoke.
        dry_run: Whether to print the command without executing it.

    Raises:
        ContractSyncError: If the local contract is absent or has an invalid checksum.
        GenerationError: If the generator executable cannot run successfully.
    """
    command = build_command(config, definition)
    print(" ".join(shlex.quote(p) for p in command))
    if dry_run:
        return
    definition.output.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            command,
            cwd=config.root,
            check=True,
            env=generator_environment(config),
        )
    except FileNotFoundError as e:
        raise GenerationError(f"Generator executable not found: {command[0]}") from e
    except subprocess.CalledProcessError as e:
        raise GenerationError(f"Generator failed with exit code {e.returncode}") from e
