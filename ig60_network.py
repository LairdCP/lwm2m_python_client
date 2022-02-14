"""IG60 Network function helper

   This module provides interfaces to the IG60 network and device
   interfaces via D-Bus connections to Network Manager (wired,
   wireless) and Ofono (LTE).
"""

import asyncio
import logging

# Import DBus/Glib stuff conditionally to allow development platforms
# (e.g., PC) to run (without the network functionality)
try:
    import dbus, dbus.exceptions
    import dbus.mainloop.glib
    from gi.repository import GObject as gobject
    from gi.repository import GLib as glib
except:
    pass

# Network Manager D-Bus objects
NM_IFACE = 'org.freedesktop.NetworkManager'
NM_SETTINGS_IFACE = 'org.freedesktop.NetworkManager.Settings'
NM_SETTINGS_OBJ = '/org/freedesktop/NetworkManager/Settings'
NM_OBJ = '/org/freedesktop/NetworkManager'
NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
NM_CONNECTION_ACTIVE_IFACE = 'org.freedesktop.NetworkManager.Connection.Active'
NM_IP4_CONFIG_IFACE = 'org.freedesktop.NetworkManager.IP4Config'
NM_IP6_CONFIG_IFACE = 'org.freedesktop.NetworkManager.IP6Config'

# NM Active Connection State values
NM_ACTIVE_CONNECTION_STATE_UNKNOWN = 0
NM_ACTIVE_CONNECTION_STATE_ACTIVATING = 1
NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
NM_ACTIVE_CONNECTION_STATE_DEACTIVATING = 3
NM_ACTIVE_CONNECTION_STATE_DEACTIVATED = 4

# Network Manager property names
NM_PROP_ACTIVE_CONNECTIONS = 'ActiveConnections'
NM_PROP_CONN_STATE = 'State'
NM_PROP_CONN_DEVICES = 'Devices'
NM_PROP_DEVICE_INTERFACE = 'Interface'
NM_PROP_IP4_CONFIG = 'Ip4Config'
NM_PROP_IP6_CONFIG = 'Ip6Config'
NM_PROP_IP_ADDR_DATA = 'AddressData'
NM_KEY_ADDRESS = 'address'

# Ofono D-Bus objects
OFONO_ROOT_PATH = '/'
OFONO_BUS_NAME = 'org.ofono'
OFONO_MANAGER_IFACE = 'org.ofono.Manager'
OFONO_MODEM_IFACE = 'org.ofono.Modem'
OFONO_NETREG_IFACE = 'org.ofono.NetworkRegistration'
OFONO_CONNMAN_IFACE = 'org.ofono.ConnectionManager'
OFONO_CONNECTION_IFACE = 'org.ofono.ConnectionContext'
OFONO_LTE_IFACE = 'org.ofono.LongTermEvolution'

log = logging.getLogger('ig60network')

class IG60Network():
    """IG60 network interface class
    """

    def __init__(self):
        self.bus = None
        self.nm = None
        self.nm_props = None
        self.ofono = None
        try:
            self.bus = dbus.SystemBus()
            self.nm = dbus.Interface(self.bus.get_object(NM_IFACE, NM_OBJ), NM_IFACE)
            self.nm_props = dbus.Interface(self.bus.get_object(NM_IFACE, NM_OBJ), DBUS_PROP_IFACE)
            self.nm_settings = dbus.Interface(self.bus.get_object(NM_IFACE, NM_SETTINGS_OBJ), NM_SETTINGS_IFACE)
            self.ofono = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME, OFONO_ROOT_PATH), OFONO_MANAGER_IFACE)
        except Exception as e:
            log.warn(f'IG60 Network integration will not function: {e}')

    def get_available_connections(self):
        """Return a list of currently available network connections"""
        conns = []
        try:
            for c in self.nm_props.Get(NM_IFACE, NM_PROP_ACTIVE_CONNECTIONS):
                conn_props = dbus.Interface(self.bus.get_object(NM_IFACE, c), DBUS_PROP_IFACE)
                conn_state = conn_props.Get(NM_CONNECTION_ACTIVE_IFACE, NM_PROP_CONN_STATE)
                dev_props = dbus.Interface(self.bus.get_object(NM_IFACE,
                    conn_props.Get(NM_CONNECTION_ACTIVE_IFACE, NM_PROP_CONN_DEVICES)[0]), DBUS_PROP_IFACE)
                iface = str(dev_props.Get(NM_DEVICE_IFACE, NM_PROP_DEVICE_INTERFACE))
                if conn_state == NM_ACTIVE_CONNECTION_STATE_ACTIVATED:
                    ip4_props = dbus.Interface(self.bus.get_object(NM_IFACE,
                        conn_props.Get(NM_CONNECTION_ACTIVE_IFACE, NM_PROP_IP4_CONFIG)),
                        DBUS_PROP_IFACE)
                    a4addr_data = ip4_props.Get(NM_IP4_CONFIG_IFACE, NM_PROP_IP_ADDR_DATA)
                    a4_addresses = []
                    for a4 in a4addr_data:
                        a4_addresses.append(str(a4[NM_KEY_ADDRESS]))
                    ip6_props = dbus.Interface(self.bus.get_object(NM_IFACE,
                        conn_props.Get(NM_CONNECTION_ACTIVE_IFACE, NM_PROP_IP6_CONFIG)),
                        DBUS_PROP_IFACE)
                    a6addr_data = ip6_props.Get(NM_IP6_CONFIG_IFACE, NM_PROP_IP_ADDR_DATA)
                    a6_addresses = []
                    for a6 in a6addr_data:
                        a6_addresses.append(str(a6[NM_KEY_ADDRESS]))
                    conns.append((iface, a4_addresses, a6_addresses,))
        except Exception as e:
            log.warn(f'Failed to parse connections over D-Bus: {e}')
        return conns

    def find_iface_by_addr(self, addr):
        """Find the interface name that matches a given IP address"""
        conns = self.get_available_connections()
        for c in conns:
            for a4 in c[1]:
                if a4 == addr:
                    return c[0]
            for a6 in c[2]:
                if a6 == addr:
                    return c[0]
        return ''

    def get_ofono_net_props(self):
        """Return Ofono Network properties"""
        try:
            modems = self.ofono.GetModems()
            netreg = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME,
                modems[0][0]), OFONO_NETREG_IFACE)
            net_props = netreg.GetProperties()
            return net_props
        except:
            return {}

    def get_ofono_net_prop_int(self, prop, default = None):
        """Return an Ofono Network property as an integer"""
        val = self.get_ofono_net_props().get(prop)
        return int(val) if val is not None else default

    def get_ofono_conn_props(self):
        """Return Ofono Connection properties"""
        try:
            modems = self.ofono.GetModems()
            connman = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME,
                modems[0][0]), OFONO_CONNMAN_IFACE)
            ctxs = connman.GetContexts()
            ctx = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME,
                ctxs[0][0]), OFONO_CONNECTION_IFACE)
            ctx_props = ctx.GetProperties()
            return ctx_props
        except:
            return {}

    def get_ofono_conn_prop_str(self, prop, default = None):
        """Return an Ofono Connection property as an string"""
        val = self.get_ofono_conn_props().get(prop)
        return str(val) if val is not None else default

    def get_ofono_lte_props(self):
        """Return Ofono LTE properties"""
        try:
            modems = self.ofono.GetModems()
            lte = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME,
                modems[0][0]), OFONO_LTE_IFACE)
            lte_props = lte.GetProperties()
            return lte_props
        except:
            return {}

    def get_ofono_lte_prop_str(self, prop, default = None):
        """Return an Ofono LTE property as a string"""
        log.debug(f'Getting Ofono LTE property {prop}')
        val = self.get_ofono_lte_props().get(prop)
        return str(val) if val is not None else default

    def set_ofono_lte_prop(self, prop, value):
        """Set an Ofono LTE property"""
        try:
            modems = self.ofono.GetModems()
            lte = dbus.Interface(self.bus.get_object(OFONO_BUS_NAME,
                modems[0][0]), OFONO_LTE_IFACE)
            log.debug(f'Setting Ofono LTE property {prop} to {value}')
            lte.SetProperty(prop, value)
            return True
        except Exception as e:
            log.error(f'Failed to set Ofono LTE property {prop}: {e}')
            return False
