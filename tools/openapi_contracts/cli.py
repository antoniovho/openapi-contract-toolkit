"""Command-line entry points for OpenAPI contract tooling."""

from __future__ import annotations
import argparse
import sys
from .config import ConfigError, load_config
from .generate import GenerationError, generate
from .sync import ContractSyncError, sync_contract
from .update import ContractUpdateError, update_contract

def contract_sync_main() -> None:
    """Run the command-line workflow that synchronizes configured contracts.

    Raises:
        SystemExit: With status 1 when configuration or synchronization fails.
    """
    p = argparse.ArgumentParser(prog="contract-sync")
    p.add_argument("contracts", nargs="*")
    p.add_argument("--pyproject", default="pyproject.toml")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    try:
        cfg = load_config(args.pyproject)
        names = args.contracts or list(cfg.contracts)
        unknown = [n for n in names if n not in cfg.contracts]
        if unknown:
            raise ConfigError("Unknown contract(s): " + ", ".join(unknown))
        for name in names:
            sync_contract(cfg.contracts[name], args.dry_run)
    except (ConfigError, ContractSyncError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def contract_update_main() -> None:
    """Run the command-line workflow that updates one pinned contract version.

    Raises:
        SystemExit: With status 1 when configuration, download, or update fails.
    """
    parser = argparse.ArgumentParser(prog="contract-update")
    parser.add_argument("contract")
    parser.add_argument("--version", required=True)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        configuration = load_config(args.pyproject)
        update_contract(
            configuration,
            args.pyproject,
            args.contract,
            args.version,
            args.dry_run,
        )
    except (ConfigError, ContractSyncError, ContractUpdateError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def generate_source_main() -> None:
    """Run the command-line workflow that generates source from a contract.

    Raises:
        SystemExit: With status 1 when configuration or generation fails.
    """
    p = argparse.ArgumentParser(prog="generate-source")
    role = p.add_mutually_exclusive_group(required=True)
    role.add_argument("--rest-server", action="store_true")
    role.add_argument("--rest-client", action="store_true")
    p.add_argument("--api", required=True)
    p.add_argument("--pyproject", default="pyproject.toml")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    try:
        cfg = load_config(args.pyproject)
        selected_role = "server" if args.rest_server else "client"
        key = ("rest", selected_role, args.api)
        if key not in cfg.generators:
            available = sorted(
                name for protocol, role_name, name in cfg.generators
                if protocol == "rest" and role_name == selected_role
            )
            extra = f" Available: {', '.join(available)}" if available else ""
            raise ConfigError(
                f"Unknown REST {selected_role} generator '{args.api}'.{extra}"
            )
        generate(cfg, cfg.generators[key], args.dry_run)
    except (ConfigError, ContractSyncError, GenerationError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from e
