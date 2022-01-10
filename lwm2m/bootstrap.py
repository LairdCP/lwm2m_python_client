"""Implementation of LwM2M bootstrap client interface

"""

import logging
import asyncio

from aiocoap import error, resource
from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.protocol import Context
from aiocoap.resource import ObservableResource, Site

from .base import LwM2MBase
from .object import LwM2MObjectInst, LwM2MBaseObject
from .resource import LwM2MResourceValue

log = logging.getLogger('bootstrap')

class LwM2MSecurityObject(LwM2MObjectInst):
    """Implementation of Object 0 (Security) instance"""

    def __init__(self, obj_inst):
        super(LwM2MSecurityObject, self).__init__(0, obj_inst)
        # Create default resources
        self.add_resource(LwM2MResourceValue(0, obj_inst, 0, '')) # 0: LwM2M Server URI
        self.add_resource(LwM2MResourceValue(0, obj_inst, 1, False)) # 1: Bootstrap-Server
        self.add_resource(LwM2MResourceValue(0, obj_inst, 2, 0)) # 2: Security Mode
        self.add_resource(LwM2MResourceValue(0, obj_inst, 3, b'')) # 3: Public Key or Identity
        self.add_resource(LwM2MResourceValue(0, obj_inst, 4, b'')) # 4: Server Public Key or Identity
        self.add_resource(LwM2MResourceValue(0, obj_inst, 5, b'')) # 5: Secret Key

class LwM2MSecurityBaseObject(LwM2MBaseObject):
    """Base class for managing instances of Security (Object 0)"""

    def __init__(self):
        super(LwM2MSecurityBaseObject, self).__init__(0)

    async def render_delete(self, request):
        log.debug(f'{self.desc}: DELETE')
        # Create default instance (/0/1) to receive bootstrap-write (PUT)
        self.add_obj_inst(LwM2MSecurityObject(1))
        self.notify_site_changed()
        return Message(code=Code.DELETED)

    def get_server_uri(self):
        """Convenience method to read the L2M2M server URI from instance 1, resource 0"""
        inst1 = self.instances.get(1)
        if inst1:
            return inst1.resources[0].get_value()

class LwM2MServerObject(LwM2MObjectInst):
    """Implementation of Object 1 (Server) instance"""

    def __init__(self, obj_inst):
        super(LwM2MServerObject, self).__init__(1, obj_inst)
        # Create default resources
        self.add_resource(LwM2MResourceValue(1, obj_inst, 0, 0)) # 0: Short Server ID
        self.add_resource(LwM2MResourceValue(1, obj_inst, 1, 0)) # 1: Lifetime

class LwM2MServerBaseObject(LwM2MBaseObject):
    """Base class for managing instances of Security (Object 0)"""

    def __init__(self):
        super(LwM2MServerBaseObject, self).__init__(1)

    async def render_delete(self, request):
        log.debug(f'{self.desc}: DELETE')
        # Create default instance (/1/0) to receive bootstrap-write (PUT)
        self.add_obj_inst(LwM2MServerObject(0))
        self.notify_site_changed()
        return Message(code=Code.DELETED)
