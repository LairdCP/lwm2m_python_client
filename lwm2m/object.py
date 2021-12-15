"""Base implementation of LwM2M objects with TLV encoding

This module provides implementation of LwM2M object
instances with TLV encoding.  Objects are implemented
as individual CoAP resources via aiocoap.
"""

import logging
import asyncio

from aiocoap import error, resource
from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.protocol import Context
from aiocoap.resource import ObservableResource, Site

from .base import LwM2MBase
from .resource import LwM2MMultiResource
from .tlv import TlvEncoder, TlvDecoder

log = logging.getLogger('object')

class LwM2MObjectInst(LwM2MBase):
    """Implementation of an LwM2M object instance"""

    def __init__(self, obj_id, obj_inst = 0):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.resources = {}
        super(LwM2MObjectInst, self).__init__(f'Obj_{obj_id}_{obj_inst}')

    def get_id(self):
        return self.obj_id

    def get_inst(self):
        return self.obj_inst

    def add_resource(self, res):
        self.resources[res.get_id()] = res

    def add_multi_resource(self, res):
        res_id = res.get_id()
        res_inst = res.get_inst()
        multi_res = self.resources.get(res_id)
        if not multi_res:
            log.info(f'Creating base resource {self.obj_id}_{self.obj_inst}_{res_id}')
            multi_res = LwM2MMultiResource(self.obj_id, self.obj_inst, res_id)
            self.resources[res_id] = multi_res
        multi_res.add_res_inst(res)

    def remove_resource(self, res_id, res_inst = None):
        if res_id in self.resources:
            if res_inst is not None:
                # Remove resource instance
                if not self.resources[res_id].remove_res_inst(res_inst):
                    # Remove multi object since no more object instances exist
                    del self.resources[res_inst]
            else:
                # Remove resource value
                del self.resources[res_inst]

    def build_site(self, site):
        """Add CoAP resource link to this object instance and its resources"""
        site.add_resource((str(self.obj_id), str(self.obj_inst)), self)
        log.debug(f'{self.obj_id}/{self.obj_inst} -> {self.desc}')
        for res_id, res in self.resources.items():
            res.build_site(site)

    def get_resources(self):
        return self.resources

    def get_resource(self, res_id):
        return self.resources[res_id]

    def update(self, resources):
        """Update existing resources"""
        for res_id, res in resources.items():
            self.resources[res_id].update(res)

    def get_object_link(self):
        return f'</{self.obj_id}/{self.obj_inst}>'

    async def render_get(self, request):
        log.debug(f'{self.desc}: GET request format={request.opt.content_format}')
        return TlvEncoder.get_object(self)

    async def render_post(self, request):
        log.debug(f'{self.desc}: POST request format={request.opt.content_format}')
        return TlvDecoder.update_object(request, self)

class LwM2MBaseObject(LwM2MBase):
    """Implementation of an LwM2M object that references one or more object instances"""

    def __init__(self, obj_id):
        self.obj_id = obj_id
        self.instances = {}
        super(LwM2MBaseObject, self).__init__(f'Obj_{obj_id}')

    def add_obj_inst(self, obj):
        self.instances[obj.get_inst()] = obj

    def remove_obj_inst(self, obj_inst):
        self.instances.pop(obj_inst, None)
        return bool(self.instances)

    def get_id(self):
        return self.obj_id

    def build_site(self, site):
        """Build site resources for multiple objects"""
        log.debug(f'{self.obj_id} -> {self.desc}')
        site.add_resource((self.obj_id,), self)
        for obj_inst, obj in self.instances.items():
            # Target for each instance
            obj.build_site(site)

    def get_instances(self):
        return self.instances

    async def render_get(self, request):
        log.debug(f'{self.desc}: GET request format={request.opt.content_format}')
        return TlvEncoder.get_objects(self)

    def get_obj_links(self):
        links = []
        for obj in self.instances.values():
            links.append(obj.get_object_link())
        return links
