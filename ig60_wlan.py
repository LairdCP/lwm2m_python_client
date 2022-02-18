"""Implementation of WLAN Connectivity (Object 12) for IG60
"""

import asyncio
import threading
import logging
import re
import dbus

from aiocoap.message import Message
from aiocoap.numbers.codes import Code

from lwm2m.object import LwM2MObjectInst, LwM2MBaseObject
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MMultiResource
from lwm2m.wlan import *
from lwm2m.tlv import TlvEncoder, TlvDecoder

log = logging.getLogger('ig60wlan')

IG60_WLAN_INTERFACE = 'wlan0'

# Network Manager connection settings
NM_SETTINGS_CONNECTION = 'connection'
NM_SETTINGS_ID = 'id'
NM_SETTINGS_IFACE_NAME = 'interface-name'
NM_SETTINGS_WIRELESS = '802-11-wireless'
NM_SETTINGS_WIRELESS_SECURITY = '802-11-wireless-security'
NM_SETTINGS_TYPE = 'type'
NM_SETTINGS_AUTOCONNECT = 'autoconnect'
NM_SETTINGS_AUTOCONNECT_PRIORITY = 'autoconnect-priority'
NM_SETTINGS_AUTOCONNECT_RETRIES = 'autoconnect-retries'
NM_SETTINGS_AUTH_RETRIES = 'auth-retries'
NM_SETTINGS_MODE = 'mode'
NM_SETTINGS_MODE_INFRASTRUCTURE = 'infrastructure'
NM_SETTINGS_SSID = 'ssid'
NM_SETTINGS_HIDDEN = 'hidden'
NM_SETTINGS_KEY_MGMT = 'key-mgmt'
NM_SETTINGS_WPA_PSK = 'wpa-psk'
NM_SETTINGS_PSK = 'psk'
NM_SETTINGS_CHANNEL = 'channel'

NM_KEY_MGMT_WPA_PSK = 'wpa-psk'

CONNECTION_DEFAULT_PRIORITY = 0
CONNECTION_DEFAULT_RETRIES = 0

NM_CONN_PREFIX = 'lwm2m_conn_'

class IG60WLANProfileStatusResource(LwM2MResourceValue):
    """Resource that reports the WLAN profile status"""

    def __init__(self, obj_inst, ig60net):
        super(IG60WLANProfileStatusResource, self).__init__(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_STATUS, LWM2M_WLAN_RESOURCE_STATUS_DISABLED)
        self.ig60net = ig60net
        self.nm_connection_id = NM_CONN_PREFIX + str(obj_inst)

    def get_value(self):
        settings = self.ig60net.get_nm_conn_settings(self.nm_connection_id)
        # Oddly, NM does not populate 'autoconnect' when it is set to 'True'?
        enabled = bool(settings[NM_SETTINGS_CONNECTION].get(NM_SETTINGS_AUTOCONNECT, True))
        if enabled:
            conns = self.ig60net.get_available_connections()
            for c in conns:
                if c[1] == settings[NM_SETTINGS_CONNECTION][NM_SETTINGS_ID]:
                    return LWM2M_WLAN_RESOURCE_STATUS_UP
            # LwM2M spec does not specify this, but this is the only
            # other option if the connection is not 'up' or 'disabled':
            return LWM2M_WLAN_RESOURCE_STATUS_ERROR
        else:
            return LWM2M_WLAN_RESOURCE_STATUS_DISABLED

class IG60WLANProfile(LwM2MObjectInst):
    """Object 12 (WLAN Connectivity) implementation for IG60

       This object implements the LwM2M resources that encapsulate a
       Network Manager wireless connection.
    """

    def __init__(self, obj_inst, ig60net, delete_cb):
        super(IG60WLANProfile, self).__init__(LWM2M_WLAN_OBJECT, obj_inst)
        self.ig60net = ig60net
        self.delete_cb = delete_cb
        # Initialize default WLAN connection settings
        self.res_interface = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_IFNAME, IG60_WLAN_INTERFACE, self.resource_changed)
        self.add_resource(self.res_interface)
        self.res_enabled = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_ENABLE, False, self.resource_changed)
        self.add_resource(self.res_enabled)
        self.add_resource(IG60WLANProfileStatusResource(self.obj_inst, self.ig60net))
        self.add_resource(LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_BSSID, ig60net.get_hw_addr(IG60_WLAN_INTERFACE)))
        self.res_ssid = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_SSID, '', self.resource_changed)
        self.add_resource(self.res_ssid)
        self.res_mode = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_MODE, LWM2M_WLAN_RESOURCE_MODE_CLIENT, self.resource_changed)
        self.add_resource(self.res_mode)
        self.res_channel = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_CHANNEL, 0, self.resource_changed)
        self.add_resource(self.res_channel)
        self.add_resource(LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_STANDARD, LWM2M_WLAN_RESOURCE_STANDARD_80211_AC))
        self.res_auth_mode = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_AUTH_MODE, LWM2M_WLAN_RESOURCE_AUTH_MODE_OPEN, self.resource_changed)
        self.add_resource(self.res_auth_mode)
        self.res_wpa_psk = LwM2MResourceValue(LWM2M_WLAN_OBJECT, obj_inst, LWM2M_WLAN_RESOURCE_WPA_KEY_PHRASE, '', self.resource_changed)
        self.add_resource(self.res_wpa_psk)
        self.nm_connection_id = NM_CONN_PREFIX + str(obj_inst)
        self.created = False

    def init_from_nm_connection(self):
        """Initialize WLAN LwM2M connection resources from a Network Manager connection"""
        settings = self.ig60net.get_nm_conn_settings(self.nm_connection_id)
        if settings:
            self.res_interface.value = str(settings[NM_SETTINGS_CONNECTION].get(NM_SETTINGS_IFACE_NAME))
            # Oddly, NM does not populate 'autoconnect' when it is set to 'True'?
            self.res_enabled.value = bool(settings[NM_SETTINGS_CONNECTION].get(NM_SETTINGS_AUTOCONNECT, True))
            self.res_ssid.value = bytearray(settings[NM_SETTINGS_WIRELESS][NM_SETTINGS_SSID]).decode()
            self.res_channel.value = int(settings[NM_SETTINGS_WIRELESS].get(NM_SETTINGS_CHANNEL, 0))
            # Support only WPA-PSK or Open, since Object 12 does not have
            # fields for EAP username & password
            if (NM_SETTINGS_WIRELESS_SECURITY in settings and
                settings[NM_SETTINGS_WIRELESS_SECURITY].get(NM_SETTINGS_KEY_MGMT) == NM_KEY_MGMT_WPA_PSK):
                    self.res_auth_mode.value = LWM2M_WLAN_RESOURCE_AUTH_MODE_PSK
                    self.res_wpa_psk.value = str(settings[NM_SETTINGS_WIRELESS_SECURITY][NM_SETTINGS_PSK])
            else:
                self.res_auth_mode.value = LWM2M_WLAN_RESOURCE_AUTH_MODE_OPEN
            self.created = True
        else:
            log.warn(f'Failed to load settings for connection {self.nm_connection_id}')

    def get_nm_connection_settings(self):
        """Get the NetworkManager WLAN connection settings from the LwM2M resources"""
        settings = {
            NM_SETTINGS_CONNECTION : {
                NM_SETTINGS_TYPE : NM_SETTINGS_WIRELESS,
                NM_SETTINGS_ID : self.nm_connection_id,
                NM_SETTINGS_AUTOCONNECT : self.res_enabled.value,
                NM_SETTINGS_AUTOCONNECT_PRIORITY : CONNECTION_DEFAULT_PRIORITY,
                NM_SETTINGS_AUTOCONNECT_RETRIES : CONNECTION_DEFAULT_RETRIES,
                NM_SETTINGS_AUTH_RETRIES : CONNECTION_DEFAULT_RETRIES,
                NM_SETTINGS_IFACE_NAME : self.res_interface.value
            },
            NM_SETTINGS_WIRELESS : {
                NM_SETTINGS_MODE : NM_SETTINGS_MODE_INFRASTRUCTURE,
                NM_SETTINGS_SSID : dbus.ByteArray(self.res_ssid.value.encode()),
                NM_SETTINGS_HIDDEN : True,
                NM_SETTINGS_CHANNEL : self.res_channel.value
            }
        }
        if self.res_wpa_psk.value and self.res_auth_mode.value == LWM2M_WLAN_RESOURCE_AUTH_MODE_PSK:
            settings[NM_SETTINGS_WIRELESS_SECURITY] = {
                NM_SETTINGS_KEY_MGMT : NM_SETTINGS_WPA_PSK,
                NM_SETTINGS_PSK : self.res_wpa_psk.value
            }
        return settings

    def resource_changed(self, value):
        """Callback when one or more resource values have been updated"""
        # Only update once the profile has been fully created
        if self.created:
            self.ig60net.add_or_modify_wlan_connection(self.get_nm_connection_settings())

    async def render_delete(self, request):
        log.info(f'Deleting WLAN object {self.obj_inst}')
        self.ig60net.delete_wlan_connection(self.nm_connection_id)
        self.delete_cb(self.obj_inst)
        return Message(code=Code.DELETED)

class IG60WLANProfileBase(LwM2MBaseObject):
    """Base object for LwM2M WLAN Profile (Object 12)"""

    def __init__(self, ig60net):
        super(IG60WLANProfileBase, self).__init__(LWM2M_WLAN_OBJECT)
        self.ig60net = ig60net
        # Populate object instances from NM WLAN connections
        wlan_conns = ig60net.get_connections_by_iface(IG60_WLAN_INTERFACE)
        for conn_id in wlan_conns:
            if conn_id.startswith(NM_CONN_PREFIX):
                obj_inst = int(re.sub(NM_CONN_PREFIX, '', conn_id))
                log.info(f'Initializing WLAN object inst {obj_inst}')
                obj = IG60WLANProfile(obj_inst, self.ig60net, self.on_delete)
                obj.init_from_nm_connection()
                self.add_obj_inst(obj)

    async def render_post(self, request):
        """Create a new (default) WLAN connection object"""
        inst_id = 0
        # Find next highest instance id
        for obj_inst, obj in self.instances.items():
            if obj_inst >= inst_id:
                inst_id = obj_inst + 1
        log.info('Creating WLAN object instance {inst_id}')
        obj = IG60WLANProfile(inst_id, self.ig60net, self.on_delete)
        if request.payload and len(request.payload) > 0:
            response = TlvDecoder.update_object(request, obj, Code.CREATED)
        else:
            response = Message(Code.CREATED)
        if response.code == Code.CREATED:
            self.add_obj_inst(obj)
            self.notify_site_changed()
            obj.created = True
            obj.resource_changed(None)
        return response

    def on_delete(self, obj_inst):
        """Callback to delete object instance"""
        log.info(f'Deleting WLAN object instance {obj_inst}')
        self.remove_obj_inst(obj_inst)
