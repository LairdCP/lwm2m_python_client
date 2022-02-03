#!/usr/bin/env python3

"""Python LwM2M Client for IG60"""

import logging
import asyncio
import sys
import argparse

from lwm2m.client import LwM2MClient
from ig60_device import IG60DeviceObject
from ig60_fwupdate import IG60FWUpdateObject

if __name__ == '__main__':
    # Default to bind to local address & port
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', default='127.0.0.1', help='Local address to bind')
    parser.add_argument('-p', '--port', type=int, default=5782, help='Local port to bind')
    parser.add_argument('-bs', '--bootstrap-address', default='', help='Address of bootstrap server')
    parser.add_argument('-bp', '--bootstrap-port', default=5683, help='Port of bootstrap server')
    parser.add_argument('-bk', '--bootstrap-psk', default='', help='PSK for DTLS-enabled bootstrap server (hex)')
    parser.add_argument('-s', '--server-address', default='localhost', help='Address of LwM2M server')
    parser.add_argument('-sp', '--server-port', type=int, default=5684, help='Port of L2M2M server')
    parser.add_argument('-sk', '--server-psk', default='', help='PSK for DTLS-enabled bootstrap server (hex)')
    parser.add_argument('-e', '--endpoint', default='python-client', help='L2M2M Endpoint')
    parser.add_argument('-d', '--debug', action='store_true', help='Set debug logging')
    args = parser.parse_args()
    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s [%(levelname)s] %(message)s')
    logging.getLogger().info(args)
    client = LwM2MClient(**vars(args))
    loop = asyncio.get_event_loop()
    loop.create_task(client.start())
    try:
        # Add IG60 Device object
        client.add_object(IG60DeviceObject())
        # Add IG60 firmware update object
        client.add_object(IG60FWUpdateObject())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()
        exit(0)
