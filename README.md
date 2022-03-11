# lwm2m_python_client

This repository contains both an LWM2M client library and IG60 client implementation written in Python 3.

# Installation

Prerequisite: Requires Python 3.7+

On a development machine, run ``pip install -r requirements.txt`` to install the necessary requirements.
The IG60 Laird Linux image will include all the necessary Python pre-requisites.

# Usage

## Running The Client

The IG60 LwM2M Python client is pre-installed on the IG60LLSD image.  There
also exists a help script that manages the client lifecycle by copying
the client to a writeable location (on first boot), and copying an updated
client when the client has been updated (see Object 9, below).  Run the
helper script with the ``--help`` option to see all available command
line arguments:

    ig60_lwm2m2_client.sh --help

For example, to connect an IG60 as client named "my-ig60" to
connect an LWM2M server running on 192.168.1.2 and port 5684:

    ig60_lwm2m2_client.sh --server 192.168.1.2 --server-port 5684 -e my-ig60

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
The IG60 LwM2M client implements both push (blockwise transfer via resource 0) and pull (download
via URI written to resource 1) to obtain the firmware update image, which is downloaded to a temporary
file (``/tmp/update.bin``).  When the firmware update is executed via resource 2, the IG60 LwM2M client
calls an external shell script (``ig60_fw_update.sh``) passing the path of the firmware image as the
single argument to the script.  This source includes an implementation of the script which will apply
the update image as an swupdate package and change the bootside in U-Boot once the update has
been successfully applied.  (The update script must be in the ``PATH`` to be executed).

Note that the LwM2M client supports 3 methods to download the firmware image:
- "Push" via CoAP blockwise-transfer to resource 0
- "Pull" from URI via CoAP (e.g., "coap://lwm2m.us.cumulocity.com/123456")
- "Pull" from URI via HTTP(S) (e.g., "http://lwm2m.us.cumulocity.com/123456")

It is **highly recommended** to use the last method as CoAP transfer is limited to a maximum
of 1024-byte blocks at a time and is **very** slow.  Also note that it has been observed that
the Cumulocity HTTPS server will present a self-signed certificate, which will (correctly)
cause the client download to fail.

### Software Management (Object 9)
The IG60 LwM2M client exposes a single instance of Object 9 to enable
in-place update of the client itself.  The update package must be a
gzipped-tarball containing the new client executable (Python egg named
'lwm2m-python-client') and a checksum file 'checksums.txt' containing the
SHA256 hash of the client.  An update package can be transferred via
the "package" resource (/9/0/2) or via a URI (/9/0/3).  Once the
update has been verified (state reports 3 "Verified"), the update should
be installed (via resource /9/0/4) and activated (via resource /9/0/10).
Once activated, the client will exit and signal to the helper script
that the update should be copied, then the helper script will restart
the (new) client.  Note that the client cannot be de-activated or
uninstalled (as this would be counterproductive).

### Cellular Connectivity (Object 10) and APN Profile (Object 11)
The IG60 LwM2M client will expose the cellular connectivity status (object 10) and APN profile (object 11)
if the IG60 LTE modem is present and has been activated.  The status will always report a single APN profile
instance (/11/0 when activated).  This single instance of the APN profile only supports setting the
preferred APN and authentication settings (via the Ofono LTE interface).

### WLAN Connectivity Profiles (Object 12)
The IG60 LwM2M client provides the WLAN connectivity profiles via object 12.  This object supports
creating, writing, reading, and deleting WLAN connections, which are mapped to Network Manager connections
on the IG60 wireless interface (wlan0).  The following resource settings and their corresponding Network
Manager settings are provided:
* Interface name (0): Must be 'wlan0'
* Enable (1): Sets the Network Manager 'autoconnect' setting (True to enable, False to disable)
* Status (3): Reports the connection status when read
* BSSID (4): Reports the WLAN0 MAC address when read
* SSID (5): Set to the connection SSID (note that per the LwM2M specification this is a string, so non-ASCII characters cannot be supported)
* Mode (8): Can be set but only Client (1) is supported
* Channel (9): Sets the Network Manager 'channel' setting
* Standard (14): Can be set but is ignored; the WLAN interface supports 802.11ac
* Authentication mode (15): Only None (0) and PSK (1) are supported (since the LwM2M specification does not provide the ability to configure EAP credentials)
* WPA Key Phrase (18): The PSK used when authentication is set to PSK

### Bearer Selection (Object 13)
The IG60 LwM2M client exposes the Bearer Selection object to control
the priority list of network interfaces that are used by the client
to connect to the server (where the lowest instance ID has the
highest priority).  This object only implements resource 0,
"Preferred Communications Bearer".  By default this resource contains
a single instance of "0: Auto", which indicates the client should
connect on one of the 3 available interfaces (Ethernet, WLAN, or
LTE).

If this resource is written with one or more instances, the priority of
the instances will be observed and the client will attempt to re-register
with the server on the interface with the highest priority, then the
next (if the connection cannot be established), etc.  Only the following
resource values will be observed (any others will be ignored):

* 0: Auto (default)
* 4: 3GPP LTE
* 7: WLAN
* 8: Ethernet

### System Log (Object 10259)
The IG60 LwM2M client exposes a single instance of the System Log object
(10259) to enable reading of the journald log.  The 'Read All' resource
(/10259/0/1) will read the entire log, and 'Read' (/10259/0/2) will read
the entire log on the first read (from client startup) and then will
return incremental logs.  Other resources are not implemented.

***NOTE:*** When using a Leshan server, the default maximum incoming message
size is 8192, and should be increased (by changing ```COAP.MAX_RESOURCE_BODY_SIZE```
in the server properties file) to be able to read larger system logs.
