"""Unit tests for the Agent class in milksnake.agent module."""

import threading
from io import StringIO

import pytest
from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
)

from milksnake.agent import Agent
from milksnake.config import Config
from milksnake.walkfile import VariableBindingEntry, parse_walkfile


@pytest.fixture
def test_entries() -> list[VariableBindingEntry]:
    """Create sample variable binding entries for testing."""
    return [
        VariableBindingEntry(
            oid="1.3.6.1.2.1.1.1.0",
            type="STRING",
            value="Test Device",
        ),
        VariableBindingEntry(oid="1.3.6.1.2.1.1.2.0", type="INTEGER", value="42"),
    ]


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration with custom port and communities."""
    return Config(
        port=19161,
        read_community="test_public",
        write_community="test_private",
    )


def test_agent_database_creation(
    test_entries: list[VariableBindingEntry],
    test_config: Config,
) -> None:
    """Test that Agent correctly creates database from entries."""
    # Arrange & Act
    agent = Agent(test_entries, test_config)

    # Assert
    expected_database_length = 2
    assert len(agent.database) == expected_database_length
    assert "1.3.6.1.2.1.1.1.0" in agent.database
    assert "1.3.6.1.2.1.1.2.0" in agent.database


def test_agent_config(
    test_entries: list[VariableBindingEntry],
    test_config: Config,
) -> None:
    """Test that Agent stores configuration correctly."""
    # Arrange & Act
    agent = Agent(test_entries, test_config)

    # Assert
    expected_port = 19161
    assert agent.config.port == expected_port
    assert agent.config.read_community == "test_public"
    assert agent.config.write_community == "test_private"


def test_verify_community(
    test_entries: list[VariableBindingEntry],
    test_config: Config,
) -> None:
    """Test community string verification accepts valid and rejects invalid."""
    # Arrange
    agent = Agent(test_entries, test_config)

    # Act & Assert
    assert agent._verify_community("test_public", 0) is True  # noqa: SLF001
    assert agent._verify_community("wrong", 0) is False  # noqa: SLF001


def test_find_entry_for_oid(
    test_entries: list[VariableBindingEntry],
    test_config: Config,
) -> None:
    """Test OID lookup returns correct entries or None for missing OIDs."""
    # Arrange
    agent = Agent(test_entries, test_config)

    # Act
    entry1 = agent._find_entry_for_oid("1.3.6.1.2.1.1.1.0")  # noqa: SLF001
    entry2 = agent._find_entry_for_oid("1.3.6.1.2.1.1.2.0")  # noqa: SLF001
    entry3 = agent._find_entry_for_oid("9.9.9.9")  # noqa: SLF001

    # Assert
    assert entry1 is not None
    assert entry1.type == "STRING"
    assert entry1.value == "Test Device"
    assert entry2 is not None
    assert entry2.type == "INTEGER"
    assert entry2.value == "42"
    assert entry3 is None


def test_build_database_with_multiple_files_no_conflict() -> None:
    """Test database building with entries from multiple walkfiles."""
    # Arrange
    config = Config.from_defaults()
    file1 = StringIO(".1.3.6.1.2.1.1.1.0 = STRING: First\n")
    file2 = StringIO(".1.3.6.1.2.1.1.2.0 = STRING: Second\n")
    entries1 = list(parse_walkfile(file1))
    entries2 = list(parse_walkfile(file2))
    all_entries = entries1 + entries2

    # Act
    agent = Agent(all_entries, config)

    # Assert
    expected_database_length = 2
    assert len(agent.database) == expected_database_length
    assert agent.database["1.3.6.1.2.1.1.1.0"].value == "First"
    assert agent.database["1.3.6.1.2.1.1.2.0"].value == "Second"


def test_build_database_with_three_files() -> None:
    """Test database building with entries from three walkfiles."""
    # Arrange
    config = Config.from_defaults()
    file1 = StringIO(".1.3.6.1.2.1.1.1.0 = INTEGER: 100\n")
    file2 = StringIO(".1.3.6.1.2.1.1.2.0 = STRING: Text\n")
    file3 = StringIO(".1.3.6.1.2.1.1.3.0 = INTEGER: 200\n")
    entries = []
    for f in [file1, file2, file3]:
        entries.extend(list(parse_walkfile(f)))

    # Act
    agent = Agent(entries, config)

    # Assert
    expected_database_length = 3
    assert len(agent.database) == expected_database_length


@pytest.mark.skip(
    reason="running agent on separate thread does not work for some reason",
)
@pytest.mark.asyncio
async def test_agent() -> None:
    """Integration test for Agent handling SNMP GET requests."""
    # Arrange
    entries = [
        VariableBindingEntry(oid="1.2.3", type="STRING", value="test"),
        VariableBindingEntry(oid="1.2.4", type="INTEGER", value="42"),
    ]
    agent = Agent(entries, port=9161)
    thread = threading.Thread(target=agent.run, daemon=True)
    thread.start()
    snmp_engine = SnmpEngine()

    # Act
    iterator = get_cmd(
        snmp_engine,
        CommunityData("public", mpModel=1),
        await UdpTransportTarget.create(("127.0.0.1", 9161), timeout=1, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity("1.2.3")),
    )
    error_indication, error_status, _, var_binds = await iterator

    # Assert
    assert error_indication is None
    assert not error_status
    assert len(var_binds) == 1
    oid, val = var_binds[0]
    assert str(oid) == "1.2.3"
    assert str(val) == "test"

    agent.stop()
    thread.join()
