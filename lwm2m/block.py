"""Implementation of block-wise resources for LwM2M
"""

import logging
import asyncio

from aiocoap.message import Message
from aiocoap.numbers.codes import Code
from aiocoap.optiontypes import BlockOption
from aiocoap.protocol import Context
from aiocoap.error import Error, ConstructionRenderableError

from .base import LwM2MBase
from .tlv import MediaType, TlvDecoder

log = logging.getLogger('block')

COAP_BLOCKWISE_MAX_EXPONENT = 6 # Max block size = 1024

class LwM2MBlockwiseResource(LwM2MBase):
    """LwM2M resource that handles incoming blockwise transfer (Block1)"""

    def __init__(self, obj_id, obj_inst, res_id, resp_sz_exp = COAP_BLOCKWISE_MAX_EXPONENT):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.res_id = res_id
        self.resp_sz_exp = resp_sz_exp
        self.last_block_number = None
        super(LwM2MBlockwiseResource, self).__init__(f'Obj_{obj_id}_{obj_inst}_Res_{res_id}')

    async def needs_blockwise_assembly(self, request):
        # aiocoap can handle the entire blockwise transfer, but we want to handle the individual
        # blocks so we can stream the incoming data
        return False

    def get_id(self):
        return self.res_id

    def notify(self, notify_cb):
        pass

    def build_site(self, site):
        log.debug(f'{self.obj_id}/{self.obj_inst}/{self.res_id} -> {self.desc}')
        site.add_resource((str(self.obj_id), str(self.obj_inst), str(self.res_id)), self)

    async def render_post(self, request):
        return await self.handle_blockwise(request)

    async def render_put(self, request):
        return await self.handle_blockwise(request)

    async def handle_blockwise(self, request):
        log.debug(f'{self.desc}: Request format={request.opt.content_format}')

        if request.opt.content_format != MediaType.OPAQUE.value and request.opt.content_format != MediaType.TLV.value:
            return Message(code=Code.NOT_ACCEPTABLE)

        if request.opt.block1 is None:
            # Payload was encoded in a single request
            self.start_payload()
            self.handle_payload(self.decode_payload(request), False)
            return Message(code=Code.CHANGED)

        if request.opt.block1.block_number == 0:
            if self.last_block_number is not None:
                log.warn('Aborting incomplete Block1 operation!')
            self.start_payload()
        else:
            if request.opt.block1.block_number != self.last_block_number + 1:
                log.warn(f'Invalid block sequence ({request.opt.block1.block_number} != {self.last_block_number + 1}')
                return Message(code=Code.REQUEST_ENTITY_INCOMPLETE)

        self.last_block_number = request.opt.block1.block_number

        if request.opt.block1.more:
            if (len(request.payload) != request.opt.block1.size or
                request.opt.block1.size != (1<<(request.opt.block1.size_exponent+4))):
                    log.warn('Invalid block size or exponent!')
                    return Message(code=Codes.BAD_REQUEST)
            resp = Message(code=Code.CONTINUE,
                           block1=BlockOption.BlockwiseTuple(
                                request.opt.block1.block_number,
                                True,
                                self.resp_sz_exp), # Request preferred transfer size
                           )
        else:
            resp = Message(code=Code.CHANGED)

        self.handle_payload(self.decode_payload(request), request.opt.block1.more)
        return resp

    def decode_payload(self, request):
        if request.opt.content_format == MediaType.TLV.value:
            _type, id, value, _ =  TlvDecoder.decode_tlv(request.payload)
            return value
        else:
            return request.payload

    def start_payload(self):
        log.debug(f'{self.desc}: Starting new blockwise payload')

    def handle_payload(self, payload, more):
        log.debug(f'{self.desc}: Received {"" if more else "last"} blockwise payload of {len(payload)} bytes')

class LwM2MBlockwiseFileResource(LwM2MBlockwiseResource):
    """LwM2M resource that receives blockwise transfer into a file"""

    def __init__(self, obj_id, obj_inst, res_id, file_path, start_cb = None, end_cb = None):
        self.obj_id = obj_id
        self.obj_inst = obj_inst
        self.res_id = res_id
        self.file_path = file_path
        self.start_cb = start_cb
        self.end_cb = end_cb
        self.f = None
        super(LwM2MBlockwiseFileResource, self).__init__(obj_id, obj_inst, res_id)

    def start_payload(self):
        if self.f:
            self.f.close()
            self.f = None
        self.f = open(self.file_path, 'wb')
        log.debug(f'{self.desc}: Starting new file {self.file_path}')
        self.total_bytes = 0
        if self.start_cb:
            self.start_cb()

    def handle_payload(self, payload, more):
        self.f.write(payload)
        self.total_bytes = self.total_bytes + len(payload)
        log.debug(f'{self.desc}: Wrote {len(payload)} bytes to {self.file_path}')
        if not more:
            log.info(f'{self.desc}: Wrote {self.total_bytes} total bytes to {self.file_path}')
            self.f.close()
            self.f = None
            if self.end_cb:
                self.end_cb()

class CoAPDownloadClient():
    """Client to download a file via CoAP"""

    async def download(self, uri, file_path, req_sz_exp = COAP_BLOCKWISE_MAX_EXPONENT):
        log.info(f'Downloading file via CoAP from {uri}')
        client = await Context.create_client_context()
        more = True
        block_number = 0
        total_bytes = 0
        with open(file_path, 'wb') as f:
            while more:
                request = Message(code=Code.GET,
                    uri=uri,
                    block2=BlockOption.BlockwiseTuple(
                        block_number,
                        True,
                        req_sz_exp),
                   )
                response = await client.request(request, handle_blockwise=False).response
                if not response.code.is_successful():
                    raise ConstructionRenderableError(response)
                if response.opt.block2 is None:
                    # Payload is single message
                    more = False
                else:
                    more = response.opt.block2.more
                if response.payload:
                    n = f.write(response.payload)
                    total_bytes = total_bytes + n
                block_number = block_number + 1
            log.info(f'CoAP download: wrote {total_bytes} to {file_path}')
