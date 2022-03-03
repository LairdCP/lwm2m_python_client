"""Implementation of LwM2M Firmware Update (Object 5) for IG60
"""

import asyncio
import logging
import requests
from requests.exceptions import RequestException

from lwm2m.fwupdate import *
from lwm2m.block import CoAPDownloadClient

log = logging.getLogger('ig60fwupdate')

FW_UPDATE_FILE = '/tmp/update.bin'
REQUEST_TIMEOUT = 30
HTTP_BLOCK_SIZE = 4096
UPDATE_COMMAND = 'ig60_fw_update.sh'

class IG60FWUpdateObject(LwM2MFWUpdateObject):
    """Object 5 (Firmware Update) implementation for IG60

       This implementation of firmware update for the IG60 will
       download an update file via CoAP blockwise transfer or via
       a URI string.  Triggering the update via 'execute' will then
       call a helper script to perform the update, and set the
       result state from the script exit code.
    """

    def __init__(self):
        super(IG60FWUpdateObject, self).__init__()
        self.add_resource(LwM2MBlockwiseFileResource(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_PACKAGE, FW_UPDATE_FILE,
            self.update_block_start, self.update_block_end))
        self.add_resource(LwM2MResourceValue(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_PACKAGE_URI, '', self.set_update_uri))
        self.add_resource(LwM2MExecutableResource(LWM2M_FWUPDATE_OBJECT, self.obj_inst, LWM2M_FWUPDATE_RESOURCE_UPDATE, self.exec_update))
        self.fw_downloaded = False

    async def http_download(self, uri, destfile):
        """Download a file via HTTP onto the local filesystem"""
        self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADING)
        try:
            total_bytes = 0
            r = requests.get(uri, stream=True, timeout=REQUEST_TIMEOUT)
            if not r.ok:
                log.warn(f'Invalid update URI {uri}')
                # Invalid URI, set results per LwM2M state machine
                self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
                self.report_update_result(LWM2M_FWUPDATE_RESULT_INVALID_URI)
                return
            with open(destfile, 'wb') as f:
                for chunk in r.iter_content(chunk_size=HTTP_BLOCK_SIZE):
                    if chunk: # Skip keep-alive chunks
                        n = f.write(chunk)
                        total_bytes = total_bytes + n
            log.info(f'Wrote {total_bytes} to {destfile}')
            self.fw_downloaded = True
            self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADED)
        except Exception as e:
            log.warn(f'Failed to download update file via HTTP: {e}')
            # Download failure, set results per LwM2M state machine
            self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
            self.report_update_result(LWM2M_FWUPDATE_RESULT_CONNLOST)
            return

    async def coap_download(self, uri, destfile):
        """Download a file via CoAP onto the local filesystem"""
        self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADING)
        try:
            client = CoAPDownloadClient()
            await client.download(uri, destfile)
            self.fw_downloaded = True
            self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADED)
        except Exception as e:
            log.warn(f'Failed to download update file via CoAP {e}')
            # Download failure, set results per LwM2M state machine
            self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
            self.report_update_result(LWM2M_FWUPDATE_RESULT_CONNLOST)

    def update_block_start(self):
        """Callback indicating blockwise transfer has started"""
        log.info('IG60 update block transfer started.')
        self.fw_downloaded = False
        self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADING)

    def update_block_end(self):
        """Callback indicating blockwise transfer is complete"""
        log.info('IG60 update block transfer complete.')
        self.fw_downloaded = True
        self.report_update_state(LWM2M_FWUPDATE_STATE_DOWNLOADED)

    def set_update_uri(self, uri):
        """Callback when update URI is written"""
        log.info(f'IG60 update URI set to {uri}')
        # Always reset download state
        self.fw_downloaded = False
        if uri.startswith('\0'):
            # NULL byte, reset state machine
            log.info('Resetting fwupdate state machine.')
            self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
            self.report_update_result(LWM2M_FWUPDATE_RESULT_INITIAL)
        else:
            # Schedule download if URI is valid
            if uri.startswith('http'):
                asyncio.get_event_loop().create_task(self.http_download(uri, FW_UPDATE_FILE))
            elif uri.startswith('coap'):
                asyncio.get_event_loop().create_task(self.coap_download(uri, FW_UPDATE_FILE))
            else:
                # Report invalid URI
                self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
                self.report_update_result(LWM2M_FWUPDATE_RESULT_INVALID_URI)

    async def perform_update(self):
        if not self.fw_downloaded:
            self.report_update_result(LWM2M_FWUPDATE_RESULT_UNSUPPORTED)
            return
        p = await asyncio.create_subprocess_shell(f'{UPDATE_COMMAND} {FW_UPDATE_FILE}', stdout=asyncio.subprocess.PIPE)
        async for line in p.stdout:
            log.debug(line.decode())
        await p.wait()
        # Reset download state once update is complete
        self.fw_downloaded = False
        log.info(f'{UPDATE_COMMAND} returned result {p.returncode}')
        # Return the script result code as the LwM2M update result and reset state
        self.report_update_state(LWM2M_FWUPDATE_STATE_IDLE)
        self.report_update_result(p.returncode)

    def exec_update(self):
        """Callback when update action is triggered"""
        log.info('IG60 update executed.')
        # Ignore if update is already in progress
        if self.update_state.get_value() != LWM2M_FWUPDATE_STATE_UPDATING:
            self.report_update_state(LWM2M_FWUPDATE_STATE_UPDATING)
            asyncio.get_event_loop().create_task(self.perform_update())
