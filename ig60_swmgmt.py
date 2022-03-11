"""Implementation of LwM2M Software Management (Object 9) for IG60
"""

import asyncio
import logging
import requests
from requests.exceptions import RequestException
import os
import shutil
import subprocess

from version import __version__
from lwm2m.resource import LwM2MResourceValue, LwM2MExecutableResource
from lwm2m.swmgmt import *
from lwm2m.block import LwM2MBlock1FileResource, CoAPDownloadClient

log = logging.getLogger('ig60swmgmt')

SW_UPDATE_FILE = '/tmp/swupdate.tar.gz'
SW_UPDATE_WORK_DIR = '/tmp/swupdate'
SW_UPDATE_CHECKSUMS = 'checksums.txt'
REQUEST_TIMEOUT = 30
HTTP_BLOCK_SIZE = 4096

IG60_SWMGMT_INSTANCE = 0

SW_PACKAGE_NAME = 'lwm2m-python-client'

SWUPDATE_EXTRACT_CMD = f'tar xzf {SW_UPDATE_FILE} -C {SW_UPDATE_WORK_DIR}'
SWUPDATE_VERIFY_CMD = f'sha256sum -c {SW_UPDATE_CHECKSUMS}'

class IG60SWManagementObject(LwM2MSWManagementObject):
    """Object 9 (Software Management) implementation for IG60

       This class implements a single instance of the LwM2M
       Software Management object, which is used to manage this
       client itself.  Updates can be downloaded via CoAP or HTTP
       and will be verified.  The update client application will
       not be installed (as it is currently running!) but when the
       'Activate' step is executed, this client will exit so that
       an external management script can apply the updated
       executable.
    """

    def __init__(self, activate_cb = None):
        super(IG60SWManagementObject, self).__init__(IG60_SWMGMT_INSTANCE)
        self.activate_cb = activate_cb
        self.add_resource(LwM2MResourceValue(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_PKGNAME, SW_PACKAGE_NAME))
        self.add_resource(LwM2MResourceValue(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_PKGVERSION, __version__))
        self.add_resource(LwM2MBlock1FileResource(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_PACKAGE, SW_UPDATE_FILE,
            self.update_block_start, self.update_block_end))
        self.add_resource(LwM2MResourceValue(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_PACKAGE_URI, '', self.set_update_uri))
        self.add_resource(LwM2MExecutableResource(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_INSTALL, self.exec_install))
        self.add_resource(LwM2MExecutableResource(LWM2M_SWMGMT_OBJECT, self.obj_inst, LWM2M_SWMGMT_RESOURCE_ACTIVATE, self.exec_activate))
        self.sw_downloaded = False

    async def http_download(self, uri, destfile):
        """Download a file via HTTP onto the local filesystem"""
        self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOAD_STARTED)
        try:
            total_bytes = 0
            r = requests.get(uri, stream=True, timeout=REQUEST_TIMEOUT)
            if not r.ok:
                log.warn(f'Invalid software package URI {uri}')
                # Invalid URI, set results per LwM2M state machine
                self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INITIAL)
                self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_INVALID_URI)
                return
            with open(destfile, 'wb') as f:
                for chunk in r.iter_content(chunk_size=HTTP_BLOCK_SIZE):
                    if chunk: # Skip keep-alive chunks
                        n = f.write(chunk)
                        total_bytes = total_bytes + n
            log.info(f'Wrote {total_bytes} to {destfile}')
            self.sw_downloaded = True
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOADED)
            # Schedule task to unpack and verify integrity
            asyncio.get_event_loop().create_task(self.unpack_verify_update())
        except Exception as e:
            log.warn(f'Failed to download software package via HTTP: {e}')
            # Download failure, set results per LwM2M state machine
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INITIAL)
            self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_CONN_FAILED)
            return

    async def coap_download(self, uri, destfile):
        """Download a file via CoAP onto the local filesystem"""
        self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOAD_STARTED)
        try:
            client = CoAPDownloadClient()
            await client.download(uri, destfile)
            self.sw_downloaded = True
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOADED)
            # Schedule task to unpack and verify integrity
            asyncio.get_event_loop().create_task(self.unpack_verify_update())
        except Exception as e:
            log.warn(f'Failed to download software package via CoAP {e}')
            # Download failure, set results per LwM2M state machine
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INITIAL)
            self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_CONN_FAILED)

    def update_block_start(self):
        """Callback indicating blockwise transfer has started"""
        log.info('IG60 software package block transfer started.')
        self.sw_downloaded = False
        self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOAD_STARTED)

    def update_block_end(self):
        """Callback indicating blockwise transfer is complete"""
        log.info('IG60 software package block transfer complete.')
        self.sw_downloaded = True
        self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DOWNLOADED)
        # Schedule task to unpack and verify integrity
        asyncio.get_event_loop().create_task(self.unpack_verify_update())

    def set_update_uri(self, uri):
        """Callback when update URI is written"""
        log.info(f'IG60 software package URI set to {uri}')
        # Always reset download state
        self.sw_downloaded = False
        if uri.startswith('\0'):
            # NULL byte, reset state machine
            log.info('Resetting software package state machine.')
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INITIAL)
            self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_INITIAL)
        else:
            # Schedule download if URI is valid
            if uri.startswith('http'):
                asyncio.get_event_loop().create_task(self.http_download(uri, SW_UPDATE_FILE))
            elif uri.startswith('coap'):
                asyncio.get_event_loop().create_task(self.coap_download(uri, SW_UPDATE_FILE))
            else:
                # Report invalid URI
                self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INITIAL)
                self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_INVALID_URI)

    async def unpack_verify_update(self):
        """Unpack and verify the update tarball"""
        try:
            shutil.rmtree(SW_UPDATE_WORK_DIR, ignore_errors=True)
            os.makedirs(SW_UPDATE_WORK_DIR)
            subprocess.run(SWUPDATE_EXTRACT_CMD.split(' '), check=True)
            subprocess.run(SWUPDATE_VERIFY_CMD.split(' '), check=True,
                cwd=SW_UPDATE_WORK_DIR)
            log.info('Software package successfully verified!')
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_DELIVERED)
            self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_VERIFIED)
        except Exception as e:
            log.error(f'Failed to unpack/verify software package: {e}')
            return False

    def exec_install(self):
        """Callback when update action is triggered"""
        log.info('IG60 software install executed.')
        # If update was verified, report state as installed
        if self.update_state.value == LWM2M_SWMGMT_UPDATE_STATE_DELIVERED:
            self.report_update_state(LWM2M_SWMGMT_UPDATE_STATE_INSTALLED)
            self.report_update_result(LWM2M_SWMGMT_UPDATE_RESULT_INSTALLED)

    def exec_activate(self):
        # If update was installed and is now activated, trigger restart
        if self.update_state.value == LWM2M_SWMGMT_UPDATE_STATE_INSTALLED:
            log.info('IG60 software activated.')
            if self.activate_cb:
                self.activate_cb()
