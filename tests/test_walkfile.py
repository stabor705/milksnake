"""Unit tests for milksnake.walkfile module."""

from io import StringIO

from milksnake.walkfile import (
    NullEntry,
    VariableBindingEntry,
    _parse_line,
    parse_walkfile,
)


def test_parse_regular_line() -> None:
    line = ".1.3.6.1.2.1.2.2.1.4.4 = INTEGER: 1500"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"
    assert entry.type == "INTEGER"
    assert entry.value == "1500"


def test_parse_null_line() -> None:
    line = '.1.3.6.1.2.1.2.2.1.4.4 = ""'

    entry = _parse_line(line)

    assert isinstance(entry, NullEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"


def test_parse_empty_value() -> None:
    line = ".1.3.6.1.2.1.2.2.1.4.4 = STRING: "

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"
    assert entry.type == "STRING"
    assert entry.value == ""


def test_parse_walkfile() -> None:
    file_mock = StringIO(
        """.1.3.6.1.2.1.2.2.1.4.4 = INTEGER: 1500
.1.3.6.1.2.1.2.2.1.4.5 = \"\"
.1.3.6.1.2.1.2.2.1.4.6 = STRING: \n""",)

    entries = list(parse_walkfile(file_mock))

    assert len(entries) == 3  # noqa: PLR2004
    assert isinstance(entries[0], VariableBindingEntry)
    assert entries[0].oid == "1.3.6.1.2.1.2.2.1.4.4"
    assert entries[0].type == "INTEGER"
    assert entries[0].value == "1500"
    assert isinstance(entries[1], NullEntry)
    assert entries[1].oid == "1.3.6.1.2.1.2.2.1.4.5"
    assert isinstance(entries[2], VariableBindingEntry)
    assert entries[2].oid == "1.3.6.1.2.1.2.2.1.4.6"
    assert entries[2].type == "STRING"
    assert entries[2].value == ""


def test_parse_line_oid_without_leading_dot() -> None:
    """Test parsing a line where OID doesn't have a leading dot."""
    line = "1.3.6.1.2.1.1.1.0 = STRING: Test"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.1.1.0"
    assert entry.type == "STRING"
    assert entry.value == "Test"


def test_parse_line_null_entry_empty_equals() -> None:
    """Test parsing a line with NULL value (no colon in value part)."""
    line = '.1.3.6.1.2.1.1.4.0 = ""'

    entry = _parse_line(line)

    assert isinstance(entry, NullEntry)
    assert entry.oid == "1.3.6.1.2.1.1.4.0"


def test_parse_line_with_colon_in_value() -> None:
    """Test parsing a line where the value contains a colon."""
    line = ".1.3.6.1.2.1.1.1.0 = STRING: Hello: World"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.1.1.0"
    assert entry.type == "STRING"
    assert entry.value == "Hello: World"


def test_parse_line_timeticks() -> None:
    """Test parsing a Timeticks line with parenthetical value."""
    line = ".1.3.6.1.2.1.1.3.0 = Timeticks: (559299) 1:33:12.99"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.1.3.0"
    assert entry.type == "Timeticks"
    assert entry.value == "(559299) 1:33:12.99"


def test_parse_line_oid_type() -> None:
    """Test parsing an OID type line."""
    line = ".1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.99999"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.1.2.0"
    assert entry.type == "OID"
    assert entry.value == ".1.3.6.1.4.1.99999"


def test_parse_line_hex_string() -> None:
    """Test parsing a Hex-STRING line."""
    line = ".1.3.6.1.2.1.1.1.0 = Hex-STRING: 48 45 4C 4C 4F"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.1.1.0"
    assert entry.type == "Hex-STRING"
    assert entry.value == "48 45 4C 4C 4F"


def test_parse_line_counter32() -> None:
    """Test parsing a Counter32 line."""
    line = ".1.3.6.1.2.1.2.2.1.10.1 = Counter32: 123456789"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.10.1"
    assert entry.type == "Counter32"
    assert entry.value == "123456789"


def test_parse_line_gauge32() -> None:
    """Test parsing a Gauge32 line."""
    line = ".1.3.6.1.2.1.2.2.1.5.1 = Gauge32: 1000000000"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.5.1"
    assert entry.type == "Gauge32"
    assert entry.value == "1000000000"


def test_parse_line_ip_address() -> None:
    """Test parsing an IpAddress line."""
    line = ".1.3.6.1.2.1.4.20.1.1.192.168.1.1 = IpAddress: 192.168.1.1"

    entry = _parse_line(line)

    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.4.20.1.1.192.168.1.1"
    assert entry.type == "IpAddress"
    assert entry.value == "192.168.1.1"
