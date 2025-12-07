from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class Config:
    port: int = 9161
    read_community: str = "public"
    write_community: str = "private"
    trap_community: str = "public"
    walkfile: str = "walkfile.txt"

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            port=data.get("port", 9161),
            read_community=data.get("read_community", "public"),
            write_community=data.get("write_community", "private"),
            trap_community=data.get("trap_community", "public"),
            walkfile=data.get("walkfile", "walkfile.txt"),
        )

    @classmethod
    def from_defaults(cls) -> "Config":
        return cls()
