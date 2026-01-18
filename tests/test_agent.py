"""Unit tests for the Agent class in milksnake.agent module."""

import threading
import types
from io import StringIO
from unittest.mock import MagicMock, patch

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
from pysnmp.proto import api

from milksnake.agent import Agent, Asn1Converter
from milksnake.config import Config
from milksnake.walkfile import Asn1Type, VariableBindingEntry, parse_walkfile


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
    assert agent._verify_community("test_public") is True  # noqa: SLF001
    assert agent._verify_community("wrong") is False  # noqa: SLF001


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


# =============================================================================
# Asn1Converter Tests
# =============================================================================


class TestAsn1Converter:
    """Tests for the Asn1Converter utility class."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    def test_create_asn_value_integer(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Integer ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Integer, "42", snmp_module)
        assert int(result) == 42

    def test_create_asn_value_string(self, snmp_module: types.ModuleType) -> None:
        """Test creation of OctetString ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.String, "hello", snmp_module)
        assert str(result) == "hello"

    def test_create_asn_value_object_identifier(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test creation of ObjectIdentifier ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.ObjectIdentifier, "1.3.6.1.2.1", snmp_module
        )
        assert str(result) == "1.3.6.1.2.1"

    def test_create_asn_value_ip_address(self, snmp_module: types.ModuleType) -> None:
        """Test creation of IpAddress ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.IpAddress, "192.168.1.1", snmp_module
        )
        # IpAddress is stored as bytes, use prettyPrint for display
        assert result.prettyPrint() == "192.168.1.1"

    def test_create_asn_value_counter32(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Counter32 ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.Counter32, "1000000", snmp_module
        )
        assert int(result) == 1000000

    def test_create_asn_value_counter64(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Counter64 ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.Counter64, "9999999999", snmp_module
        )
        assert int(result) == 9999999999

    def test_create_asn_value_gauge32(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Gauge32 ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Gauge32, "500", snmp_module)
        assert int(result) == 500

    def test_create_asn_value_timeticks(self, snmp_module: types.ModuleType) -> None:
        """Test creation of TimeTicks ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.Timeticks, "123456", snmp_module
        )
        assert int(result) == 123456

    def test_create_asn_value_unsigned32(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Unsigned32 ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.Unsigned32, "65535", snmp_module
        )
        assert int(result) == 65535

    def test_create_asn_value_hex_string(self, snmp_module: types.ModuleType) -> None:
        """Test creation of HexString ASN.1 value."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.HexString, "48454C4C4F", snmp_module
        )
        assert bytes(result) == b"HELLO"

    def test_create_asn_value_opaque(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Opaque ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Opaque, "data", snmp_module)
        assert bytes(result) == b"data"

    def test_create_asn_value_bits(self, snmp_module: types.ModuleType) -> None:
        """Test creation of Bits ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Bits, "01", snmp_module)
        # Bits are stored as strings
        assert result is not None


# =============================================================================
# Agent Handler Tests
# =============================================================================


class TestAgentHandlers:
    """Tests for Agent request handler methods."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    @pytest.fixture
    def agent_with_entries(self) -> Agent:
        """Create an agent with sample entries for handler testing."""
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test System",
            ),
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.2.0",
                type="OID",
                value="1.3.6.1.4.1.99999",
            ),
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.3.0",
                type="Timeticks",
                value="12345678",
            ),
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.5.0",
                type="STRING",
                value="test-hostname",
            ),
        ]
        config = Config(port=19162, read_community="public", write_community="private")
        return Agent(entries, config)

    def test_handle_get_existing_oid(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get returns correct value for existing OID."""
        # Arrange
        request_pdu = snmp_module.GetRequestPDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        variable_bindings, errors = agent_with_entries._handle_get(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 0
        assert len(variable_bindings) == 1
        assert str(variable_bindings[0][1]) == "Test System"

    def test_handle_get_nonexistent_oid(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get returns error for nonexistent OID."""
        # Arrange
        request_pdu = snmp_module.GetRequestPDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.99.99.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        variable_bindings, errors = agent_with_entries._handle_get(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 1
        # Error is set_no_such_instance_error (correct pysnmp API name)
        assert errors[0][0] == snmp_module.apiPDU.set_no_such_instance_error

    def test_handle_get_multiple_oids(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get handles multiple OIDs in single request."""
        # Arrange
        request_pdu = snmp_module.GetRequestPDU()
        oid1 = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        oid2 = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.5.0")
        snmp_module.apiPDU.set_varbinds(
            request_pdu,
            [(oid1, snmp_module.Null()), (oid2, snmp_module.Null())],
        )

        # Act
        variable_bindings, errors = agent_with_entries._handle_get(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 0
        assert len(variable_bindings) == 2
        assert str(variable_bindings[0][1]) == "Test System"
        assert str(variable_bindings[1][1]) == "test-hostname"

    def test_handle_get_next_returns_next_oid(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get_next returns the next OID in lexicographic order."""
        # Arrange
        request_pdu = snmp_module.GetNextRequestPDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        variable_bindings, errors = agent_with_entries._handle_get_next(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 0
        assert len(variable_bindings) == 1
        # Should return OID 1.3.6.1.2.1.1.2.0 (next after 1.3.6.1.2.1.1.1.0)
        assert str(variable_bindings[0][0]) == "1.3.6.1.2.1.1.2.0"

    def test_handle_get_next_end_of_mib(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get_next returns end-of-MIB error when at last OID."""
        # Arrange
        request_pdu = snmp_module.GetNextRequestPDU()
        # Use an OID greater than all in database
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.5.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        variable_bindings, errors = agent_with_entries._handle_get_next(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 1
        # Correct pysnmp API method name is set_end_of_mib_error
        assert errors[0][0] == snmp_module.apiPDU.set_end_of_mib_error

    def test_handle_get_next_from_prefix(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _handle_get_next from a prefix OID returns first matching OID."""
        # Arrange
        request_pdu = snmp_module.GetNextRequestPDU()
        # Use a prefix OID that comes before all entries
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        variable_bindings, errors = agent_with_entries._handle_get_next(  # noqa: SLF001
            snmp_module, request_pdu
        )

        # Assert
        assert len(errors) == 0
        assert len(variable_bindings) == 1
        # Should return the first OID in database
        assert str(variable_bindings[0][0]) == "1.3.6.1.2.1.1.1.0"


# =============================================================================
# Agent Fill Response Tests
# =============================================================================


class TestAgentFillResponse:
    """Tests for Agent _fill_response method."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    @pytest.fixture
    def agent_with_entries(self) -> Agent:
        """Create an agent with sample entries."""
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test Device",
            ),
        ]
        config = Config(port=19163, read_community="public", write_community="private")
        return Agent(entries, config)

    def test_fill_response_get_request(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _fill_response handles GET request correctly."""
        # Arrange
        request_pdu = snmp_module.GetRequestPDU()
        response_pdu = snmp_module.GetResponsePDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        errors = agent_with_entries._fill_response(  # noqa: SLF001
            request_pdu, response_pdu, snmp_module
        )

        # Assert
        assert len(errors) == 0
        varbinds = snmp_module.apiPDU.get_varbinds(response_pdu)
        assert len(list(varbinds)) == 1

    def test_fill_response_get_next_request(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _fill_response handles GETNEXT request correctly."""
        # Arrange
        request_pdu = snmp_module.GetNextRequestPDU()
        response_pdu = snmp_module.GetResponsePDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        errors = agent_with_entries._fill_response(  # noqa: SLF001
            request_pdu, response_pdu, snmp_module
        )

        # Assert
        assert len(errors) == 0

    def test_fill_response_unsupported_pdu_type(
        self,
        agent_with_entries: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test _fill_response raises error for unsupported PDU type."""
        # Arrange - use SetRequestPDU which is not supported
        request_pdu = snmp_module.SetRequestPDU()
        response_pdu = snmp_module.GetResponsePDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported PDU type"):
            agent_with_entries._fill_response(  # noqa: SLF001
                request_pdu, response_pdu, snmp_module
            )


# =============================================================================
# Agent Lifecycle Tests
# =============================================================================


class TestAgentLifecycle:
    """Tests for Agent run and stop methods."""

    @pytest.fixture
    def simple_agent(self) -> Agent:
        """Create a simple agent for lifecycle testing."""
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test",
            ),
        ]
        config = Config(port=19164, read_community="public", write_community="private")
        return Agent(entries, config)

    def test_dispatcher_is_initialized(self, simple_agent: Agent) -> None:
        """Test that dispatcher is properly initialized."""
        # Assert - dispatcher should be set up
        assert simple_agent._dispatcher is not None  # noqa: SLF001

    def test_agent_has_config(self, simple_agent: Agent) -> None:
        """Test that agent has the correct configuration."""
        assert simple_agent.config.port == 19164
        assert simple_agent.config.read_community == "public"


# =============================================================================
# Agent Database Edge Cases
# =============================================================================


class TestAgentDatabaseEdgeCases:
    """Tests for edge cases in database operations."""

    def test_empty_database(self) -> None:
        """Test agent handles empty database gracefully."""
        # Arrange
        config = Config.from_defaults()
        entries: list[VariableBindingEntry] = []

        # Act
        agent = Agent(entries, config)

        # Assert
        assert len(agent.database) == 0

    def test_find_entry_returns_none_for_empty_database(self) -> None:
        """Test _find_entry_for_oid returns None for empty database."""
        # Arrange
        config = Config.from_defaults()
        agent = Agent([], config)

        # Act
        result = agent._find_entry_for_oid("1.3.6.1.2.1.1.1.0")  # noqa: SLF001

        # Assert
        assert result is None

    def test_database_maintains_sorted_order(self) -> None:
        """Test that database maintains OIDs in sorted order."""
        # Arrange
        config = Config.from_defaults()
        entries = [
            VariableBindingEntry(oid="1.3.6.1.2.1.1.5.0", type="STRING", value="E"),
            VariableBindingEntry(oid="1.3.6.1.2.1.1.1.0", type="STRING", value="A"),
            VariableBindingEntry(oid="1.3.6.1.2.1.1.3.0", type="STRING", value="C"),
        ]

        # Act
        agent = Agent(entries, config)
        oids = list(agent.database.keys())

        # Assert - OIDs should be in sorted order
        assert oids == sorted(oids)

    def test_duplicate_oid_last_entry_wins(self) -> None:
        """Test that when duplicate OIDs exist, the last entry wins."""
        # Arrange
        config = Config.from_defaults()
        entries = [
            VariableBindingEntry(oid="1.3.6.1.2.1.1.1.0", type="STRING", value="First"),
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0", type="STRING", value="Second"
            ),
        ]

        # Act
        agent = Agent(entries, config)

        # Assert
        assert len(agent.database) == 1
        assert agent.database["1.3.6.1.2.1.1.1.0"].value == "Second"


# =============================================================================
# Community Verification Tests
# =============================================================================


class TestCommunityVerification:
    """Extended tests for community string verification."""

    @pytest.fixture
    def agent(self) -> Agent:
        """Create an agent with known community strings."""
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test",
            ),
        ]
        config = Config(
            port=19165,
            read_community="secret_read",
            write_community="secret_write",
        )
        return Agent(entries, config)

    def test_verify_community_exact_match(self, agent: Agent) -> None:
        """Test community verification with exact match."""
        assert agent._verify_community("secret_read") is True  # noqa: SLF001

    def test_verify_community_wrong_community(self, agent: Agent) -> None:
        """Test community verification rejects wrong community."""
        assert agent._verify_community("wrong_community") is False  # noqa: SLF001

    def test_verify_community_empty_string(self, agent: Agent) -> None:
        """Test community verification rejects empty string."""
        assert agent._verify_community("") is False  # noqa: SLF001

    def test_verify_community_case_sensitive(self, agent: Agent) -> None:
        """Test community verification is case-sensitive."""
        assert agent._verify_community("SECRET_READ") is False  # noqa: SLF001
        assert agent._verify_community("Secret_Read") is False  # noqa: SLF001

    def test_verify_community_write_community_rejected_for_read(
        self, agent: Agent
    ) -> None:
        """Test that write community is not accepted as read community."""
        # The current implementation only checks read_community
        assert agent._verify_community("secret_write") is False  # noqa: SLF001


# =============================================================================
# Asn1Converter Edge Case Tests
# =============================================================================


class TestAsn1ConverterEdgeCases:
    """Tests for edge cases in Asn1Converter."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    def test_create_asn_value_with_unsupported_type(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test that unsupported ASN type returns error OctetString."""
        # Create a mock unsupported type
        from unittest.mock import MagicMock

        fake_type = MagicMock()
        fake_type.__str__ = lambda s: "UnsupportedType"

        result = Asn1Converter.create_asn_value(fake_type, "value", snmp_module)
        # Should return an OctetString with error message
        assert "Unsupported type" in str(result)

    def test_create_asn_value_integer_negative(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test creation of negative Integer ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Integer, "-100", snmp_module)
        assert int(result) == -100

    def test_create_asn_value_integer_zero(self, snmp_module: types.ModuleType) -> None:
        """Test creation of zero Integer ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.Integer, "0", snmp_module)
        assert int(result) == 0

    def test_create_asn_value_empty_string(self, snmp_module: types.ModuleType) -> None:
        """Test creation of empty OctetString ASN.1 value."""
        result = Asn1Converter.create_asn_value(Asn1Type.String, "", snmp_module)
        assert str(result) == ""

    def test_create_asn_value_string_with_spaces(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test creation of string with spaces."""
        result = Asn1Converter.create_asn_value(
            Asn1Type.String, "hello world", snmp_module
        )
        assert str(result) == "hello world"

    def test_create_asn_value_timeticks_large_value(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test creation of large TimeTicks value."""
        large_value = "4294967295"  # Max 32-bit unsigned
        result = Asn1Converter.create_asn_value(
            Asn1Type.Timeticks, large_value, snmp_module
        )
        assert int(result) == 4294967295


# =============================================================================
# Dispatcher Callback Tests
# =============================================================================


class TestDispatcherCallback:
    """Tests for _dispatcher_receive_callback method."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    @pytest.fixture
    def agent(self) -> Agent:
        """Create an agent for callback testing."""
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test System Description",
            ),
        ]
        config = Config(port=19166, read_community="public", write_community="private")
        return Agent(entries, config)

    def test_callback_with_valid_get_request(
        self,
        agent: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test callback processes valid GET request correctly."""
        from pyasn1.codec.ber import encoder

        # Build a valid SNMP GET request message
        request = snmp_module.Message()
        snmp_module.apiMessage.set_defaults(request)
        snmp_module.apiMessage.set_community(request, "public")

        request_pdu = snmp_module.GetRequestPDU()
        snmp_module.apiPDU.set_defaults(request_pdu)
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])
        snmp_module.apiMessage.set_pdu(request, request_pdu)

        message = encoder.encode(request)

        # Mock dispatcher
        mock_dispatcher = MagicMock()

        # Act
        result = agent._dispatcher_receive_callback(  # noqa: SLF001
            mock_dispatcher,
            ("udp", "127.0.0.1"),
            ("127.0.0.1", 12345),
            message,
        )

        # Assert - dispatcher should have sent a response for GET request
        mock_dispatcher.send_message.assert_called_once()

    def test_callback_with_invalid_community(
        self,
        agent: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test callback rejects request with invalid community."""
        from pyasn1.codec.ber import encoder

        # Build a SNMP request with wrong community
        request = snmp_module.Message()
        snmp_module.apiMessage.set_defaults(request)
        snmp_module.apiMessage.set_community(request, "wrong_community")

        request_pdu = snmp_module.GetRequestPDU()
        snmp_module.apiPDU.set_defaults(request_pdu)
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1.1.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])
        snmp_module.apiMessage.set_pdu(request, request_pdu)

        message = encoder.encode(request)

        # Mock dispatcher
        mock_dispatcher = MagicMock()

        # Act
        result = agent._dispatcher_receive_callback(  # noqa: SLF001
            mock_dispatcher,
            ("udp", "127.0.0.1"),
            ("127.0.0.1", 12345),
            message,
        )

        # Assert - dispatcher should NOT have sent a response
        mock_dispatcher.send_message.assert_not_called()

    def test_callback_with_getnext_request(
        self,
        agent: Agent,
        snmp_module: types.ModuleType,
    ) -> None:
        """Test callback processes valid GETNEXT request correctly."""
        from pyasn1.codec.ber import encoder

        # Build a valid SNMP GETNEXT request message
        request = snmp_module.Message()
        snmp_module.apiMessage.set_defaults(request)
        snmp_module.apiMessage.set_community(request, "public")

        request_pdu = snmp_module.GetNextRequestPDU()
        snmp_module.apiPDU.set_defaults(request_pdu)
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.1")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])
        snmp_module.apiMessage.set_pdu(request, request_pdu)

        message = encoder.encode(request)

        # Mock dispatcher
        mock_dispatcher = MagicMock()

        # Act
        result = agent._dispatcher_receive_callback(  # noqa: SLF001
            mock_dispatcher,
            ("udp", "127.0.0.1"),
            ("127.0.0.1", 12345),
            message,
        )

        # Assert - dispatcher should have sent a response for GETNEXT
        mock_dispatcher.send_message.assert_called_once()


# =============================================================================
# NullEntry and Entry Type Tests
# =============================================================================


class TestEntryTypes:
    """Tests for different entry types in the database."""

    def test_database_with_null_entry(self) -> None:
        """Test that NullEntry is stored in database but not returned by find."""
        from milksnake.walkfile import NullEntry

        config = Config.from_defaults()
        entries = [
            NullEntry(oid="1.3.6.1.2.1.1.4.0"),
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test",
            ),
        ]

        agent = Agent(entries, config)

        # Assert - both entries are in database
        assert len(agent.database) == 2
        assert "1.3.6.1.2.1.1.4.0" in agent.database
        assert "1.3.6.1.2.1.1.1.0" in agent.database

        # But _find_entry_for_oid returns None for NullEntry
        result = agent._find_entry_for_oid("1.3.6.1.2.1.1.4.0")  # noqa: SLF001
        assert result is None

        # And returns the VariableBindingEntry correctly
        result = agent._find_entry_for_oid("1.3.6.1.2.1.1.1.0")  # noqa: SLF001
        assert result is not None
        assert result.value == "Test"


# =============================================================================
# Response Error Setting Tests
# =============================================================================


class TestFillResponseErrors:
    """Tests for error handling in _fill_response."""

    @pytest.fixture
    def snmp_module(self) -> types.ModuleType:
        """Get the SNMPv2c protocol module for testing."""
        return api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]

    def test_fill_response_sets_error_on_response_pdu(
        self, snmp_module: types.ModuleType
    ) -> None:
        """Test that fill_response properly sets errors on response PDU."""
        # Create an agent with one entry
        entries = [
            VariableBindingEntry(
                oid="1.3.6.1.2.1.1.1.0",
                type="STRING",
                value="Test",
            ),
        ]
        config = Config(port=19167, read_community="public", write_community="private")
        agent = Agent(entries, config)

        # Create request for non-existent OID
        request_pdu = snmp_module.GetRequestPDU()
        response_pdu = snmp_module.GetResponsePDU()
        oid = snmp_module.ObjectIdentifier("1.3.6.1.2.1.99.99.0")
        snmp_module.apiPDU.set_varbinds(request_pdu, [(oid, snmp_module.Null())])

        # Act
        errors = agent._fill_response(request_pdu, response_pdu, snmp_module)  # noqa: SLF001

        # Assert - errors should have been set
        assert len(errors) == 1
