"""TLV encoder/decoder for LwM2M resources and objects

This module provides classes that enable TLV encoding and
decoding of LwM2M resource values, resources instances, and
object instances.
"""

import logging
from enum import Enum
from math import log
from struct import pack, unpack
from datetime import datetime

from aiocoap.message import Message
from aiocoap.numbers.codes import Code

logger = logging.getLogger('tlv')

class TlvType(Enum):
    OBJECT_INSTANCE = 0b00000000
    RESOURCE_INSTANCE = 0b01000000
    MULTIPLE_RESOURCE = 0b10000000
    RESOURCE_VALUE = 0b11000000

class MediaType(Enum):
    TEXT = 0
    LINK = 40
    OPAQUE = 42
    TLV = 11542
    JSON = 11543

# useful lambda to calculate the needed bytes from an integer
def needs_bytes(n): return 1 if n == 0 else int(log(abs(n), 256)) + 1

def hexdump(obj):
    return ''.join('{:02X} '.format(a) for a in obj)

class TlvEncoder(object):
    """Base class for TLV encoding
    
    Resource values are encoded and decoded based on the underlying
    Python type (e.g., a resource with a value of a Python "int" type
    is encoded to an integer per the LwM2M specification (of 8,
    16, 32, or 64 bits depending on the value).
    """

    @staticmethod
    def encode_value(v):
        """Encode a resource value to bytes based on its type"""
        _type = type(v).__name__
        if _type == 'int':
            _payload = v.to_bytes(
                int(v.bit_length() / 8) + 1, byteorder='big', signed=True)
        elif _type == 'str':
            _payload = v.encode()
        elif _type == 'float':
            if float.fromhex('0x0.000002P-126') <= v <= float.fromhex('0x1.fffffeP+127'):
                # fits in a float
                _payload = pack('>f', v)
            else:
                # use double
                _payload = pack('>d', v)
        elif _type == 'bool':
            _payload = b'\x01' if v else b'\x00'
        elif _type == 'datetime':
            _payload = TlvEncoder.encode_value(int(v.timestamp()))
        elif _type == 'bytes':
            _payload = v
        else:
            raise TypeError(
                f'unknown value type: {_type}. Must be one of (int,str,float,bool,datetime,bytes)')
        logger.debug(f'encode_value: {hexdump(_payload)}')
        return _payload

    @staticmethod
    def encode_tlv(tlv_type, _id, v):
        """Encode a resource value as a TLV with a specified type"""
        result = bytearray()
        _type = int(tlv_type.value)
        payload = TlvEncoder.encode_value(v)
        _len = len(payload)
        _type |= 0b000000 if 1 == needs_bytes(_id) else 0b100000
        if _len < 8:
            _type |= _len
        elif needs_bytes(_len) == 1:
            _type |= 0b00001000
        elif needs_bytes(_len) == 2:
            _type |= 0b00010000
        else:
            _type |= 0b00011000
        result.append(_type)
        result.extend(_id.to_bytes(1, byteorder='big') if _id <
                      256 else _id.to_bytes(2, byteorder='big'))
        if _len >= 8:
            if _len < 256:
                result.extend(_len.to_bytes(1, byteorder='big'))
            elif _len < 65536:
                result.extend(_len.to_bytes(2, byteorder='big'))
            else:
                msb = _len & 0xFF0000 >> 16
                result.extend(msb.to_bytes(1, byteorder='big'))
                result.extend((_len & 0xFFFF).to_bytes(2, byteorder='big'))
        result.extend(payload)
        logger.debug(f'encode_tlv: {hexdump(result)}')
        return bytes(result)

    @staticmethod
    def pack_resource_value(res):
        """Return the packed TLV representation of a resource value"""
        logger.debug(f'Packing resource value {res.get_desc()}')
        return TlvEncoder.encode_tlv(TlvType.RESOURCE_VALUE, res.get_id(), res.get_value())

    @staticmethod
    def get_resource_value(res):
        """Return the TLV-encoded CoAP message response to 'GET' a resource value"""
        return Message(code=Code.CONTENT, payload=TlvEncoder.pack_resource_value(res), content_format=MediaType.TLV.value)

    @staticmethod
    def pack_resource_inst(res_inst):
        """Return the packed TLV representation of a resource instance"""
        logger.debug(f'Packing resource value {res_inst.get_desc()}')
        return TlvEncoder.encode_tlv(TlvType.RESOURCE_INSTANCE, res_inst.get_inst(), res_inst.get_value())

    @staticmethod
    def get_resource_inst(res_inst):
        """Return the TLV encoded CoAP message response to 'GET' a resource instance"""
        return Message(code=Code.CONTENT, payload=TlvEncoder.pack_resource_inst(res_inst), content_format=MediaType.TLV.value)

    @staticmethod
    def pack_multi_resource(multi_res):
        """Return the packed TLV representation of all instances in a multiple resource"""
        logger.debug(f'Packing multi resource {multi_res.get_desc()}')
        _payload = bytearray()
        for inst, res_inst in multi_res.get_instances().items():
            _payload.extend(TlvEncoder.pack_resource_inst(res_inst))
        return TlvEncoder.encode_tlv(TlvType.MULTIPLE_RESOURCE, multi_res.get_id(), bytes(_payload))

    @staticmethod
    def get_multi_resource(multi_res):
        """Return the CoAP message object with the TLV encoding of a multiple resource"""
        return Message(code=Code.CONTENT, payload=TlvEncoder.pack_multi_resource(multi_res), content_format=MediaType.TLV.value)

    @staticmethod
    def pack_object(obj):
        """Return the packed TLV representation of the object's resources"""
        logger.debug(f'Packing object {obj.get_desc()} resources')
        payload = bytearray()
        for id, res in obj.get_resources().items():
            if getattr(res, 'get_instances', None) == None:
                # Resource value implementation
                payload.extend(TlvEncoder.pack_resource_value(res))
            else:
                # Multi-resource implementation
                payload.extend(TlvEncoder.pack_multi_resource(res))
        return bytes(payload)

    @staticmethod
    def get_object(obj):
        """Return the TLV encoded CoAP message response to 'GET' a single object"""
        return Message(code=Code.CONTENT, payload=TlvEncoder.pack_object(obj), content_format=MediaType.TLV.value)

    def pack_objects(objs):
        """Return the packed TLV representation of all object instances"""
        logger.debug(f'Packing base object {objs.get_desc()}')
        payload = bytearray()
        for inst, obj in objs.get_instances().items():
            payload.extend(TlvEncoder.encode_tlv(TlvType.OBJECT_INSTANCE, inst, TlvEncoder.pack_object(obj)))
        return bytes(payload)

    def get_objects(objs):
        """Return the packed TLV representation of all object instances"""
        return Message(code=Code.CONTENT, payload=TlvEncoder.pack_objects(objs), content_format=MediaType.TLV.value)

class TlvDecoder(object):
    @staticmethod
    def decode_value(_type, _bytes):
        """Decode a resource value from bytes based on the specified type"""
        logger.debug(f'decode_value: {hexdump(_bytes)}')
        if _type == 'int':
            return int.from_bytes(_bytes, byteorder='big', signed=True)
        elif _type == 'str':
            return _bytes.decode('utf-8')
        elif _type == 'float':
            if len(_bytes) == 4:
                return unpack('>f', _bytes)[0]
            elif len(_bytes) == 8:
                return unpack('>d', _bytes)[0]
        elif _type == 'bool':
            return bool.from_bytes(_bytes, byteorder='big')
        elif _type == 'datetime':
            return datetime.utcfromtimestamp(int.from_bytes(_bytes, byteorder='big', signed=True))
        elif _type == 'bytes':
            return _bytes
        raise TypeError(
            f'unknown value for type {_type}: Must be one of (int,str,float,bool,datetime,bytes)')

    @staticmethod
    def decode_tlv(_bytes):
        """Decode a TLV into a tuple of (type, id, len) from the given bytes"""
        logger.debug(f'decode_tlv: {hexdump(_bytes)}')
        _type = _bytes[0]
        _len_type = _type >> 3 & 0b11
        _len = None
        if _len_type == 0:
            _len = _type & 0b111
        id_len = _type >> 5 & 1
        _payload = _bytes[1:]
        _id = None
        if id_len == 1:
            _id = int.from_bytes(_payload[0:2], byteorder='big')
            _payload = _payload[2:]
        else:
            _id = int.from_bytes(_payload[0:1], byteorder='big')
            _payload = _payload[1:]
        if _len is None:
            _len = int.from_bytes(_payload[0:_len_type], byteorder='big')
            logger.info(f'value length: {_len}')
            _payload = _payload[_len_type:]
        _value = _payload[0:_len]
        remain = _payload[_len:]
        return (_type & 0b11000000, _id, _value, remain)

    @staticmethod
    def update_resource_value(request, res):
        """Update a resource value from a TLV-encoded CoAP message"""
        if request.opt.content_format != MediaType.TLV.value:
            logger.error(f'Invalid content format: {request.opt.content_format}')
            return Message(code=Code.NOT_ACCEPTABLE)
        try:
            tlv_type, id, value_bytes, remain = TlvDecoder.decode_tlv(request.payload)
        except:
            logger.error('Failed to decode TLV')
            return Message(code=Code.BAD_REQUEST)
        if tlv_type != TlvType.RESOURCE_VALUE.value:
            logger.error(f'Invalid TLV type: {_type}')
            return Message(code=Code.BAD_REQUEST)
        if id != res.get_id():
            logger.error(f'Invalid id type: {id}')
            return Message(code=Code.BAD_REQUEST)
        try:
            newval = TlvDecoder.decode_value(res.get_type(), value_bytes)
            logger.debug(f'Setting new value of resource {id} to {newval}')
            res.update(newval)
            return Message(code=Code.CHANGED)
        except Exception as e:
            logger.error(f'Failed to decode value: {e}')
            return Message(code=Code.BAD_REQUEST)

    @staticmethod
    def decode_multi_resource(res_type, payload):
        """Decode a multi-resource payload"""
        instances = {}
        while payload:
            tlv_type, inst, value_bytes, payload = TlvDecoder.decode_tlv(payload)
            if tlv_type != TlvType.RESOURCE_INSTANCE.value:
                raise Exception(f'Invalid TLV type: {tlv_type}')
            newval = TlvDecoder.decode_value(res_type, payload)
            instances[inst] = newval
        return instances

    @staticmethod
    def update_multi_resource(request, multi_res):
        if request.opt.content_format != MediaType.TLV.value:
            raise Exception(f'Invalid content format: {request.opt.content_format}')
        try:
            tlv_type, id, inst_payload = TlvDecoder.decode_tlv(request.payload)
        except:
            logger.error('Failed to decode TLV')
            return Message(code=Code.BAD_REQUEST)
        if tlv_type != TlvType.MULTIPLE_RESOURCE.value:
            raise Exception(f'Invalid TLV type: {tlv_type}')
        if id != multi_res.get_id():
            raise Exception(f'Invalid id: {id}')
        try:
            # Decode/validate all instances before changing the object
            instances = TlvDecoder.decode_multi_resource(multi_res.get_type(), inst_payload)
            logger.debug(f'Updating multi-resource {id} with {instances}')
            multi_res.update(instances)
            return Message(code=Code.CHANGED)
        except Exception as e:
            logger.error(f'Failed to decode resource instances: {e}')
            return Message(code=Code.BAD_REQUEST)

    @staticmethod
    def update_object(request, obj_inst):
        """Update resources of an object instance from a TLV-encoded CoAP message"""
        if request.opt.content_format != MediaType.TLV.value:
            logger.error(f'Invalid content format: {request.opt.content_format}')
            return Message(code=Code.NOT_ACCEPTABLE)
        payload = request.payload
        resources = {}
        try:
            # Decode/validate all resources before changing the object
            while payload:
                tlv_type, res_id, value_bytes, payload = TlvDecoder.decode_tlv(payload)
                if res_id in obj_inst.get_resources():
                    res_type = obj_inst.get_resource(res_id).get_type()
                    if tlv_type == TlvType.RESOURCE_VALUE.value:
                        # Decode a resource value
                        resources[res_id] = TlvDecoder.decode_value(res_type, value_bytes)
                    elif tlv_type == TlvType.MULTIPLE_RESOURCE.value:
                        # Decode a multi-resource
                        resources[res_id] = TlvDecoder.decode_multi_resource(res_type, value_bytes)
                    else:
                        raise Exception(f'Invalid TLV type: {tlv_type}')
                else:
                    logger.debug(f'Skipping optional resource {res_id}')
            logger.debug(f'Updating object with {resources}')
            obj_inst.update(resources)
            return Message(code=Code.CHANGED)
        except Exception as e:
            logger.error(f'Failed to decode resource: {e}')
            return Message(code=Code.BAD_REQUEST)
