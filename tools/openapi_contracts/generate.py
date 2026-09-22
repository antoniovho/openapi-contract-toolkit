from __future__ import annotations
import os
import shlex
import subprocess
from .config import Configuration, Generator
from .sync import verify_contract

class GenerationError(RuntimeError):
    pass

def _value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)

def build_command(config: Configuration, definition: Generator) -> list[str]:
    contract = config.contracts[definition.contract]
    verify_contract(contract)
    command = shlex.split(
        os.environ.get("OPENAPI_GENERATOR_CMD", "openapi-generator-cli")
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

def generate(config: Configuration, definition: Generator, dry_run: bool = False) -> None:
    command = build_command(config, definition)
    print(" ".join(shlex.quote(p) for p in command))
    if dry_run:
        return
    definition.output.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, cwd=config.root, check=True)
    except FileNotFoundError as e:
        raise GenerationError(f"Generator executable not found: {command[0]}") from e
    except subprocess.CalledProcessError as e:
        raise GenerationError(f"Generator failed with exit code {e.returncode}") from e
