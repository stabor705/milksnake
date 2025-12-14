import threading
from io import StringIO
from pysnmp.hlapi.asyncio import (
    SnmpEngine,
    get_cmd,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
import pytest
from milksnake.agent import Agent
from milksnake.config import Config
from milksnake.walkfile import VariableBindingEntry, parse_walkfile


@pytest.fixture
def test_entries():
    return [
        VariableBindingEntry(
            oid="1.3.6.1.2.1.1.1.0", type="STRING", value="Test Device"
        ),
        VariableBindingEntry(oid="1.3.6.1.2.1.1.2.0", type="INTEGER", value="42"),
    ]


@pytest.fixture
def test_config():
    return Config(
        port=19161,
        read_community="test_public",
        write_community="test_private",
    )


def test_agent_database_creation(test_entries, test_config):
    # Arrange & Act
    agent = Agent(test_entries, test_config)

    # Assert
    assert len(agent.database) == 2
    assert "1.3.6.1.2.1.1.1.0" in agent.database
    assert "1.3.6.1.2.1.1.2.0" in agent.database


def test_agent_config(test_entries, test_config):
    # Arrange & Act
    agent = Agent(test_entries, test_config)

    # Assert
    assert agent.config.port == 19161
    assert agent.config.read_community == "test_public"
    assert agent.config.write_community == "test_private"


def test_verify_community(test_entries, test_config):
    # Arrange
    agent = Agent(test_entries, test_config)

    # Act & Assert
    assert agent._verify_community("test_public", 0) is True
    assert agent._verify_community("wrong", 0) is False


def test_find_entry_for_oid(test_entries, test_config):
    # Arrange
    agent = Agent(test_entries, test_config)

    # Act
    entry1 = agent._find_entry_for_oid("1.3.6.1.2.1.1.1.0")
    entry2 = agent._find_entry_for_oid("1.3.6.1.2.1.1.2.0")
    entry3 = agent._find_entry_for_oid("9.9.9.9")

    # Assert
    assert entry1 is not None
    assert entry1.type == "STRING"
    assert entry1.value == "Test Device"
    assert entry2 is not None
    assert entry2.type == "INTEGER"
    assert entry2.value == "42"
    assert entry3 is None

def test_build_database_with_multiple_files_no_conflict():
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
    assert len(agent.database) == 2
    assert agent.database["1.3.6.1.2.1.1.1.0"].value == "First"
    assert agent.database["1.3.6.1.2.1.1.2.0"].value == "Second"


def test_build_database_with_three_files():
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
    assert len(agent.database) == 3


@pytest.mark.skip(
    reason="running agent on separate thread does not work for some reason"
)
@pytest.mark.asyncio
async def test_agent():
    # Arrange
    entries = [
        VariableBindingEntry(oid="1.2.3", type="STRING", value="test"),
        VariableBindingEntry(oid="1.2.4", type="INTEGER", value="42"),
    ]
    agent = Agent(entries, port=9161)
    thread = threading.Thread(target=agent.run, daemon=True)
    thread.start()
    snmpEngine = SnmpEngine()

    # Act
    iterator = get_cmd(
        snmpEngine,
        CommunityData("public", mpModel=1),
        await UdpTransportTarget.create(("127.0.0.1", 9161), timeout=1, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity("1.2.3")),
    )
    errorIndication, errorStatus, errorIndex, varBinds = await iterator

    # Assert
    assert errorIndication is None
    assert not errorStatus
    assert len(varBinds) == 1
    oid, val = varBinds[0]
    assert str(oid) == "1.2.3"
    assert str(val) == "test"

    agent.stop()
    thread.join()
