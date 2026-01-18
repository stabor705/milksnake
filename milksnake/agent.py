"""milksnake.agent.

SNMP agent implementation built on top of pysnmp's asyncio carrier.

This agent listens on a UDP port and responds to GET requests based on an
in-memory database populated from a walkfile. Communities and port are
configured via the ``Config`` object.
"""

import types
from collections.abc import Callable
from typing import Any, ClassVar

from pyasn1.codec.ber import decoder, encoder
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.carrier.asyncio.dispatch import AsyncioDispatcher
from pysnmp.proto import api
from sortedcontainers import SortedDict

from milksnake.config import Config
from milksnake.walkfile import Asn1Type, Entry, VariableBindingEntry

Database = SortedDict[str, Entry]


class Agent:
    """A minimal SNMP agent.

    The agent uses pysnmp's AsyncioDispatcher to receive requests and returns
    values from a simple in-memory database keyed by OID string.

    Parameters
    ----------
    entries:
        Parsed walkfile entries used to seed the agent database.
    config:
        Runtime configuration (port and communities).

    """

    def __init__(self, entries: list[Entry], config: Config) -> None:
        """Initialize the agent with a database and configuration."""
        self.database = self._build_database(entries)
        self.config = config

        self._dispatcher = AsyncioDispatcher()
        self._dispatcher.register_recv_callback(self._dispatcher_receive_callback)
        self._dispatcher.register_transport(
            udp.DOMAIN_NAME,
            udp.UdpAsyncioTransport().open_server_mode(("127.0.0.1", config.port)),
        )

    def run(self) -> None:
        """Run the dispatcher loop until interrupted.

        This method blocks the current thread. Use a background thread if you
        need tests or other code to proceed concurrently.
        """
        self._dispatcher.job_started(1)
        try:
            print(f"Started on port {self.config.port}. Press Ctrl-C to stop")
            self._dispatcher.run_dispatcher()

        except KeyboardInterrupt:
            print("Shutting down...")

        finally:
            self._dispatcher.close_dispatcher()

    def stop(self) -> None:
        """Request a graceful shutdown of the dispatcher loop."""
        self._dispatcher.job_finished(1)
        self._dispatcher.close_dispatcher()

    def _dispatcher_receive_callback(
        self,
        dispatcher: AsyncioDispatcher,
        domain: tuple[str, ...],
        address: tuple[str, int],
        message: bytes,
    ) -> bytes:
        """Handle an incoming SNMP message and send a response.

        Parameters
        ----------
        dispatcher:
            pysnmp dispatcher instance.
        domain:
            Transport domain id.
        address:
            Remote address tuple.
        message:
            Raw BER-encoded SNMP message bytes.

        Returns
        -------
        bytes
            The remaining undecoded part of the message as required by pysnmp.

        """
        version = api.decodeMessageVersion(message)
        module = api.PROTOCOL_MODULES[version]
        request, message = decoder.decode(message, asn1Spec=module.Message())

        community = module.apiMessage.get_community(request)
        community_str = str(community.prettyPrint())
        if not self._verify_community(community_str):
            print(f"Invalid community string from {address}")
            return message

        response = module.apiMessage.get_response(request)
        response_pdu = module.apiMessage.get_pdu(response)
        request_pdu = module.apiMessage.get_pdu(request)

        self._fill_response(request_pdu, response_pdu, module)

        dispatcher.send_message(encoder.encode(response), domain, address)
        return message

    def _fill_response(
        self,
        request_pdu: Any,  # noqa: ANN401, could not find type for pysnmp PDU
        response_pdu: Any,  # noqa: ANN401
        module: types.ModuleType,
    ) -> list[tuple[Callable[[Any, int], None], int]]:
        variable_bindings: list[tuple[Any, Any]] = []
        errors: list[tuple[Callable[[Any, int], None], int]] = []
        if request_pdu.isSameTypeWith(module.GetRequestPDU()):
            new_variable_bindings, new_errors = self._handle_get(module, request_pdu)
            variable_bindings.extend(new_variable_bindings)
            errors.extend(new_errors)
        elif request_pdu.isSameTypeWith(module.GetNextRequestPDU()):
            new_variable_bindings, new_errors = self._handle_get_next(
                module,
                request_pdu,
            )
            variable_bindings.extend(new_variable_bindings)
            errors.extend(new_errors)
        else:
            msg = "Unsupported PDU type in request"
            raise ValueError(msg)

        module.apiPDU.set_varbinds(response_pdu, variable_bindings)
        for error_func, idx in errors:
            error_func(response_pdu, idx)
        return errors

    def _handle_get(
        self,
        module: types.ModuleType,
        request_pdu: Any,  # noqa: ANN401, could not find type for pysnmp PDU
    ) -> tuple[list[tuple[Any, Any]], list[tuple[Callable[[Any, int], None], int]]]:
        errors: list[tuple[Callable[[Any, int], None], int]] = []
        variable_bindings: list[tuple[Any, Any]] = []
        for idx, (oid, value) in enumerate(module.apiPDU.get_varbinds(request_pdu)):
            entry = self._find_entry_for_oid(str(oid))
            if entry is None:
                errors.append((module.apiPDU.set_no_such_instance_error, idx))
                variable_bindings.append((oid, value))
                break
            asn_value = Asn1Converter.create_asn_value(
                entry.type,
                entry.value,
                module,
            )
            variable_bindings.append((oid, asn_value))
        return variable_bindings, errors

    def _handle_get_next(
        self,
        module: types.ModuleType,
        request_pdu: Any,  # noqa: ANN401, could not find type for pysnmp PDU
    ) -> tuple[list[tuple[Any, Any]], list[tuple[Callable[[Any, int], None], int]]]:
        variable_bindings: list[tuple[Any, Any]] = []
        errors: list[tuple[Callable[[Any, int], None], int]] = []
        for idx, (oid, _) in enumerate(module.apiPDU.get_varbinds(request_pdu)):
            i = self.database.bisect_right(str(oid))
            if i < len(self.database):
                next_oid, next_entry = self.database.peekitem(i)
                asn_value = Asn1Converter.create_asn_value(
                    next_entry.type,
                    next_entry.value,
                    module,
                )
                variable_bindings.append((module.ObjectIdentifier(next_oid), asn_value))
            else:
                print(f"End of MIB reached: {oid}")
                errors.append((module.apiPDU.set_end_of_mib_error, idx))
                break
        return variable_bindings, errors

    def _verify_community(self, community: str) -> bool:
        """Validate the community string for this request.

        For now this checks read community only and ignores SNMP version.
        """
        return community == self.config.read_community

    def _find_entry_for_oid(self, oid: str) -> VariableBindingEntry | None:
        """Find a variable binding entry by OID string.

        Returns ``None`` if the OID either does not exist or is not a variable
        binding entry.
        """
        entry = self.database.get(oid)
        if entry is None or not isinstance(entry, VariableBindingEntry):
            return None
        return entry

    @staticmethod
    def _build_database(entries: list[Entry]) -> Database:
        """Build the internal OID -> Entry mapping from parsed entries."""
        return SortedDict({entry.oid: entry for entry in entries})


class Asn1Converter:
    """Utility class for converting between textual ASN.1 types and pysnmp types."""

    _ASN_CONVERTERS: ClassVar[dict[Asn1Type, Callable[[str], Any]]] = {
        Asn1Type.Integer: int,
        Asn1Type.String: str,
        Asn1Type.ObjectIdentifier: str,
        Asn1Type.IpAddress: str,
        Asn1Type.Counter32: int,
        Asn1Type.Counter64: int,
        Asn1Type.Gauge32: int,
        Asn1Type.Timeticks: int,
        Asn1Type.Opaque: lambda v: v.encode("utf-8"),
        Asn1Type.Bits: str,
        Asn1Type.Unsigned32: int,
        Asn1Type.HexString: bytes.fromhex,
    }

    _ASN_TYPE_MAP: ClassVar[dict[Asn1Type, str]] = {
        Asn1Type.Integer: "Integer",
        Asn1Type.String: "OctetString",
        Asn1Type.ObjectIdentifier: "ObjectIdentifier",
        Asn1Type.IpAddress: "IpAddress",
        Asn1Type.Counter32: "Counter32",
        Asn1Type.Counter64: "Counter64",
        Asn1Type.Gauge32: "Gauge32",
        Asn1Type.Timeticks: "TimeTicks",
        Asn1Type.Opaque: "Opaque",
        Asn1Type.Bits: "Bits",
        Asn1Type.Unsigned32: "Unsigned32",
        Asn1Type.HexString: "OctetString",
    }

    # ...existing code...

    @staticmethod
    def create_asn_value(
        asn_type: Asn1Type,
        value: str,
        module: types.ModuleType,
    ) -> Any:  # noqa: ANN401
        """Construct a pysnmp ASN.1 value from a textual type and value."""
        if asn_type not in Asn1Converter._ASN_TYPE_MAP:
            return module.OctetString(f"Unsupported type: {asn_type}")

        converter = Asn1Converter._ASN_CONVERTERS[asn_type]
        type_name = Asn1Converter._ASN_TYPE_MAP[asn_type]
        asn_class = getattr(module, type_name)
        return asn_class(converter(value))
