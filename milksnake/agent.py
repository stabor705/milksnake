from pysnmp.carrier.asyncio.dispatch import AsyncioDispatcher
from pysnmp.carrier.asyncio.dgram import udp
from pyasn1.codec.ber import encoder, decoder
from pysnmp.proto import api

from typing import List, Dict, Any

from milksnake.config import Config
from milksnake.walkfile import Entry, VariableBindingEntry

Database = Dict[str, Entry]


class Agent:
    def __init__(self, entries: List[Entry], config: Config):
        self.database = self._build_database(entries)
        self.config = config

        self._dispatcher = AsyncioDispatcher()
        self._dispatcher.register_recv_callback(self._dispatcher_receive_callback)
        self._dispatcher.register_transport(
            udp.DOMAIN_NAME,
            udp.UdpAsyncioTransport().open_server_mode(("127.0.0.1", config.port)),
        )

    def run(self):
        self._dispatcher.job_started(1)
        try:
            print(f"Started on port {self.config.port}. Press Ctrl-C to stop")
            self._dispatcher.run_dispatcher()

        except KeyboardInterrupt:
            print("Shutting down...")

        finally:
            self._dispatcher.close_dispatcher()

    def stop(self):
        self._dispatcher.job_finished(1)
        self._dispatcher.close_dispatcher()

    def _dispatcher_receive_callback(self, dispatcher, domain, address, message):
        version = api.decodeMessageVersion(message)
        module = api.PROTOCOL_MODULES[version]
        request, message = decoder.decode(message, asn1Spec=module.Message())
        
        community = module.apiMessage.get_community(request)
        community_str = str(community.prettyPrint())
        if not self._verify_community(community_str, version):
            print(f"Invalid community string from {address}")
            return message
        
        response = module.apiMessage.get_response(request)
        responsePdu = module.apiMessage.get_pdu(response)
        requestPdu = module.apiMessage.get_pdu(request)

        oid, _ = module.apiPDU.get_varbinds(requestPdu)[0]
        entry = self._find_entry_for_oid(str(oid))
        
        if entry is None:
            print(f"OID not found: {oid}")
            module.apiPDU.set_error_status(responsePdu, 2)
        else:
            asn_value = self._create_asn_value(entry.type, entry.value, module)
            module.apiPDU.set_varbinds(responsePdu, [(oid, asn_value)])
        
        dispatcher.send_message(encoder.encode(response), domain, address)
        return message

    def _verify_community(self, community: str, version: int) -> bool:
        return community == self.config.read_community

    def _find_entry_for_oid(self, oid: str) -> VariableBindingEntry | None:
        entry = self.database.get(oid)
        if entry is None or not isinstance(entry, VariableBindingEntry):
            return None
        return entry

    @staticmethod
    def _create_asn_value(type: str, value: str, module):
        match type:
            case "INTEGER":
                return module.Integer(int(value))
            case "STRING":
                return module.OctetString(value)
            case _:
                raise ValueError(f"Unsupported type: {type}")

    @staticmethod
    def _build_database(entries: List[Entry]) -> Database:
        return {entry.oid: entry for entry in entries}
