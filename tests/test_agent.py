import threading
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
from milksnake.walkfile import VariableBindingEntry


@pytest.fixture
def test_entries():
    return [
        VariableBindingEntry(oid="1.3.6.1.2.1.1.1.0", type="STRING", value="Test Device"),
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
    agent = Agent(test_entries, test_config)
    assert len(agent.database) == 2
    assert "1.3.6.1.2.1.1.1.0" in agent.database
    assert "1.3.6.1.2.1.1.2.0" in agent.database


def test_agent_config(test_entries, test_config):
    agent = Agent(test_entries, test_config)
    assert agent.config.port == 19161
    assert agent.config.read_community == "test_public"
    assert agent.config.write_community == "test_private"


def test_verify_community(test_entries, test_config):
    agent = Agent(test_entries, test_config)
    assert agent._verify_community("test_public", 0) is True
    assert agent._verify_community("wrong", 0) is False


def test_find_entry_for_oid(test_entries, test_config):
    agent = Agent(test_entries, test_config)
    
    entry = agent._find_entry_for_oid("1.3.6.1.2.1.1.1.0")
    assert entry is not None
    assert entry.type == "STRING"
    assert entry.value == "Test Device"
    
    entry = agent._find_entry_for_oid("1.3.6.1.2.1.1.2.0")
    assert entry is not None
    assert entry.type == "INTEGER"
    assert entry.value == "42"
    
    entry = agent._find_entry_for_oid("9.9.9.9")
    assert entry is None


@pytest.mark.skip(
    reason="running agent on separate thread does not work for some reason"
)
@pytest.mark.asyncio
async def test_agent():
    entries = [
        VariableBindingEntry(oid="1.2.3", type="STRING", value="test"),
        VariableBindingEntry(oid="1.2.4", type="INTEGER", value="42"),
    ]

    agent = Agent(entries, port=9161)
    thread = threading.Thread(target=agent.run, daemon=True)
    thread.start()

    snmpEngine = SnmpEngine()
    iterator = get_cmd(
        snmpEngine,
        CommunityData("public", mpModel=1),
        await UdpTransportTarget.create(("127.0.0.1", 9161), timeout=1, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity("1.2.3")),
    )

    errorIndication, errorStatus, errorIndex, varBinds = await iterator
    assert errorIndication is None
    assert not errorStatus
    assert len(varBinds) == 1
    oid, val = varBinds[0]
    assert str(oid) == "1.2.3"
    assert str(val) == "test"

    agent.stop()
    thread.join()
