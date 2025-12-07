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


@pytest.mark.skip(
    reason="running agent on separate thread does not work for some reason"
)
@pytest.mark.asyncio
async def test_agent():
    from milksnake.agent import Agent
    from milksnake.walkfile import VariableBindingEntry

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
