from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

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

    DEFAULT_PORT: int = 9161
    DEFAULT_READ_COMMUNITY: str = "public"
    DEFAULT_WRITE_COMMUNITY: str = "private"
    DEFAULT_TRAP_COMMUNITY: str = "public"
    DEFAULT_WALKFILES: ClassVar[list[str]] = ["walkfile.txt"]

    port: int = DEFAULT_PORT
    read_community: str = DEFAULT_READ_COMMUNITY
    write_community: str = DEFAULT_WRITE_COMMUNITY
    trap_community: str = DEFAULT_TRAP_COMMUNITY
    walkfiles: list[str] | None = None

    def __post_init__(self) -> None:
        """Post-initialization to set default walkfiles if none provided."""
        if self.walkfiles is None:
            self.walkfiles = self.DEFAULT_WALKFILES

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Create a ``Config`` object from a YAML configuration file."""
        with Path.open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        walkfiles = data.get("walkfiles", cls.DEFAULT_WALKFILES)

        return cls(
            port=data.get("port", cls.DEFAULT_PORT),
            read_community=data.get("read_community", cls.DEFAULT_READ_COMMUNITY),
            write_community=data.get("write_community", cls.DEFAULT_WRITE_COMMUNITY),
            trap_community=data.get("trap_community", cls.DEFAULT_TRAP_COMMUNITY),
            walkfiles=walkfiles,
        )

    @classmethod
    def from_defaults(cls) -> "Config":
        """Create a ``Config`` object with all default values."""
        return cls()
