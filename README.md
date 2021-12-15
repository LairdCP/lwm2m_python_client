
# lwm2m_python_client

An LWM2M client library and basic implementation written in Python 3.

# Installation

Prerequisite: Requires Python 3.7+

run ``pip install -r requirements.txt`` to install the necessary requirements.

# Usage

## Running The Client

Use the ``test.py`` command to connect LWM2M server listening on udp://localhost:5683 (for instance, a [Leshan](http://www.eclipse.org/leshan/) server).
Note that the underlying aiocoap server requires an address to bind to for incoming requests (by default this is 127.0.0.1:5683).
