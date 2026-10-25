#!/bin/bash
# The two-arm run with moved lines on warm (research TWO_ARM_METHOD_WARM.md): phases-two-arm.sh unchanged, with
# each arm's frozen node also data_warm (compose.warm.yaml) and the recipe rendered with tierDownPlacement 'warm'
# (TD_PLACEMENT), whose tier_down template arm B's overflow template copies. The rig's containers and volumes are
# removed before and after.
#   MCP=<log10x-mcp> GH_TOKEN=... ENGINE_IMAGE=<image> RESULTS=<dir> [M=6] phases-two-arm-warm.sh
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export WARM=1 ARM_B=1 TD_PLACEMENT=${TD_PLACEMENT:-warm}
"$HERE/run.sh" clean
"$HERE/phases-two-arm.sh"
rc=$?
"$HERE/run.sh" mark phases_exit "\"rc\":$rc"
[ -e "${RESULTS:?}/.down.done" ] || "$HERE/run.sh" down
"$HERE/run.sh" clean
exit $rc
