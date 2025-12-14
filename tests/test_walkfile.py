def test_parse_regular_line():
    # Arrange
    from milksnake.walkfile import _parse_line, VariableBindingEntry
    line = ".1.3.6.1.2.1.2.2.1.4.4 = INTEGER: 1500"

    # Act
    entry = _parse_line(line)

    # Assert
    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"
    assert entry.type == "INTEGER"
    assert entry.value == "1500"


def test_parse_null_line():
    # Arrange
    from milksnake.walkfile import _parse_line, NullEntry
    line = '.1.3.6.1.2.1.2.2.1.4.4 = ""'

    # Act
    entry = _parse_line(line)

    # Assert
    assert isinstance(entry, NullEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"


def test_parse_empty_value():
    # Arrange
    from milksnake.walkfile import _parse_line, VariableBindingEntry
    line = ".1.3.6.1.2.1.2.2.1.4.4 = STRING: "

    # Act
    entry = _parse_line(line)

    # Assert
    assert isinstance(entry, VariableBindingEntry)
    assert entry.oid == "1.3.6.1.2.1.2.2.1.4.4"
    assert entry.type == "STRING"
    assert entry.value == ""


def test_parse_walkfile():
    # Arrange
    from io import StringIO
    from milksnake.walkfile import parse_walkfile, VariableBindingEntry, NullEntry
    file_mock = StringIO(
        """.1.3.6.1.2.1.2.2.1.4.4 = INTEGER: 1500
.1.3.6.1.2.1.2.2.1.4.5 = \"\"
.1.3.6.1.2.1.2.2.1.4.6 = STRING: 
"""
    )

    # Act
    entries = list(parse_walkfile(file_mock))

    # Assert
    assert len(entries) == 3
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
