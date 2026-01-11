"""milksnake.main.

Command-line entry point for running the Milksnake SNMP simulator.

Parses arguments, loads configuration and walkfile, then starts the agent.
"""

import argparse
from pathlib import Path

from milksnake.agent import Agent
from milksnake.config import Config
from milksnake.walkfile import Entry, parse_walkfile


def _read_walkfiles(walkfiles: list[str]) -> list[Entry]:
    """Read and parse multiple walkfiles from disk.

    Parameters
    ----------
    walkfiles:
        List of paths to walkfiles containing OID/value lines.

    """
    all_entries = []
    for walkfile in walkfiles:
        with Path.open(walkfile, "r", encoding="utf-8") as f:
            entries = list(parse_walkfile(f))
        print(f"Loaded {len(entries)} entries from {walkfile}")
        all_entries.extend(entries)
    return all_entries


def _parse_args() -> argparse.Namespace:
    """Build and parse CLI arguments for the simulator."""
    parser = argparse.ArgumentParser(description="Milksnake SNMP Simulator")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file (YAML)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help=f"UDP port to listen on (default: {Config.DEFAULT_PORT})",
    )
    parser.add_argument(
        "--read-community",
        type=str,
        help=f"Read community string (default: {Config.DEFAULT_READ_COMMUNITY})",
    )
    parser.add_argument(
        "--write-community",
        type=str,
        help=f"Write community string (default: {Config.DEFAULT_WRITE_COMMUNITY})",
    )
    parser.add_argument(
        "--trap-community",
        type=str,
        help=f"Trap community string (default: {Config.DEFAULT_TRAP_COMMUNITY})",
    )
    parser.add_argument(
        "--walkfile",
        "-w",
        type=str,
        action="append",
        help=f"Path to walkfile - can be specified multiple times \
        (default: {', '.join(Config.DEFAULT_WALKFILES)})",
    )
    return parser.parse_args()


def _load_config(args: argparse.Namespace) -> Config:
    """Create a ``Config`` object from CLI arguments and/or file."""
    if args.config:
        config = Config.from_file(args.config)
        print(f"Loaded configuration from {args.config}")
    else:
        config = Config.from_defaults()
        print("Using default configuration")

    config.port = args.port if args.port is not None else config.port
    config.read_community = (
        args.read_community
        if args.read_community is not None
        else config.read_community
    )
    config.write_community = (
        args.write_community
        if args.write_community is not None
        else config.write_community
    )
    config.trap_community = (
        args.trap_community
        if args.trap_community is not None
        else config.trap_community
    )
    config.walkfiles = args.walkfile if args.walkfile is not None else config.walkfiles

    return config


def _print_config(config: Config) -> None:
    """Print configuration details."""
    print("Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Read community: {config.read_community}")
    print(f"  Write community: {config.write_community}")
    print(f"  Trap community: {config.trap_community}")
    print(f"  Walkfiles: {', '.join(config.walkfiles)}")


if __name__ == "__main__":
    args = _parse_args()
    config = _load_config(args)

    _print_config(config)

    entries = _read_walkfiles(config.walkfiles)
    agent = Agent(entries, config)
    agent.run()
