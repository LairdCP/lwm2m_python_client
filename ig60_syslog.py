"""Implementation of System Log (Object 10259) for IG60
"""

import asyncio
import subprocess
import logging
import os

from lwm2m.object import LwM2MObjectInst
from lwm2m.resource import LwM2MResourceValue, LwM2MResourceInst, LwM2MExecutableResource
from lwm2m.syslog import *
from lwm2m.block import LwM2MBlock2FileResource

SYSLOG_NAME = 'journald'
SYSLOG_FILE = '/tmp/syslog.txt'

IG60_SYSLOG_INSTANCE = 0

JOURNAL_CMD = 'journalctl'
JOURNAL_INCREMENTAL_CMD = 'journalctl --cursor-file=/tmp/lwm2m-cursor'

log = logging.getLogger('ig60syslog')

class IG60JournaldLogResource(LwM2MBlock2FileResource):
    """Implementation of 'Read' resource for LwM2M System Log that
       reads from the journald log
    """
    def __init__(self, res_id, incremental):
        self.incremental = incremental
        super(IG60JournaldLogResource, self).__init__(LWM2M_SYSLOG_OBJECT, IG60_SYSLOG_INSTANCE, res_id, SYSLOG_FILE)

    def start_payload(self):
        # Create a temporary file with the log contents
        log.info(f'Writing journald log to {self.filename}')
        if self.incremental:
            cmd = JOURNAL_INCREMENTAL_CMD.split(' ')
        else:
            cmd = JOURNAL_CMD.split(' ')
        with open(SYSLOG_FILE, 'w') as f:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            while True:
                # Convert each line to string
                line = proc.stdout.readline()
                if line:
                    f.write(line.decode())
                else:
                    break
            proc.wait()
        super(IG60JournaldLogResource, self).start_payload()

    def end_payload(self):
        log.info(f'Deleting log file {self.filename}')
        os.remove(self.filename)

class IG60SyslogObject(LwM2MObjectInst):
    """Object 10259 (System Log) implementation for IG60
    """

    def __init__(self):
        super(IG60SyslogObject, self).__init__(LWM2M_SYSLOG_OBJECT, IG60_SYSLOG_INSTANCE)
        self.add_resource(LwM2MResourceValue(LWM2M_SYSLOG_OBJECT, IG60_SYSLOG_INSTANCE, LWM2M_SYSLOG_RESOURCE_NAME, SYSLOG_NAME))
        self.add_resource(IG60JournaldLogResource(LWM2M_SYSLOG_RESOURCE_READ_ALL, False))
        self.add_resource(IG60JournaldLogResource(LWM2M_SYSLOG_RESOURCE_READ, True))
