"""milksnake.config
===================

Configuration model and helpers for the Milksnake SNMP simulator.

Settings can be loaded from a small YAML file or constructed from defaults.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml


@dataclass
class Config:
    """Runtime configuration for the agent.

    Attributes
    ----------
    port:
        UDP port for the agent to listen on.
    read_community:
        Community string for read (GET) requests.
    write_community:
        Community string for write requests (not yet used).
    trap_community:
        Community string for traps (not yet used).
    walkfiles:
        List of paths to walkfiles used to populate the agent database.
    """

    port: int = 9161
    read_community: str = "public"
    write_community: str = "private"
    trap_community: str = "public"
    walkfiles: List[str] = None

    def __post_init__(self):
        if self.walkfiles is None:
            self.walkfiles = ["walkfile.txt"]

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file.

        Parameters
        ----------
        path:
            Path to a YAML file. Missing keys default to sensible values.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        walkfiles = data.get("walkfiles")
        if walkfiles is None:
            walkfile = data.get("walkfile")
            walkfiles = [walkfile] if walkfile else ["walkfile.txt"]
        
        return cls(
            port=data.get("port", 9161),
            read_community=data.get("read_community", "public"),
            write_community=data.get("write_community", "private"),
            trap_community=data.get("trap_community", "public"),
            walkfiles=walkfiles,
        )

    @classmethod
    def from_defaults(cls) -> "Config":
        """Return a configuration with default values."""
        return cls()
