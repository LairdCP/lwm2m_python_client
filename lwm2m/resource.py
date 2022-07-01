"""Base implementation of LwM2M resources with TLV encoding

This module provides implementation of LwM2M resource values
and multi-resource instances with TLV encoding.  Resources
and resource instances are implemented as individual CoAP
resources via aiocoap.
"""

import logging
import asyncio

from aiocoap import error, resource
from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.protocol import Context
from aiocoap.resource import ObservableResource, Site

from .base import LwM2MBase
from .tlv import TlvEncoder, TlvDecoder

log = logging.getLogger('resource')

class LwM2MResourceBase(LwM2MBase):
    """Base implementation of an LwM2M resource value or instance"""

    def __init__(self, obj_id, obj_inst, res_id, res_inst = None, value = None, value_written_cb = None):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.res_id = res_id
        self.res_inst = res_inst
        self.value = value
        self.value_written_cb = value_written_cb
        self._type = type(value).__name__
        self.observe = False
        self.notify_cb = None
        if res_inst:
            super(LwM2MResourceBase, self).__init__(f'Obj_{obj_id}_{obj_inst}_Res_{res_id}_{res_inst}')
        else:
            super(LwM2MResourceBase, self).__init__(f'Obj_{obj_id}_{obj_inst}_Res_{res_id}')

    def get_id(self):
        return self.res_id

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value
        if self.notify_cb:
            self.notify_cb()

    def update_observation_count(self, newcount):
        log.debug(f'{self.desc} observation count = {newcount}')
        self.observe = newcount > 0
        super(LwM2MResourceBase, self).update_observation_count(newcount)

    def get_type(self):
        return self._type

    def update(self, value):
        self.value = value
        if self.value_written_cb:
            self.value_written_cb(value)

    def notify(self, notify_cb):
        self.notify_cb = notify_cb

class LwM2MResourceValue(LwM2MResourceBase):
    """Implementation of an LwM2M resource value"""
    def __init__(self, obj_id, obj_inst, res_id, value = None, value_written_cb = None):
        super(LwM2MResourceValue, self).__init__(obj_id, obj_inst, res_id, None, value, value_written_cb)

    def set_value(self, value):
        super(LwM2MResourceValue, self).set_value(value)
        if self.observe:
            log.debug(f'Sending notify for {self.desc}')
            self.updated_state(TlvEncoder.get_resource_value(self))

    def build_site(self, site):
        """Add CoAP resource link to this resource value"""
        log.debug(f'{self.obj_id}/{self.obj_inst}/{self.res_id} -> {self.desc}')
        site.add_resource((str(self.obj_id), str(self.obj_inst), str(self.res_id)), self)

    async def render_get(self, request):
        log.debug(f'{self.desc}: GET request format={request.opt.content_format} observe={request.opt.observe}')
        return TlvEncoder.get_resource_value(self)

    async def render_post(self, request):
        log.debug(f'{self.desc}: POST request format={request.opt.content_format}')
        return TlvDecoder.update_resource_value(request, self)

    async def render_put(self, request):
        log.debug(f'{self.desc}: PUT request format={request.opt.content_format}')
        return TlvDecoder.update_resource_value(request, self)

class LwM2MResourceInst(LwM2MResourceBase):
    """Implementation of an LwM2M resource instance"""

    def __init__(self, obj_id, obj_inst, res_id, res_inst, value = None, value_written_cb = None):
        super(LwM2MResourceInst, self).__init__(obj_id, obj_inst, res_id, res_inst, value, value_written_cb)

    def get_inst(self):
        return self.res_inst

    def set_value(self, value):
        super(LwM2MResourceInst, self).set_value(value)
        if self.observe:
            log.debug(f'Sending notify for {self.desc}')
            self.updated_state(TlvEncoder.get_resource_inst(self))

    def build_site(self, site):
        """Add CoAP resource link to this resource instance"""
        log.debug(f'{self.obj_id}/{self.obj_inst}/{self.res_id}/{self.res_inst} -> {self.desc}')
        site.add_resource((str(self.obj_id), str(self.obj_inst), str(self.res_id), str(self.res_inst)), self)

    async def render_get(self, request):
        log.debug(f'{self.desc}: GET request format={request.opt.content_format} observe={request.opt.observe}')
        return TlvEncoder.get_resource_inst(self)

    async def render_post(self, request):
        log.debug(f'{self.desc}: POST request format={request.opt.content_format}')
        return TlvDecoder.update_resource_value(request, self)

    async def render_put(self, request):
        log.debug(f'{self.desc}: PUT request format={request.opt.content_format}')
        return TlvDecoder.update_resource_value(request, self)

class LwM2MMultiResource(LwM2MBase):
    """Implementation of an LwM2M multiple resource that contains resource instances"""

    def __init__(self, obj_id, obj_inst, res_id):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.res_id = res_id
        self.instances = {}
        self._type = None
        self.observe = False
        self.notify_cb = None
        super(LwM2MMultiResource, self).__init__(f'Obj_{obj_id}_{obj_inst}_Res_{res_id}')

    def add_res_inst(self, res):
        self.instances[res.get_inst()] = res
        # Store type so we can properly decode writes
        if self._type == None:
            self._type = type(res.get_value()).__name__
        # Tell instance to notify us when changed
        res.notify(self.instance_changed)

    def get_id(self):
        return self.res_id

    def get_type(self):
        return self._type

    def get_instances(self):
        return self.instances

    def update(self, instances):
        """Update (change or add) resource instances"""
        for inst, newval in instances.items():
            if inst in self.instances:
                self.instances[inst].set_value(newval)
            else:
                self.instances[inst] = LwM2MResourceInst(self.obj_id, self.obj_inst, self.res_id, inst, newval)

    def update_observation_count(self, newcount):
        log.debug(f'{self.desc} observation count = {newcount}')
        self.observe = newcount > 0
        super(LwM2MMultiResource, self).update_observation_count(newcount)

    def instance_changed(self):
        if self.observe:
            self.updated_state(TlvEncoder.get_multi_resource(self))
        if self.notify_cb:
            self.notify_cb()

    def notify(self, notify_cb):
        self.notify_cb = notify_cb

    def build_site(self, site):
        """Add CoAP resource link to the base resource and its instances"""
        log.debug(f'{self.obj_id}/{self.obj_inst}/{self.res_id} -> {self.desc}')
        site.add_resource((str(self.obj_id), str(self.obj_inst), str(self.res_id)), self)
        for res_id, res in self.instances.items():
            res.build_site(site)

    async def render_get(self, request):
        log.debug(f'{self.desc}: GET request format={request.opt.content_format} observe={request.opt.observe}')
        return TlvEncoder.get_multi_resource(self)

    async def render_post(self, request):
        log.debug(f'{self.desc}: POST request format={request.opt.content_format}')
        return TlvDecoder.update_multi_resource(request, self)

    async def render_put(self, request):
        log.debug(f'{self.desc}: PUT request format={request.opt.content_format}')
        return TlvDecoder.update_multi_resource(request, self)

class LwM2MExecutableResource(LwM2MBase):
    """LwM2M resource that executes a callback function"""

    def __init__(self, obj_id, obj_inst, res_id, exec_cb):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.res_id = res_id
        self.exec_cb = exec_cb
        super(LwM2MExecutableResource, self).__init__(f'Obj_{obj_id}_{obj_inst}_Res_{res_id}')

    def get_id(self):
        return self.res_id

    def notify(self, notify_cb):
        pass

    def build_site(self, site):
        log.debug(f'{self.obj_id}/{self.obj_inst}/{self.res_id} -> {self.desc}')
        site.add_resource((str(self.obj_id), str(self.obj_inst), str(self.res_id)), self)

    async def render_post(self, request):
        self.exec_cb()
        return Message(code=Code.CHANGED)
