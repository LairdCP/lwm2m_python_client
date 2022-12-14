"""Cellular Network and APN (Object 10, 11) resources
"""

# LwM2M Object 10 (Cellular Connectivity) resource and instance definitions

LWM2M_CELLULAR_CONN_OBJECT = 10

LWM2M_CELLULAR_CONN_INSTANCE = 0

LWM2M_CELLULAR_RESOURCE_SMSC_ADDRESS = 0
LWM2M_CELLULAR_RESOURCE_DISABLE_RADIO_PERIOD = 1
LWM2M_CELLULAR_RESOURCE_MODULE_ACTIVATION_CODE = 2
LWM2M_CELLULAR_RESOURCE_VENDOR_SPECIFIC_EXTENSIONS = 3
LWM2M_CELLULAR_RESOURCE_PSM_TIMER = 4
LWM2M_CELLULAR_RESOURCE_ACTIVE_TIMER = 5
LWM2M_CELLULAR_RESOURCE_SERVING_PLM_RATE_CONTROL = 6
LWM2M_CELLULAR_RESOURCE_EDRX_PARAMS_IU = 7
LWM2M_CELLULAR_RESOURCE_EDRX_PARAMS_WB_S1 = 8
LWM2M_CELLULAR_RESOURCE_EDRX_PARAMS_NB_S1 = 9
LWM2M_CELLULAR_RESOURCE_EDRX_PARAMS_A_GB = 10
LWM2M_CELLULAR_RESOURCE_ACTIVATED_PROFILES = 11

# LwM2M Object 11 (APN Connection Profile) resource and instance definitions

LWM2M_APN_PROFILE_OBJECT = 11

LWM2M_APN_PROFILE_INSTANCE = 0

LWM2M_APN_PROFILE_RESOURCE_NAME = 0
LWM2M_APN_PROFILE_RESOURCE_APN = 1
LWM2M_APN_PROFILE_RESOURCE_AUTO_SELECT = 2
LWM2M_APN_PROFILE_RESOURCE_ENABLE_STATUS = 3
LWM2M_APN_PROFILE_RESOURCE_AUTH_TYPE = 4
LWM2M_APN_PROFILE_RESOURCE_USERNAME = 5
LWM2M_APN_PROFILE_RESOURCE_SECRET = 6
LWM2M_APN_PROFILE_RESOURCE_RECONNECT_SCHED = 7
LWM2M_APN_PROFILE_RESOURCE_VALIDITY = 8
LWM2M_APN_PROFILE_RESOURCE_CONN_ESTABLISH_TIME = 9
LWM2M_APN_PROFILE_RESOURCE_CONN_ESTABLISH_RESULT = 10
LWM2M_APN_PROFILE_RESOURCE_CONN_ESTABLISH_REJECT_CAUSE = 11
LWM2M_APN_PROFILE_RESOURCE_CONN_END_TIME = 12
LWM2M_APN_PROFILE_RESOURCE_BYTES_SENT = 13
LWM2M_APN_PROFILE_RESOURCE_BYTES_RECEIVED = 14
LWM2M_APN_PROFILE_RESOURCE_IP_ADDRESS = 15
LWM2M_APN_PROFILE_RESOURCE_PREFIX_LENGTH = 16
LWM2M_APN_PROFILE_RESOURCE_SUBNET_MASK = 17
LWM2M_APN_PROFILE_RESOURCE_GATEWAY = 18
LWM2M_APN_PROFILE_RESOURCE_PRIMARY_DNS_ADDR = 19
LWM2M_APN_PROFILE_RESOURCE_SECONDARY_DNS_ADDR = 20
LWM2M_APN_PROFILE_RESOURCE_QCI = 21
LWM2M_APN_PROFILE_RESOURCE_VENDOR_SPECIFIC_EXT = 22
LWM2M_APN_PROFILE_RESOURCE_PACKETS_SENT = 23
LWM2M_APN_PROFILE_RESOURCE_PDN_TYPE = 24
LWM2M_APN_PROFILE_RESOURCE_APN_RATE_CONTROL = 24

LWM2M_APN_AUTH_TYPE_PAP = 0
LWM2M_APN_AUTH_TYPE_CHAP = 1
LWM2M_APN_AUTH_TYPE_PAP_OR_CHAP = 2
LWM2M_APN_AUTH_TYPE_NONE = 3

LWM2M_APN_PDN_TYPE_NON_IP = 0
LWM2M_APN_PDN_TYPE_IPV4 = 1
LWM2M_APN_PDN_TYPE_IPV6 = 2
LWM2M_APN_PDN_TYPE_IPV4V6 = 3

