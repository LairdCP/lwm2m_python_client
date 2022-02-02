#!/bin/sh
#
# Basic IG60 Update Script for LwM2M client
#
# This script is intended as a template for providing the external firmware update
# function to the LwM2M client.  It currently applies an swupdate (SWU) package
# to the opposite of the current 'bootside'.  The script returns an exit code that
# is the LwM2M update state result.
#

# Make verbose log, fail on uncaught errors
set -xe

UPDATEFILE=$1
UPDATE_EXCLUDE="2 3" # Ignore U-Boot environment

cleanup_and_fail(){
    echo $1
    rm -f ${UPDATEFILE}
    exit 8 # LwM2M result = UPDATE_RESULT_FAILED
}

# Read the configured bootside and actual root filesystem partition in use
BOOTSIDE=`fw_printenv -n bootside` || cleanup_and_fail "Cannot read bootside"

if [ ${BOOTSIDE} == "a" ]; then
    UPDATESIDE="b"
else
    UPDATESIDE="a"
fi

UPDATESEL="stable,main-${UPDATESIDE}"

# Apply update
echo "Applying update ${UPDATESEL} from ${UPDATEFILE}"
swupdate -b "${UPDATE_EXCLUDE}" -l 4 -v -i "${UPDATEFILE}" -e "${UPDATESEL}" || cleanup_and_fail "Failed to perform swupdate"

# Change the bootside
fw_setenv bootside ${UPDATESIDE} || cleanup_and_fail "Cannot set bootside"

# Delete the update file
rm -f ${UPDATEFILE}

exit 1 # LwM2M update result = UPDATE_RESULT_SUCESS
