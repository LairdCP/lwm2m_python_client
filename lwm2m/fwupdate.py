"""Implementation of LwM2M Firmware Update (Object 5)
"""

import logging
import asyncio

from .base import LwM2MBase
from .object import LwM2MObjectInst, LwM2MBaseObject
from .resource import LwM2MResourceValue, LwM2MExecutableResource

log = logging.getLogger('fwupdate')

# LwM2M Object 5 (Firmware Update) resource and instance definitions
LWM2M_FWUPDATE_OBJECT = 5

LWM2M_FWUPDATE_RESOURCE_PACKAGE = 0
LWM2M_FWUPDATE_RESOURCE_PACKAGE_URI = 1
LWM2M_FWUPDATE_RESOURCE_UPDATE = 2
LWM2M_FWUPDATE_RESOURCE_STATE = 3
LWM2M_FWUPDATE_RESOURCE_RESULT = 5
LWM2M_FWUPDATE_RESOURCE_METHOD = 9

LWM2M_FWUPDATE_INSTANCE = 0

LWM2M_FWUPDATE_STATE_IDLE = 0
LWM2M_FWUPDATE_STATE_DOWNLOADING = 1
LWM2M_FWUPDATE_STATE_DOWNLOADED = 2
LWM2M_FWUPDATE_STATE_UPDATING = 3

LWM2M_FWUPDATE_RESULT_INITIAL = 0
LWM2M_FWUPDATE_RESULT_SUCCESS = 1
LWM2M_FWUPDATE_RESULT_NOFLASH = 2
LWM2M_FWUPDATE_RESULT_NOMEM = 3
LWM2M_FWUPDATE_RESULT_CONNLOST = 4
LWM2M_FWUPDATE_RESULT_INTEGRITY_FAILED = 5
LWM2M_FWUPDATE_RESULT_UNSUPPORTED = 6
LWM2M_FWUPDATE_RESULT_INVALID_URI = 7
LWM2M_FWUPDATE_RESULT_UPDATE_FAILED = 8
LWM2M_FWUPDATE_RESULT_BAD_PROTOCOL = 9

LWM2M_FWUPDATE_METHOD_PULL = 0
LWM2M_FWUPDATE_METHOD_PUSH = 1
LWM2M_FWUPDATE_METHOD_BOTH = 2

class LwM2MFWUpdateObject(LwM2MObjectInst):
    """Base implementation of Object 5 (Firmware Update) instance

       This object provides the framework for performing a firmware update and reporting the
       status; it is expected that this class will be extended with device-specific actions.
    """

    def __init__(self, update_method = LWM2M_FWUPDATE_METHOD_BOTH):
        super(LwM2MFWUpdateObject, self).__init__(LWM2M_FWUPDATE_OBJECT, LWM2M_FWUPDATE_INSTANCE)
        # Create default resources for reporting state
        self.update_state = LwM2MResourceValue(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_STATE, LWM2M_FWUPDATE_STATE_IDLE)
        self.add_resource(self.update_state)
        self.update_result = LwM2MResourceValue(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_RESULT, LWM2M_FWUPDATE_RESULT_INITIAL)
        self.add_resource(self.update_result)
        self.add_resource(LwM2MResourceValue(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_METHOD, update_method))

    def report_update_state(self, state):
        self.update_state.set_value(state)

    def report_update_result(self, result):
        self.update_result.set_value(result)
