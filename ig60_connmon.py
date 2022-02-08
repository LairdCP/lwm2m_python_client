"""Implementation of Connectivity Monitoring (Object 4) for IG60
"""

import asyncio
import threading
import logging

from lwm2m.object import LwM2MObjectInst
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MMultiResource
from lwm2m.connmon import *

log = logging.getLogger('ig60connmon')

# Ofono Property names
OFONO_PROP_RSSI = 'Strength'
OFONO_PROP_CELLID = 'CellId'
OFONO_PROP_MNC = 'MobileNetworkCode'
OFONO_PROP_MCC = 'MobileCountryCode'
OFONO_PROP_LAC = 'LocationAreaCode'
OFONO_PROP_APN = 'AccessPointName'

# Network Interface Prefixes
IFACE_ETH = 'eth'
IFACE_WLAN = 'wlan'
IFACE_LTE = 'usb'

class IG60CurrentBearerResource(LwM2MResourceValue):
    """Resource that reports the current network bearer based on bind address"""

    def __init__(self, ig60net, addr):
        super(IG60CurrentBearerResource, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, LWM2M_CONNMON_RESOURCE_NET_BEARER, 0)
        self.ig60net = ig60net
        self.addr = addr

    def get_value(self):
        iface = self.ig60net.find_iface_by_addr(self.addr)
        if iface.startswith(IFACE_LTE):
            # Gemalto PLS62-W is FDD only
            return LWM2M_CONNMON_BEARER_LTE_FDD
        elif iface.startswith(IFACE_WLAN):
            return LWM2M_CONNMON_BEARER_WLAN
        else:
            return LWM2M_CONNMON_BEARER_ETHERNET

class IG60AvailableBearersResource(LwM2MMultiResource):
    """Resource that reports all available network bearers"""

    def __init__(self, ig60net):
        super(IG60AvailableBearersResource, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, LWM2M_CONNMON_RESOURCE_AVAIL_NET_BEARER)
        self.ig60net = ig60net

    def get_instances(self):
        """Build multi-resource list based on available connections"""
        self.instances = {}
        have_lte = False
        have_wlan = False
        have_eth = False
        res_inst = 0
        conns = self.ig60net.get_available_connections()
        for c in conns:
            if c[0].startswith(IFACE_LTE) and not have_lte:
                have_lte = True
                self.add_res_inst(LwM2MResourceInst(self.obj_id, self.obj_inst, self.res_id, res_inst, LWM2M_CONNMON_BEARER_LTE_FDD))
                res_inst = res_inst + 1
            elif c[0].startswith(IFACE_WLAN) and not have_wlan:
                have_wlan = True
                self.add_res_inst(LwM2MResourceInst(self.obj_id, self.obj_inst, self.res_id, res_inst, LWM2M_CONNMON_BEARER_WLAN))
                res_inst = res_inst + 1
            elif c[0].startswith(IFACE_ETH) and not have_eth:
                have_eth = True
                self.add_res_inst(LwM2MResourceInst(self.obj_id, self.obj_inst, self.res_id, res_inst, LWM2M_CONNMON_BEARER_ETHERNET))
                res_inst = res_inst + 1
        return self.instances

class IG60OfonoRSSIResource(LwM2MResourceValue):
    """Resource that reports Ofono RSSI"""

    def __init__(self, ig60net):
        super(IG60OfonoRSSIResource, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, LWM2M_CONNMON_RESOURCE_RSSI, 0)
        self.ig60net = ig60net

    def get_value(self):
        strength = self.ig60net.get_ofono_net_prop_int(OFONO_PROP_RSSI)
        # Ofono reports "strength" as percent 0-100, which is derived
        # from the Gemalto AT+CSQ response in the range 0-5, where
        # 0:-112dBm ... 5:-51 dBm; convert back to dBm:
        if strength is not None:
            return int(-112 + ((strength / 20) * 15))
        else:
            return None

class IG60OfonoNetPropertyIntResource(LwM2MResourceValue):
    """Resource that reports a value based on the current value of an
       Ofono network property (integer)
    """

    def __init__(self, resid, ig60net, prop):
        super(IG60OfonoNetPropertyIntResource, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, resid, 0)
        self.ig60net = ig60net
        self.prop = prop

    def get_value(self):
        return self.ig60net.get_ofono_net_prop_int(self.prop)

class IG60OfonoConnPropertyStrResource(LwM2MResourceValue):
    """Resource that reports a value based on the current value of an
       Ofono connection property (string)
    """

    def __init__(self, resid, ig60net, prop):
        super(IG60OfonoConnPropertyStrResource, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, resid, '')
        self.ig60net = ig60net
        self.prop = prop

    def get_value(self):
        return self.ig60net.get_ofono_conn_prop_str(self.prop)

class IG60ConnectionMonitor(LwM2MObjectInst):
    """Object 4 (Connection Monitoring) implementation for IG60
    """

    def __init__(self, ig60net, addr):
        super(IG60ConnectionMonitor, self).__init__(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE)
        self.add_resource(IG60CurrentBearerResource(ig60net, addr))
        self.add_resource(IG60AvailableBearersResource(ig60net))
        self.add_resource(LwM2MResourceValue(LWM2M_CONNMON_OBJECT, LWM2M_CONNMON_INSTANCE, LWM2M_CONNMON_RESOURCE_IP_ADDRESSES, addr))
        self.add_resource(IG60OfonoRSSIResource(ig60net))
        self.add_resource(IG60OfonoNetPropertyIntResource(LWM2M_CONNMON_RESOURCE_CELLID, ig60net, OFONO_PROP_CELLID))
        self.add_resource(IG60OfonoNetPropertyIntResource(LWM2M_CONNMON_RESOURCE_SMNC,  ig60net, OFONO_PROP_MNC))
        self.add_resource(IG60OfonoNetPropertyIntResource(LWM2M_CONNMON_RESOURCE_SMCC,  ig60net, OFONO_PROP_MCC))
        self.add_resource(IG60OfonoNetPropertyIntResource(LWM2M_CONNMON_RESOURCE_LAC,  ig60net, OFONO_PROP_LAC))
        self.add_resource(IG60OfonoConnPropertyStrResource(LWM2M_CONNMON_RESOURCE_APN,  ig60net, OFONO_PROP_APN))
