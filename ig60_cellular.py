"""Implementation of Cellular Connectivity (Object 10) and APN (Object 11) for IG60
"""

import asyncio
import threading
import logging

from lwm2m.object import LwM2MObjectInst
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MMultiResource
from lwm2m.cellular import *
from lwm2m.tlv import ObjLink

log = logging.getLogger('ig60cellular')

# Ofono Property names
OFONO_PROP_DEFAULT_APN = 'DefaultAccessPointName'
OFONO_PROP_AUTH_METHOD = 'AuthenticationMethod'
OFONO_PROP_USERNAME = 'Username'
OFONO_PROP_PASSWORD = 'Password'
OFONO_PROP_PROTOCOL = 'Protocol'

OFONO_PROP_SETTINGS = 'Settings'

OFONO_SETTING_ADDRESS = 'Address'
OFONO_SETTING_GATEWAY = 'Gateway'
OFONO_SETTING_NETMASK = 'Netmask'
OFONO_SETTING_DNS = 'DomainNameServers'

OFONO_AUTH_TYPE_NONE = 'none'
OFONO_AUTH_TYPE_CHAP = 'chap'
OFONO_AUTH_TYPE_PAP = 'pap'

OFONO_PROTOCOL_IP = 'ip'
OFONO_PROTOCOL_IPV6 = 'ipv6'
OFONO_PROTOCOL_DUAL = 'dual'

ACTIVATED_APN_PROFILE_RESOURCE_INSTANCE = 0

PRIMARY_DNS_INDEX = 0
SECONDARY_DNS_INDEX = 1

class IG60ActivatedProfilesResource(LwM2MMultiResource):
    """Resource that reports all activated APN profiles

       Since the IG60 Ofono interface only supports a single LTE
       connection (via the configured default EPS bearer), this
       resource will only report the single APN object instance
       when the connection is active
    """

    def __init__(self, ig60net):
        super(IG60ActivatedProfilesResource, self).__init__(LWM2M_CELLULAR_CONN_OBJECT, LWM2M_CELLULAR_CONN_INSTANCE, LWM2M_CELLULAR_RESOURCE_ACTIVATED_PROFILES)
        self.ig60net = ig60net

    def get_instances(self):
        """Build multi-resource list when connection is active"""
        self.instances = {}
        # Check if connection properties exist -> connection is active
        if len(self.ig60net.get_ofono_conn_props()) > 0:
            # Resource instance is an ObjLink to the APN connection
            self.add_res_inst(LwM2MResourceInst(self.obj_id, self.obj_inst, self.res_id, ACTIVATED_APN_PROFILE_RESOURCE_INSTANCE,
                ObjLink(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE)))
        return self.instances

class IG60OfonoAPNResource(LwM2MResourceValue):
    """Resource that gets/sets the Ofono LTE APN"""

    def __init__(self, ig60net):
        super(IG60OfonoAPNResource, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, LWM2M_APN_PROFILE_RESOURCE_APN, '', self.set_apn_cb)
        self.ig60net = ig60net

    def get_value(self):
        val = self.ig60net.get_ofono_lte_prop_str(OFONO_PROP_DEFAULT_APN, '')
        log.debug(f'Ofono APN property {OFONO_PROP_DEFAULT_APN} = {val}')
        return val

    def set_apn_cb(self, value):
        if not self.ig60net.set_ofono_lte_prop(OFONO_PROP_DEFAULT_APN, value):
            # Encoder will catch exception and report 'BAD VALUE'
            raise Exception('Cannot set APN resource')

class IG60OfonoAuthTypeResource(LwM2MResourceValue):
    """Resource that gets/sets the LTE authentication type"""

    def __init__(self, ig60net):
        super(IG60OfonoAuthTypeResource, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, LWM2M_APN_PROFILE_RESOURCE_AUTH_TYPE, LWM2M_APN_AUTH_TYPE_NONE,
            self.set_auth_cb)
        self.ig60net = ig60net

    def get_value(self):
        # Decode Ofono Auth type to LwM2M enumeration
        ofono_auth_type = self.ig60net.get_ofono_lte_prop_str(OFONO_PROP_AUTH_METHOD, '')
        if ofono_auth_type == OFONO_AUTH_TYPE_NONE:
            value = LWM2M_APN_AUTH_TYPE_NONE
        elif ofono_auth_type == OFONO_AUTH_TYPE_CHAP:
            value = LWM2M_APN_AUTH_TYPE_CHAP
        elif ofono_auth_type == OFONO_AUTH_TYPE_PAP:
            value = LWM2M_APN_AUTH_TYPE_PAP
        else:
            value = None # Value will not be encoded
        self.value = value
        return value

    def set_auth_cb(self, value):
        # Decode LwM2M enumeration to Ofono auth type
        if value == LWM2M_APN_AUTH_TYPE_NONE:
            ofono_value = OFONO_AUTH_TYPE_NONE
        elif value == LWM2M_APN_AUTH_TYPE_CHAP:
            ofono_value = OFONO_AUTH_TYPE_CHAP
        elif value == LWM2M_APN_AUTH_TYPE_PAP:
            ofono_value = OFONO_AUTH_TYPE_PAP
        else:
            # Encoder will catch exception and report 'BAD VALUE'
            raise Exception('Invalid LTE auth type')
        if not self.ig60net.set_ofono_lte_prop(OFONO_PROP_AUTH_METHOD, ofono_value):
            raise Exception('Cannot set Ofono LTE auth type')

class IG60OfonoPDNTypeResource(LwM2MResourceValue):
    """Resource that gets/sets the LTE PDN type"""

    def __init__(self, ig60net):
        super(IG60OfonoPDNTypeResource, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, LWM2M_APN_PROFILE_RESOURCE_PDN_TYPE, LWM2M_APN_PDN_TYPE_NON_IP,
            self.set_pdn_cb)
        self.ig60net = ig60net

    def get_value(self):
        # Decode Ofono protocol type to LwM2M PDN type enumeration
        ofono_protocol = self.ig60net.get_ofono_lte_prop_str(OFONO_PROP_PROTOCOL, '')
        if ofono_protocol == OFONO_PROTOCOL_IP:
            value = LWM2M_APN_PDN_TYPE_IPV4
        elif ofono_protocol == OFONO_PROTOCOL_IPV6:
            value = LWM2M_APN_PDN_TYPE_IPV6
        elif ofono_protocol == OFONO_PROTOCOL_DUAL:
            value = LWM2M_APN_PDN_TYPE_IPV4V6
        else:
            value = None # Value will not be encoded
        self.value = value
        return value

    def set_pdn_cb(self, value):
        if value == LWM2M_APN_PDN_TYPE_IPV4:
            ofono_value = OFONO_PROTOCOL_IP
        elif value == OFONO_PROTOCOL_IPV6:
            ofono_value = LWM2M_APN_PDN_TYPE_IPV6
        elif value == LWM2M_APN_PDN_TYPE_IPV4V6:
            ofono_value = LWM2M_APN_PDN_TYPE_IPV4V6
        else:
            # Encoder will catch exception and report 'BAD VALUE'
            raise Exception('Invalid PDN type')
        if not self.ig60net.set_ofono_lte_prop(OFONO_PROP_PROTOCOL, ofono_value):
            raise Exception('Cannot set Ofono LTE protocol')

class IG60OfonoLTEPropertyStrResource(LwM2MResourceValue):
    """Resource that gets/sets an Ofono LTE property (string)"""

    def __init__(self, resid, ig60net, prop):
        super(IG60OfonoLTEPropertyStrResource, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, resid, '', self.set_value_cb)
        self.ig60net = ig60net
        self.prop = prop

    def get_value(self):
        self.value = self.ig60net.get_ofono_lte_prop_str(self.prop)
        return self.value

    def set_value_cb(self, value):
        if not self.ig60net.set_ofono_lte_prop(self.prop, value):
            raise Exception(f'Cannot set Ofono LTE property {self.prop}')

class IG60OfonoConnSettingStrResource(LwM2MResourceValue):
    """Resource that reports a value based on the current value of an
       Ofono connection setting (string) or list of strings
    """

    def __init__(self, resid, ig60net, setting, index = None):
        super(IG60OfonoConnSettingStrResource, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, resid, '')
        self.ig60net = ig60net
        self.setting = setting
        self.index = index

    def get_value(self):
        conn_props = self.ig60net.get_ofono_conn_props()
        if conn_props and OFONO_PROP_SETTINGS in conn_props:
            if self.setting in conn_props[OFONO_PROP_SETTINGS]:
                if self.index is None:
                    return str(conn_props[OFONO_PROP_SETTINGS][self.setting])
                elif len(conn_props[OFONO_PROP_SETTINGS][self.setting]) > self.index:
                    return str(conn_props[OFONO_PROP_SETTINGS][self.setting][self.index])

        return None # Ignored by encoder

class IG60Cellular(LwM2MObjectInst):
    """Object 10 (Cellular Connectivity) implementation for IG60
    """
    def __init__(self, ig60net):
        super(IG60Cellular, self).__init__(LWM2M_CELLULAR_CONN_OBJECT, LWM2M_CELLULAR_CONN_INSTANCE)
        self.add_resource(IG60ActivatedProfilesResource(ig60net))

class IG60APNProfile(LwM2MObjectInst):
    """Object 11 (APN Profile) implementation for IG60
    """

    def __init__(self, ig60net):
        super(IG60APNProfile, self).__init__(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE)
        self.add_resource(LwM2MResourceValue(LWM2M_APN_PROFILE_OBJECT, LWM2M_APN_PROFILE_INSTANCE, LWM2M_APN_PROFILE_RESOURCE_NAME, ''))
        self.add_resource(IG60OfonoAPNResource(ig60net))
        self.add_resource(IG60OfonoAuthTypeResource(ig60net))
        self.add_resource(IG60OfonoLTEPropertyStrResource(LWM2M_APN_PROFILE_RESOURCE_USERNAME, ig60net, OFONO_PROP_USERNAME))
        self.add_resource(IG60OfonoLTEPropertyStrResource(LWM2M_APN_PROFILE_RESOURCE_SECRET, ig60net, OFONO_PROP_PASSWORD))
        self.add_resource(IG60OfonoPDNTypeResource(ig60net))
        self.add_resource(IG60OfonoConnSettingStrResource(LWM2M_APN_PROFILE_RESOURCE_IP_ADDRESS,  ig60net, OFONO_SETTING_ADDRESS))
        self.add_resource(IG60OfonoConnSettingStrResource(LWM2M_APN_PROFILE_RESOURCE_GATEWAY,  ig60net, OFONO_SETTING_GATEWAY))
        self.add_resource(IG60OfonoConnSettingStrResource(LWM2M_APN_PROFILE_RESOURCE_SUBNET_MASK,  ig60net, OFONO_SETTING_NETMASK))
        self.add_resource(IG60OfonoConnSettingStrResource(LWM2M_APN_PROFILE_RESOURCE_PRIMARY_DNS_ADDR,  ig60net, OFONO_SETTING_DNS, PRIMARY_DNS_INDEX))
        self.add_resource(IG60OfonoConnSettingStrResource(LWM2M_APN_PROFILE_RESOURCE_SECONDARY_DNS_ADDR,  ig60net, OFONO_SETTING_DNS, SECONDARY_DNS_INDEX))
