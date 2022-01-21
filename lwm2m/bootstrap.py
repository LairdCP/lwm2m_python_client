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

# LwM2M Object 0 (Security) resource and instance definitions
LWM2M_SECURITY_OBJECT = 0

LWM2M_SECURITY_RESOURCE_SERVER_URI = 0
LWM2M_SECURITY_RESOURCE_BOOTSTRAP_SERVER = 1
LWM2M_SECURITY_RESOURCE_SECURITY_MODE = 2
LWM2M_SECURITY_RESOURCE_PUBLIC_KEY = 3
LWM2M_SECURITY_RESOURCE_SERVER_PUBLIC_KEY = 4
LWM2M_SECURITY_RESOURCE_SECRET_KEY = 5

LWM2M_SECURITY_BOOTSTRAP_INSTANCE = 0
LWM2M_SECURITY_SERVER_INSTANCE = 1

# LwM2M Object 1 (Server) resource and instance definitions
LWM2M_SERVER_OBJECT = 1

LWM2M_SERVER_RESOURCE_SHORT_SERVER_ID = 0
LWM2M_SERVER_RESOURCE_LIFETIME = 1

LWM2M_SERVER_INSTANCE = 0

class LwM2MSecurityObject(LwM2MObjectInst):
    """Implementation of Object 0 (Security) instance"""

    def __init__(self, obj_inst):
        super(LwM2MSecurityObject, self).__init__(LWM2M_SECURITY_OBJECT, obj_inst)
        # Create default resources
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_SERVER_URI, '')) # 0: LwM2M Server URI
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_BOOTSTRAP_SERVER, False)) # 1: Bootstrap-Server
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_SECURITY_MODE, 0)) # 2: Security Mode
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_PUBLIC_KEY, b'')) # 3: Public Key or Identity
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_SERVER_PUBLIC_KEY, b'')) # 4: Server Public Key or Identity
        self.add_resource(LwM2MResourceValue(LWM2M_SECURITY_OBJECT, obj_inst, LWM2M_SECURITY_RESOURCE_SECRET_KEY, b'')) # 5: Secret Key

class LwM2MSecurityBaseObject(LwM2MBaseObject):
    """Base class for managing instances of Security (Object 0)"""

    def __init__(self):
        super(LwM2MSecurityBaseObject, self).__init__(LWM2M_SECURITY_OBJECT)

    async def render_delete(self, request):
        log.debug(f'{self.desc}: DELETE')
        # Create default instance (/0/1) to receive bootstrap-write (PUT)
        self.add_obj_inst(LwM2MSecurityObject(LWM2M_SECURITY_SERVER_INSTANCE))
        self.notify_site_changed()
        return Message(code=Code.DELETED)

    def get_server_uri(self):
        """Convenience method to read the L2M2M server URI"""
        inst1 = self.instances.get(LWM2M_SECURITY_SERVER_INSTANCE)
        if inst1:
            return inst1.resources[LWM2M_SECURITY_RESOURCE_SERVER_URI].get_value()

    def get_psk(self):
        """Convenience method to read the PSK"""
        inst1 = self.instances.get(LWM2M_SECURITY_SERVER_INSTANCE)
        if inst1:
            return inst1.resources[LWM2M_SECURITY_RESOURCE_SECRET_KEY].get_value()

class LwM2MServerObject(LwM2MObjectInst):
    """Implementation of Object 1 (Server) instance"""

    def __init__(self, obj_inst):
        super(LwM2MServerObject, self).__init__(LWM2M_SERVER_OBJECT, obj_inst)
        # Create default resources
        self.add_resource(LwM2MResourceValue(1, obj_inst, LWM2M_SERVER_RESOURCE_SHORT_SERVER_ID, 0)) # 0: Short Server ID
        self.add_resource(LwM2MResourceValue(1, obj_inst, LWM2M_SERVER_RESOURCE_LIFETIME, 0)) # 1: Lifetime

class LwM2MServerBaseObject(LwM2MBaseObject):
    """Base class for managing instances of Security (Object 0)"""

    def __init__(self):
        super(LwM2MServerBaseObject, self).__init__(LWM2M_SERVER_OBJECT)

    async def render_delete(self, request):
        log.debug(f'{self.desc}: DELETE')
        # Create default instance (/1/0) to receive bootstrap-write (PUT)
        self.add_obj_inst(LwM2MServerObject(LWM2M_SERVER_INSTANCE))
        self.notify_site_changed()
        return Message(code=Code.DELETED)

    def get_lifetime(self):
        """Convenience method to read the client lifetime"""
        return self.instances.get(LWM2M_SERVER_INSTANCE).resources[LWM2M_SERVER_RESOURCE_LIFETIME].get_value()
