"""milksnake.walkfile.

Utilities for parsing simple SNMP walk files.

Each non-empty line is expected to be in one of the following forms:

    .1.3.6.1.2.1.1.1.0 = STRING: Milksnake Agent
    .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1
    .1.3.6.1.2.1.1.3.0 = Timeticks: (559299) 1:33:12.99
    .1.3.6.1.2.1.1.4.0 =

Where the last form represents a present OID with a NULL value.
Leading dots on OIDs are removed during parsing.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import IO


@dataclass
class Entry:
    """Base class for all walkfile entries.

    Attributes
    ----------
    oid:
        Object identifier as a string. Leading dot is removed during parsing.

    """

    oid: str


class Asn1Type(StrEnum):
    """Enumeration of supported ASN.1 types in walkfiles."""

    String = "STRING"
    Integer = "INTEGER"
    ObjectIdentifier = "OID"
    IpAddress = "IpAddress"
    Counter32 = "Counter32"
    Counter64 = "Counter64"
    Gauge32 = "Gauge32"
    Timeticks = "Timeticks"
    Opaque = "Opaque"
    Bits = "BITS"
    Unsigned32 = "Unsigned32"
    HexString = "Hex-STRING"


@dataclass
class VariableBindingEntry(Entry):
    """A concrete variable binding with type and value as text.

    ``type`` corresponds to a textual SNMP type (e.g., ``STRING``, ``INTEGER``),
    and ``value`` holds the raw textual value as seen in the walk output.
    """

    type: Asn1Type
    value: str


@dataclass
class NullEntry(Entry):
    """An entry representing a present OID with a NULL value."""


def parse_walkfile(reader: IO) -> list[Entry]:
    """Parse all lines from a text reader into a list of ``Entry`` objects.

    Notes
    -----
    This function preserves trailing spaces in values and assumes each line
    ends with a single trailing newline character.

    """
    return [_parse_line(line[:-1]) for line in reader]


def _parse_line(line: str) -> Entry:
    """Parse a single walkfile line into an ``Entry`` instance."""
    oid, var = line.split(" = ", 1)
    oid = _remove_leading_dot(oid)
    if var.find(":") == -1:
        return NullEntry(oid=oid)
    type_, value = var.split(": ", 1)
    return VariableBindingEntry(oid=oid, type=Asn1Type(type_), value=value)


def _remove_leading_dot(oid: str) -> str:
    """Return ``oid`` without a leading dot, if present."""
    if oid.startswith("."):
        return oid[1:]
    return oid
