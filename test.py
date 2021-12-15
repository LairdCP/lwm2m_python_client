#!/usr/bin/env python3

"""Test application for Python LwM2M client"""

import logging
import asyncio
import sys
import argparse

from lwm2m.client import LwM2MClient
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst
from lwm2m.object import LwM2MObjectInst

from datetime import datetime

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s')

if __name__ == '__main__':
    # Default to bind to local address & port
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', default='127.0.0.1', help='Local address to bind')
    parser.add_argument('-p', '--port', default=5683, help='Local port to bind')
    args = parser.parse_args()
    client = LwM2MClient(args.address, args.port)
    loop = asyncio.get_event_loop()
    loop.create_task(client.start())
    try:
        # Add default single instance for Object 3
        obj3 = LwM2MObjectInst(3)
        obj3.add_resource(LwM2MResourceValue(3, 0, 0, 'Laird Connectivity, Inc.'))
        obj3.add_resource(LwM2MResourceValue(3, 0, 1, 'Sentrius IG60'))
        obj3.add_multi_resource(LwM2MResourceInst(3, 0, 6, 0, 0))
        obj3.add_multi_resource(LwM2MResourceInst(3, 0, 6, 1, 1))
        obj3.add_resource(LwM2MResourceValue(3, 0, 13, datetime.now()))
        obj3.add_resource(LwM2MResourceValue(3, 0, 14, 'UTC+0500'))
        obj3.add_resource(LwM2MResourceValue(3, 0, 15, 'EST'))
        client.add_object(obj3)
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()
        exit(0)
