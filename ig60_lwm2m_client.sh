#!/bin/sh
#
# IG60 LwM2M Client Runner Script
#
# This script runthe IG60 LwM2M Python client, and manages the
# client lifecycle, including:
#
#   - Copying the initial client applciation from a read-only
#     location to a writeable partition
#   - Detecting when the client has been updated and copying in the
#     new version
#

INITIAL_EXE_PATH=/usr/bin       # Path for initial (read-only) executable
EXE_PATH=/gg/lwm2m              # Path to run and update executable
UPDATE_PATH=/tmp/swupdate       # Update location
EXE_NAME='lwm2m-python-client'  # EXE name
ENOPKG=65                       # Exit code indicates app update requested

# Make verbose log, fail on uncaught errors
set -xe

# Create executable path
mkdir -p ${EXE_PATH}

# Copy initial executable if it doesn't exist yet
if [ ! -r "${EXE_PATH}/${EXE_NAME}" ]; then
    cp -f "${INITIAL_EXE_PATH}/${EXE_NAME}" "${EXE_PATH}/${EXE_NAME}"
fi

while :; do
    if python "${EXE_PATH}/${EXE_NAME}" "$@" ; then
        # CLient returned success, pass it on
        exit 0
    else
        EXIT_STATUS=$?
        echo "${EXE_NAME} exited with code ${EXIT_STATUS}"
        if [ ${EXIT_STATUS} == ${ENOPKG} ]; then
            # Copy updated EXE
            cp -f "${UPDATE_PATH}/${EXE_NAME}" "${EXE_PATH}/${EXE_NAME}"
        else
            exit ${EXIT_STATUS}
        fi
    fi
done
