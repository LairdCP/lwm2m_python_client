"""Implementation of LwM2M Device (Object 3) for IG60

   This class provides a few useful resources via Object 3 including device name,
   version, memory information, etc.
"""

import asyncio
import subprocess
import re
import logging
from datetime import datetime
import os

from lwm2m.object import LwM2MObjectInst
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MExecutableResource
from lwm2m.device import *

IG60_MANUFACTURER = 'Laird Connectivity, Inc.'
IG60_MODEL = 'Sentrius IG60'

TZ_DEFAULT = 'UTC+00:00'

class IG60FWVersionResource(LwM2MResourceValue):
    """LwM2M Resource that reads the IG60 firmware version"""
    def __init__(self, obj_id, obj_inst, res_id):
        super(IG60FWVersionResource, self).__init__(obj_id, obj_inst, res_id)

    def get_value(self):
        p = subprocess.run(['grep', 'VERSION_ID', '/etc/os-release'], capture_output=True)
        return p.stdout.decode().strip().split('=')[1]

class IG60MemoryResource(LwM2MResourceValue):
    """LwM2M Resource that reads a line from the Linux memory proc resource"""
    def __init__(self, obj_id, obj_inst, res_id, mem_id):
        super(IG60MemoryResource, self).__init__(obj_id, obj_inst, res_id)
        self.mem_id = mem_id

    def get_value(self):
        p = subprocess.run(['grep', self.mem_id, '/proc/meminfo'], capture_output=True)
        free_k = int(re.split('\W+', p.stdout.decode().strip())[1])
        # LwM2M spec defines "kilobyte" as exactly 1000 bytes (SMH)
        return int((free_k * 1024) / 1000)

class IG60DeviceObject(LwM2MObjectInst):
    """Object 3 (Device) implementation for IG60
    """

    def __init__(self):
        super(IG60DeviceObject, self).__init__(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE)
        self.add_resource(LwM2MResourceValue(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_MANUFACTURER, IG60_MANUFACTURER))
        self.add_resource(LwM2MResourceValue(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_MODEL, IG60_MODEL))
        self.add_resource(IG60FWVersionResource(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_FW_VERSION))
        self.add_resource(LwM2MExecutableResource(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_REBOOT, self.reboot))
        pwr_src_dc = LwM2MResourceInst(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_AVAILABLE_POWER_SOURCES, 0, LWM2M_DEVICE_POWER_DC)
        self.add_multi_resource(pwr_src_dc)
        self.time_resource = LwM2MResourceValue(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_CURRENT_TIME, datetime.now())
        self.add_resource(self.time_resource)
        # TZ environment is the offset (e.g., "UTC+05:00")
        utc_offset = os.getenv('TZ') or TZ_DEFAULT
        self.add_resource(LwM2MResourceValue(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_UTC_OFFSET, utc_offset))
        self.add_resource(IG60MemoryResource(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_MEMORY_FREE, 'MemFree'))
        self.add_resource(IG60MemoryResource(LWM2M_DEVICE_OBJECT, LWM2M_DEVICE_INSTANCE, LWM2M_DEVICE_RESOURCE_MEMORY_TOTAL, 'MemTotal'))
        asyncio.get_event_loop().create_task(self.update_time())

    async def update_time(self):
        while True:
            await asyncio.sleep(1)
            self.time_resource.set_value(datetime.now())

    def reboot(self):
        # Start an orderly systemd reboot
        subprocess.run(['systemctl', 'reboot'])
