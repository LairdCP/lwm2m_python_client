#!/usr/bin/env python3

"""Python LwM2M Client for IG60"""

import logging
import asyncio
import sys
import argparse
import errno
import aiocoap.error

from lwm2m.client import LwM2MClient
from ig60_device import IG60DeviceObject
from ig60_fwupdate import IG60FWUpdateObject
from ig60_network import IG60Network
from ig60_connmon import IG60ConnectionMonitor
from ig60_cellular import IG60Cellular, IG60APNProfile
from ig60_wlan import IG60WLANProfileBase
from lwm2m.wlan import LWM2M_WLAN_OBJECT
from ig60_bearer import IG60BearerObject
from ig60_swmgmt import IG60SWManagementObject
from ig60_syslog import IG60SyslogObject

RET_SUCCESS = 0

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger()

class BearerUpdated(Exception):
    """Exception used to signal bearer selection changed"""
    pass

class ClientUpdated(Exception):
    """Exception used to signal client was updated via software management"""
    pass

class IG60LwM2MClient(LwM2MClient):
    def __init__(self, port, **kwargs):
        super(IG60LwM2MClient, self).__init__(**kwargs)
        self.port = port
        self.result = None
        # Create IG60 Network interface helper
        self.ig60net = IG60Network()
        # Add IG60 Device object
        self.add_object(IG60DeviceObject())
        # Add IG60 Connection Monitor
        self.connmon = IG60ConnectionMonitor(self.ig60net)
        self.add_object(self.connmon)
        # Add IG60 firmware update object
        self.add_object(IG60FWUpdateObject())
        if len(self.ig60net.get_ofono_lte_props()) > 0:
            # LTE modem is present, add Cellular and APN objects
            self.add_object(IG60Cellular(self.ig60net))
            self.add_object(IG60APNProfile(self.ig60net))
        # Add WLAN Profile base object (it will populate instances)
        ig60wlan = IG60WLANProfileBase(self.ig60net)
        # Callback to client to re-register when instances change
        ig60wlan.site_changed(self.client_updated)
        self.add_base_object(LWM2M_WLAN_OBJECT, ig60wlan)
        # Add Bearer Selection object with callback
        self.ig60_bearer = IG60BearerObject(self.set_bearer)
        self.add_object(self.ig60_bearer)
        # Add Software Management object
        self.add_object(IG60SWManagementObject(self.sw_install))
        # Add system Log object
        self.add_object(IG60SyslogObject())

    async def run(self):
        self.result = None
        while (self.result is None or self.result == RET_SUCCESS): # Emulate do-while
            try:
                conns = self.ig60net.get_available_connections()
                self.result = errno.ENONET
                # Attempt a connection on each available interface that
                # is in the bearer list
                interfaces = self.ig60_bearer.get_interfaces()
                log.info(f'Bearer interfaces: {interfaces}')
                for i in interfaces:
                    match_conns = [c for c in conns if c[0].startswith(i)]
                    for iface, _, addrs, _ in match_conns:
                        # Attempt connection on each address on the interface
                        for address in addrs:
                            log.info(f'Adding special route for interface {iface}')
                            self.ig60net.add_special_route_for_iface(iface)
                            try:
                                # Update Connection Monitor object with current binding info
                                self.connmon.update_bind(i, address)
                                self.result = RET_SUCCESS
                                log.info(f'Starting client on {address}:{self.port}')
                                await self.start(address, self.port)
                                if self.result == RET_SUCCESS:
                                    # Client exited without a result code,
                                    # restart bearer selection
                                    raise BearerUpdated()
                                elif self.result == errno.ENOPKG:
                                    # Client updated, exit with package
                                    # update result
                                    raise ClientUpdated()
                            except aiocoap.error.TimeoutError:
                                log.warn('CoAP timeout occurred')
                            except aiocoap.error.ConstructionRenderableError as e:
                                log.warn(f'CoAP response error {e.message.code}')
                            except aiocoap.error.Error:
                                log.warn('CoAP error occurred')
                            finally:
                                self.ig60net.delete_special_route()
            except BearerUpdated:
                log.info('Restarting bearer selection.')
            except ClientUpdated:
                log.info('Client updated, exiting.')
            except asyncio.CancelledError:
                log.warn('Client task cancelled.')
                self.result = errno.EINTR
            except Exception as e:
                log.error(f'Exception during client execution: {e}')
                self.result = errno.EAGAIN
        return self.result

    def set_bearer(self, bearer_value):
        log.info('Default bearer written, stopping client.')
        self.stop()

    def sw_install(self):
        log.info('Client application updated, exiting.')
        self.result = errno.ENOPKG
        self.stop()

async def client_task():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5782, help='Local port to bind')
    parser.add_argument('-bs', '--bootstrap-address', default='', help='Address of bootstrap server')
    parser.add_argument('-bp', '--bootstrap-port', default=5683, help='Port of bootstrap server')
    parser.add_argument('-bk', '--bootstrap-psk', default='', help='PSK for DTLS-enabled bootstrap server (hex)')
    parser.add_argument('-s', '--server-address', default='', help='Address of LwM2M server')
    parser.add_argument('-sp', '--server-port', type=int, default=0, help='Port of L2M2M server')
    parser.add_argument('-sk', '--server-psk', default='', help='PSK for DTLS-enabled bootstrap server (hex)')
    parser.add_argument('-e', '--endpoint', default='python-client', help='L2M2M Endpoint')
    parser.add_argument('-l', '--lifetime', type=int, default=3600, help='Client lifetime')
    parser.add_argument('-d', '--debug', action='store_true', help='Set debug logging')
    args = parser.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    log.info(args)
    client = IG60LwM2MClient(**vars(args))
    ret = await client.run()
    return ret

def run_client():
    try:
        ret = asyncio.run(client_task())
    except KeyboardInterrupt:
        ret = errno.EINTR
    exit(ret)

if __name__ == '__main__':
    run_client()
