"""DTLS Context for LwM2M

This module implements a DTLS client context for the LwM2M
client, based on the 'tinydtls' context implemented in aiocoap.

An LwM2M client using DTLS is really a "hybrid" client and
server; the LwM2M client initiates the DTLS session by sending
the intial request (bootstrap or registration).  While the
LwM2M client contains a CoAP server, there are no server credentials
in the LwM2M client since the DTLS session is already established.

This module subclasses the DTLSClientConnection and MessageInterfaceTinyDTLS
classes from the tinydtls transport to make the following changes:

    * Remove the weak reference logic (so that the transport persists
      after the initial message transfer)
    * Add a "bind" parameter to the UDP connection so that the
      LwM2M client can operate on known address and port
"""

import asyncio
from aiocoap.protocol import Context
from aiocoap.transports import tinydtls

class LwM2MDTLSClientConnection(tinydtls.DTLSClientConnection):
    def __init__(self, bind, host, port, pskId, psk, coaptransport):
        self.bind = bind
        return super().__init__(host, port, pskId, psk, coaptransport)

    async def _start(self):
        from DTLSSocket import dtls
        dtls.setLogLevel(dtls.DTLS_LOG_DEBUG)
        self._dtls_socket = None

        self._connection = None

        try:
            self._transport, _ = await self.coaptransport.loop.create_datagram_endpoint(
                    self.SingleConnection.factory(self),
                    remote_addr=(self._host, self._port),
                    local_addr=self.bind
                    )

            self._dtls_socket = dtls.DTLS(
                    read=self._read,
                    write=self._write,
                    event=self._event,
                    pskId=self._pskId,
                    pskStore={self._pskId: self._psk},
                    )
            self._connection = self._dtls_socket.connect(tinydtls._SENTINEL_ADDRESS, tinydtls._SENTINEL_PORT)

            self._retransmission_task = asyncio.create_task(self._run_retransmissions())

            self._connecting = asyncio.get_running_loop().create_future()
            await self._connecting

            queue = self._queue
            self._queue = None

            for message in queue:
                self.send(message)
            return

        except asyncio.CancelledError:
            # Can be removed starting with Python 3.8 as it's a workaround for
            # https://bugs.python.org/issue32528
            raise
        except Exception as e:
            self.coaptransport.ctx.dispatch_error(e, self)
        finally:
            if self._queue is None:
                # all worked, we're done here
                return
            self.shutdown()

class MessageInterfaceLwM2MDTLS(tinydtls.MessageInterfaceTinyDTLS):
    def __init__(self, bind, ctx, log, loop):
        self.bind = bind
        super().__init__(ctx, log, loop)
        self._pool = {}

    def _connection_for_address(self, host, port, pskId, psk):
        try:
            return self._pool[(host, port, pskId)]
        except KeyError:
            self.log.info(f'Creating LwM2MDTLSClientConnnection to ({host}, {port}, {psk})')
            connection = LwM2MDTLSClientConnection(self.bind, host, port, pskId, psk, self)
            self._pool[(host, port, pskId)] = connection
            return connection

    @classmethod
    async def create_client_transport_endpoint(cls, bind, ctx, log, loop):
        return cls(bind, ctx, log, loop)

    async def recognize_remote(self, remote):
        self.log.info(f'Searching for remote to match {remote}')
        return isinstance(remote, LwM2MDTLSClientConnection) and remote in self._pool.values()

class DtlsContext(Context):
    @classmethod
    async def create_server_context(cls, site, bind=None, *, loggername="coap-server", loop=None, server_credentials=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self = cls(loop=loop, serversite=site, loggername=loggername, server_credentials=server_credentials)
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceLwM2MDTLS.create_client_transport_endpoint(bind, mman, log=self.log, loop=loop))
        return self
