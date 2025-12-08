"""milksnake.main
=================

Command-line entry point for running the Milksnake SNMP simulator.

Parses arguments, loads configuration and walkfile, then starts the agent.
"""

import argparse

from milksnake.agent import Agent
from milksnake.config import Config
from milksnake.walkfile import parse_walkfile


def _read_walkfile(walkfile: str):
    """Read and parse a walkfile from disk.

    Parameters
    ----------
    walkfile:
        Path to the walkfile containing OID/value lines.
    """
    with open(walkfile, "r", encoding="utf-8") as f:
        entries = list(parse_walkfile(f))
    print(f"Loaded {len(entries)} entries from {walkfile}")
    return entries


def _parse_args():
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
        help="UDP port to listen on (default: 9161)",
    )
    parser.add_argument(
        "--read-community",
        type=str,
        help="Read community string (default: public)",
    )
    parser.add_argument(
        "--write-community",
        type=str,
        help="Write community string (default: private)",
    )
    parser.add_argument(
        "--trap-community",
        type=str,
        help="Trap community string (default: public)",
    )
    parser.add_argument(
        "--walkfile",
        "-w",
        type=str,
        help="Path to walkfile (default: walkfile.txt)",
    )
    return parser.parse_args()


def _load_config(args) -> Config:
    """Create a ``Config`` object from CLI arguments and/or file."""
    if args.config:
        config = Config.from_file(args.config)
        print(f"Loaded configuration from {args.config}")
    else:
        config = Config.from_defaults()
        print("Using default configuration")

    if args.port is not None:
        config.port = args.port
    if args.read_community is not None:
        config.read_community = args.read_community
    if args.write_community is not None:
        config.write_community = args.write_community
    if args.trap_community is not None:
        config.trap_community = args.trap_community
    if args.walkfile is not None:
        config.walkfile = args.walkfile

    return config


if __name__ == "__main__":
    args = _parse_args()
    config = _load_config(args)

    print("Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Read community: {config.read_community}")
    print(f"  Write community: {config.write_community}")
    print(f"  Trap community: {config.trap_community}")
    print(f"  Walkfile: {config.walkfile}")

    entries = _read_walkfile(config.walkfile)
    agent = Agent(entries, config)
    agent.run()
