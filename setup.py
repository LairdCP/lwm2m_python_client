#!/usr/bin/python

from setuptools import setup

setup(
    name='lwm2m_python_client',
    version='0.1',
    py_modules=[
        'lwm2m/__init__',
        'lwm2m/base',
        'lwm2m/bearer',
        'lwm2m/block',
        'lwm2m/bootstrap',
        'lwm2m/cellular',
        'lwm2m/client',
        'lwm2m/connmon',
        'lwm2m/device',
        'lwm2m/dtls',
        'lwm2m/fwupdate',
        'lwm2m/object',
        'lwm2m/resource',
        'lwm2m/tlv',
        'lwm2m/wlan',
        '__init__',
        '__main__',
        'ig60_bearer',
        'ig60_cellular',
        'ig60_connmon',
        'ig60_device',
        'ig60_fwupdate',
        'ig60_lwm2m_client',
        'ig60_network',
        'ig60_wlan'
        ]
      )
