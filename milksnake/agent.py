from pysnmp.carrier.asyncio.dispatch import AsyncioDispatcher
from pysnmp.carrier.asyncio.dgram import udp
from pyasn1.codec.ber import encoder, decoder
from pysnmp.proto import api

sysDescrOid = "1.3.6.1.2.1.1.1"

class Agent:
    def __init__(self):
        self.dispatcher = AsyncioDispatcher()
        self.dispatcher.register_recv_callback(self.dispatcher_receive_callback)
        self.dispatcher.register_transport(udp.DOMAIN_NAME, udp.UdpAsyncioTransport().open_server_mode(("localhost", 9161)))

    def run(self):
        self.dispatcher.job_started(1)
        try:
            print("Started. Press Ctrl-C to stop")
            # Dispatcher will never finish as job#1 never reaches zero
            self.dispatcher.run_dispatcher()

        except KeyboardInterrupt:
            print("Shutting down...")

        finally:
            self.dispatcher.close_dispatcher()

    def dispatcher_receive_callback(self, dispatcher, domain, address, message):
        version = api.decodeMessageVersion(message)
        module = api.PROTOCOL_MODULES[version]
        request, message = decoder.decode(message, asn1Spec=module.Message())
        response = module.apiMessage.get_response(request)
        responsePdu = module.apiMessage.get_pdu(response)
        requestPdu = module.apiMessage.get_pdu(request)

        oid, val = module.apiPDU.get_varbinds(requestPdu)[0]
        if str(oid) == sysDescrOid:
            module.apiPDU.set_varbinds(responsePdu, [(oid, api.PROTOCOL_MODULES[version].OctetString("Milksnake SNMP Agent"))])
        dispatcher.send_message(encoder.encode(response), domain, address)

        return message