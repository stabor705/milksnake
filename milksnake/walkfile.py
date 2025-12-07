from dataclasses import dataclass
from typing import List, IO


@dataclass
class Entry:
    oid: str


@dataclass
class VariableBindingEntry(Entry):
    type: str
    value: str


@dataclass
class NullEntry(Entry):
    pass


def parse_walkfile(reader: IO) -> List[Entry]:
    entries = []
    for line in reader:
        entries.append(_parse_line(line[:-1]))
    return entries


def _parse_line(line: str):
    oid, var = line.split(" = ", 1)
    oid = _remove_leading_dot(oid)
    if var.find(":") == -1:
        return NullEntry(oid=oid)
    type_, value = var.split(": ", 1)
    return VariableBindingEntry(oid=oid, type=type_, value=value)


def _remove_leading_dot(oid: str) -> str:
    if oid.startswith("."):
        return oid[1:]
    return oid


if __name__ == "__main__":
    with open("walkfile.txt", "r", encoding="utf-8") as f:
        entries = parse_walkfile(f)
        for entry in entries:
            print(entry)
