"""Implementation of LwM2M client

The LwM2M client implementation is based on the aiocoap
server (since an LwM2M client is both a CoAP server and
client).
"""

import logging
import asyncio
import os

from aiocoap import error, resource
from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.protocol import Context
from aiocoap.resource import ObservableResource, Site
from urllib.parse import urlparse

from .base import LwM2MBase
from .object import LwM2MBaseObject
from .bootstrap import LwM2MSecurityBaseObject, LwM2MServerBaseObject
from .dtls import DtlsContext

log = logging.getLogger('client')

class LwM2MBootstrapFinish(LwM2MBase):
    """Implementation of the LwM2M bootstrap-finish endpoint"""

    def __init__(self, site, event):
        self.event = event
        super(LwM2MBootstrapFinish, self).__init__(f'bootstrap-finish')

    def build_site(self, site):
        """Build site resources for multiple objects"""
        log.debug(f'bs -> {self.desc}')
        site.add_resource(('bs',), self)

    def get_obj_links(self):
        return []

    async def render_post(self, request):
        log.debug('bootstrap-finish')
        self.event.set()
        return Message(code=Code.CHANGED)

class LwM2MClient(Site):
    """LwM2M client implementation"""

    def __init__(self, address, port, bootstrap_address, bootstrap_port,
        bootstrap_psk, server_address, server_port, server_psk, endpoint,
        lifetime, **kwargs):
        super(LwM2MClient, self).__init__()
        self.address = address
        self.port = port
        self.bootstrap_address = bootstrap_address
        self.bootstrap_port = bootstrap_port
        self.bootstrap_psk = bytes.fromhex(bootstrap_psk)
        self.server_address = server_address
        self.server_port = server_port
        self.server_psk = bytes.fromhex(server_psk)
        self.endpoint = endpoint
        self.lifetime = lifetime
        self.binding_mode = 'U'
        self.objects = {}
        self.running = True
        self.register_event = asyncio.Event()
        self.bootstrap_finish_event = asyncio.Event()
        # Create endpoint for bootstrap-finish
        self.bootstrap_finish = LwM2MBootstrapFinish(self, self.bootstrap_finish_event)
        self.add_base_object('bs', self.bootstrap_finish)
        # Create object handlers for client bootstrap
        self.security_base = LwM2MSecurityBaseObject()
        self.security_base.site_changed(self.build_site)
        self.server_base = LwM2MServerBaseObject()
        self.server_base.site_changed(self.build_site)
        self.add_base_object(0, self.security_base)
        self.add_base_object(1, self.server_base)

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

    def add_base_object(self, obj_id, base_obj):
        """Add a base handler for LwM2M object instances"""
        log.info(f'Adding base object for {obj_id}')
        self.objects[obj_id] = base_obj

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

    async def bootstrap_request(self, context):
        """Perform LwM2M bootstrap request"""
        bootstrap_uri = f'coap{"s" if self.bootstrap_psk else ""}://{self.bootstrap_address}:{self.bootstrap_port}/bs?ep={self.endpoint}'
        log.debug(f'Bootstrap request: {bootstrap_uri}')
        request = Message(code=Code.POST, uri=bootstrap_uri)
        response = await context.request(request).response
        if response.code != Code.CHANGED:
            raise BaseException(
                f'unexpected code received: {response.code}. Unable to register!')

    async def client_bootstrap(self):
        """Perform client bootstrap"""
        if self.bootstrap_psk:
            bs_context = await DtlsContext.create_server_context(self, bind=(self.address, self.port))
            bs_context.client_credentials.load_from_dict(
                { f'*' : { 'dtls' : {
                    'psk' : self.bootstrap_psk,
                    'client-identity' : self.endpoint.encode()
                }}}
            )
        else:
            bs_context = await Context.create_server_context(self, bind=(self.address, self.port))
        await self.bootstrap_request(bs_context)
        await self.bootstrap_finish_event.wait()
        await bs_context.shutdown()
        # Obtain bootstrap config to client
        server_uri = self.security_base.get_server_uri()
        log.info(f'L2M2M server URI after bootstrap: {server_uri}')
        u = urlparse(server_uri)
        self.server_address = u.hostname
        self.server_port = u.port
        lifetime = self.server_base.get_lifetime()
        if lifetime > 0:
            log.info(f'Client lifetime is now {lifetime}')
            self.lifetime  = lifetime
        self.server_psk = self.security_base.get_psk()

    async def register(self, is_update=False, update_objects=False):
        """Send LwM2M client registration"""
        request = Message(code=Code.POST,
            uri=f'coap{"s" if self.server_psk else ""}://{self.server_address}:{self.server_port}'
        )
        request.opt.uri_host = self.server_address
        request.opt.uri_port = self.server_port
        # Use our registration path after initial registration
        if is_update or update_objects:
            request.opt.uri_path = ('rd', self.rd_resource,)
        else:
            request.opt.uri_path = ('rd',)
        # Include endpoint information on initial registration
        if not is_update:
            request.opt.uri_query = (
                f'ep={self.endpoint}', f'b={self.binding_mode}', f'lt={self.lifetime}', 'lwm2m=1.0')
        # Send objects on initial registration or when objects are updated
        if update_objects or not is_update:
            request.payload = ','.join(self.get_reg_links()).encode()
        log.debug('Registration to {}:{} payload={} query={}'.format(request.opt.uri_host, request.opt.uri_port, request.payload.decode(), request.opt.uri_query))
        response = await self.context.request(request).response

        # Check for success
        if not response.code.is_successful():
            raise BaseException(
                f'unexpected code received: {response.code}. Unable to register!')

        # we receive resource path ('rd', 'xyz...')
        if not is_update:
            self.rd_resource = response.opt.location_path[1]
            log.info(f'client registered at location {self.rd_resource}')

    async def registration_task(self):
        """Task that updates LwM2M client registration"""
        log.debug('registration_task()')
        # Send initial registration
        await self.register(False, False)
        while self.running:
            # Await timeout or event signalling object changes
            try:
                await asyncio.wait_for(self.register_event.wait(), self.lifetime)
                if self.register_event.is_set():
                    self.register_event.clear()
                    # Object change, re-register object list
                    self.build_site()
                    await self.register(True, True)
            except asyncio.TimeoutError as e:
                # No change, update registration on timeout
                await self.register(True, False)

    def client_updated(self):
        """Client was updated, register new objects and resources"""
        # Trigger registration task to update objects
        self.register_event.set()

    async def start(self):
        """Start and run the LwM2M client"""
        self.build_site()
        if self.bootstrap_address and self.bootstrap_port:
            # Perform bootstrap before starting client
            await self.client_bootstrap()
        if self.server_psk:
            self.context = await DtlsContext.create_server_context(self, bind=(self.address, self.port))
            self.context.client_credentials.load_from_dict(
                { f'*' : { 'dtls' : {
                    'psk' : self.server_psk,
                    'client-identity' : self.endpoint.encode()
                }}}
            )
        else:
            self.context = await Context.create_server_context(self, bind=(self.address, self.port))
        # Start registration task
        asyncio.ensure_future(self.registration_task())
