"""Implementation of LwM2M client

The LwM2M client implementation is based on the aiocoap
server (since an LwM2M client is both a CoAP server and
client).
"""

import logging
import asyncio

from aiocoap import error, resource
from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.protocol import Context
from aiocoap.resource import ObservableResource, Site

from .object import LwM2MBaseObject

log = logging.getLogger('client')

class LwM2MClient(Site):
    """LwM2M client implementation"""

    def __init__(self, address, port, server_address = 'localhost', server_port = 5783, endpoint = 'python-client'):
        super(LwM2MClient, self).__init__()
        self.address = address
        self.port = port
        self.server_address = server_address
        self.server_port = server_port
        self.endpoint = endpoint
        self.lifetime = 3600
        self.binding_mode = 'U'
        self.objects = {}

    async def render(self, request):
        """Handle render request from aiocoap"""
        log.debug(f'client render {str(request.code)} on {request.opt.uri_path}')
        return await super().render(request)

    def add_object(self, obj):
        """Add an LwM2M object instance"""
        obj_id = obj.get_id()
        base_obj = self.objects.get(obj_id)
        if not base_obj:
            log.info(f'Creating base object {obj_id}')
            base_obj = LwM2MBaseObject(obj_id)
            self.objects[obj_id] = base_obj
        base_obj.add_obj_inst(obj)

    def remove_object(self, obj_id, obj_inst = None):
        """Remove an LwM2M Object instance"""
        if obj_id in self._objects:
            if not self._objects[obj_id].remove_obj_inst(obj_inst):
                # Remove base object since no more object instances exist
                log.info(f'Removing base object {obj_id}')
                del self._objects[obj_id]

    def build_site(self):
        """Build or re-build the CoAP site resources"""
        self._resources = {}
        for obj_id, obj in self.objects.items():
            obj.build_site(self)

    def get_reg_links(self):
        """Obtain the list of objct instance links used for client registration"""
        links = []
        for base_obj in self.objects.values():
            links = links + base_obj.get_obj_links()
        return links

    async def register(self):
        """Perform initial LwM2M client registration"""
        request = Message(code=Code.POST, payload=','.join(
            self.get_reg_links()).encode(),
            uri=f'coap://{self.server_address}:{self.server_port}'
        )
        request.opt.uri_host = self.server_address
        request.opt.uri_port = self.server_port
        request.opt.uri_path = ('rd',)
        request.opt.uri_query = (
            f'ep={self.endpoint}', f'b={self.binding_mode}', f'lt={self.lifetime}', 'lwm2m=1.0')
        log.debug('Initial registration to {}:{} payload={} query={}'.format(request.opt.uri_host, request.opt.uri_port, request.payload.decode(), request.opt.uri_query))
        response = await self.context.request(request).response

        # expect ACK
        if response.code != Code.CREATED:
            raise BaseException(
                f'unexpected code received: {response.code}. Unable to register!')

        # we receive resource path ('rd', 'xyz...')
        self.rd_resource = response.opt.location_path[1]
        log.info(f'client registered at location {self.rd_resource}')
        if self.lifetime > 0:
            await asyncio.sleep(self.lifetime - 1)
            asyncio.ensure_future(self.update_register())

    async def update_register(self):
        """Update LwM2M client registration"""
        log.debug('update_register()')
        update = Message(code=Code.POST, uri=f'coap://{self.server_address}:{self.server_port}')
        update.opt.uri_host = self.server_address
        update.opt.uri_port = self.server_port
        update.opt.uri_path = ('rd', self.rd_resource)
        response = await self.context.request(update).response
        if response.code != Code.CHANGED:
            # error while update, fallback to re-register
            log.warning(
                f'failed to update registration, code {response.code}, falling back to registration')
            asyncio.ensure_future(self.register())
        else:
            log.info(f'updated registration for {self.rd_resource}')
            # yield to next update - 1 sec
            if self.lifetime > 0:
                await asyncio.sleep(self.lifetime - 1)
                asyncio.ensure_future(self.update_register())

    async def start(self):
        """Start and run the LwM2M client"""
        self.build_site()
        self.context = await Context.create_server_context(self, bind=(self.address, self.port))
        await self.register()
