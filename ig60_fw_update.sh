#!/bin/sh
#
# Basic IG60 Update Script for LwM2M client
#
# This script is intended as a template for providing the external firmware update
# function to the LwM2M client.  It currently applies an swupdate (SWU) package
# to the opposite of the current 'bootside'.  The script returns an exit code that
# is the LwM2M update state result.
#

# Make verbose log
set -x

UPDATEFILE=$1

# Call the built-in 'fw_update' script
# -v: verbose
# -m: method (full)
# -x r: extra options - prevent auto-reboot
fw_update -v -m full -x r "${UPDATEFILE}"
EXIT_STATUS=$?

# Delete the update file
rm -f ${UPDATEFILE}

# Check 'fw_update' exit code
if [ ${EXIT_STATUS} -eq 0 ]; then
    exit 1 # LwM2M update result = UPDATE_RESULT_SUCESS
else
    echo "Failed to perform swupdate"
    exit 8 # LwM2M result = UPDATE_RESULT_FAILED
fi
