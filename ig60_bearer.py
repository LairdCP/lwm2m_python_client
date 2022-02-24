"""Implementation of Bearer Selection (Object 13) for IG60
"""

import asyncio
import threading
import logging

from lwm2m.object import LwM2MObjectInst
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MMultiResource
from lwm2m.bearer import *

log = logging.getLogger('ig60bearer')

# Network Manager interface prefixes
NM_IFACE_ETHERNET = 'eth'
NM_IFACE_WLAN = 'wlan'
NM_IFACE_LTE = 'usb'

class IG60DefaultBearerResource(LwM2MMultiResource):
    """Implementation of Default Bearer resource for IG60"""

    def __init__(self, set_bearer_cb):
        super(IG60DefaultBearerResource, self).__init__(LWM2M_BEARER_OBJECT,
            LWM2M_BEARER_INSTANCE, LWM2M_BEARER_RESOURCE_PREFERRED_BEARER)
        self.set_bearer_cb = set_bearer_cb

    def update(self, instances):
        super(IG60DefaultBearerResource, self).update(instances)
        self.set_bearer_cb(instances)

    def get_interfaces(self):
        """Get ordered list of interfaces names from bearer resources"""
        interfaces = []
        # Sort bearer list by resource instance id
        for res_inst, bearer in sorted(self.instances.items()):
            if bearer.value == LWM2M_BEARER_AUTO:
                # If 'auto' is specified in any instance,
                # return a list of all interfaces:
                return [NM_IFACE_ETHERNET, NM_IFACE_WLAN, NM_IFACE_LTE]
            elif bearer.value == LWM2M_BEARER_ETHERNET:
                interfaces.append(NM_IFACE_ETHERNET)
            elif bearer.value == LWM2M_BEARER_WLAN:
                interfaces.append(NM_IFACE_WLAN)
            elif bearer.value == LWM2M_BEARER_3GPP_LTE:
                interfaces.append(NM_IFACE_LTE)
        return interfaces

class IG60BearerObject(LwM2MObjectInst):
    """Object 13 (Bearer Selection) implementation for IG60
    """

    def __init__(self, set_bearer_cb):
        super(IG60BearerObject, self).__init__(LWM2M_BEARER_OBJECT, LWM2M_BEARER_INSTANCE)
        self.default_bearer_res = IG60DefaultBearerResource(set_bearer_cb)
        self.default_bearer_res.add_res_inst(LwM2MResourceInst(LWM2M_BEARER_OBJECT,
            LWM2M_BEARER_INSTANCE, LWM2M_BEARER_RESOURCE_PREFERRED_BEARER, 0,
            LWM2M_BEARER_AUTO))
        self.add_resource(self.default_bearer_res)

    def get_interfaces(self):
        return self.default_bearer_res.get_interfaces()

