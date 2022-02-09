# lwm2m_python_client

This repository contains both an LWM2M client library and IG60 client implementation written in Python 3.

# Installation

Prerequisite: Requires Python 3.7+

On a development machine, run ``pip install -r requirements.txt`` to install the necessary requirements.
The IG60 Laird Linux image will include all the necessary Python pre-requisites.

# Usage

## Installation
To install the client on an IG60, simply copy this source tree to the local filesystem on an IG60
running Laird Linux; e.g.:

    scp -r * root@192.168.1.10:/root

## Running The Client

Run ``python ig60_lwm2m_client.py --help`` command to display the command-line options available.
For example, to connect an IG60 as client named "my-ig60" with a local IP address of 192.168.1.10
to an LWM2M server running on 192.168.1.2

    python ig60_lwm2m_client.py -a 192.168.1.10 -p 5682 -s 192.168.1.2 -sp 5684 -e my-ig60

Note that you **must** specify a local address (``--address``) and port (``--port``) to bind the client to; this
determines the interface (Ethernet, WLAN, or LTE) that the client will utilize.

**IMPORTANT:** If the LwM2M client is run behind a firewall (to the server, e.g., to a cloud-based
LwM2M service such as Cumulocity), the firewall **must** support UDP NAT traversal ("hole punching"),
and the client lifetime must be configured (via the bootstrap) to be less than the NAT timeout interval
applied by the firewall.

# Features
## LwM2M Client Library
The LwM2M client library is located in the ``lwm2m`` directory and includes support for the following:

* Basic implementation of LwM2M resources  (```resource.py```), objects (``object.py``)
* TLV encoding and decoding of resources and objects (``tlv.py``)
* A functional client (``client.py``)
* Secure connections using DTLS (``dtls.py``)
* Bootstrap operation (``bootstrap.py``)

## IG60 LwM2M Client
When run on an IG60, in addition to the features listed above, the client provides the following LwM2M
objects as detailed.

### Security (Object 0), Server (Object 1)
When run in bootstrap mode, the IG60 LwM2M client allows a bootstrap server to configure only the
server URI, security mode, secret key (DTLS PSK), and lifetime.

### Device (Object 3)
The IG60 LwM2M client implements all the mandatory "Device" resources (e.g., "Reboot"), and additional
resources such as the manufacturer, model, as well as some memory statistics.

### Connectivity Monitoring (Object 4)
The IG60 LwM2M client implements the Network Bearer resource (indicating the connection based on the
bound IP address as LTE, WLAN, or Ethernet) and available Bearers.  If the LTE modem is available and has
been enabled prior to launching the client, additional applicable resources such as the RSSI and cellular
identifiers will be readable.

### Firmware Update (Object 5)
The IG60 LwM2M client implements both push (blockwise transfer via resource 0) and pull (HTTP download
via URI written to resource 1) to obtain the firmware update image, which is downloaded to a temporary
file (``/tmp/update.bin``).  When the firmware update is executed via resource 2, the IG60 LwM2M client
calls an external shell script (``ig60_fw_update.sh``) passing the path of the firmware image as the
single argument to the script.  This source includes an implementation of the script which will apply
the update image as an swupdate package and change the bootside in U-Boot once the update has
been successfully applied.  (The update script must be in the ``PATH`` to be executed).
