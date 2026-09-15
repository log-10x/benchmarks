#!/usr/bin/env bash
#
# Replays EventJsonExtractor's offset arithmetic over eclipse parsson 1.1.7,
# the version the engine builds against, and prints the drop range it computes
# for `drop:tag`.
#
#   ./run.sh          the six shapes, one after another through one parser
#   ./run.sh sweep    every alignment from 0 to 2600 against 0, 1, 2, 5 and 30
#                     escapes, printing only the cases where the computed range
#                     is not the true range
#
# Needs a JDK and the two jars, which gradle leaves in the usual cache.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE="${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2/files-2.1"
PARSSON="$(find "$CACHE/org.eclipse.parsson" -name 'parsson-1.1.7.jar' | head -1)"
JSONAPI="$(find "$CACHE/jakarta.json" -name 'jakarta.json-api-*.jar' | head -1)"
[ -n "$PARSSON" ] && [ -n "$JSONAPI" ] || { echo "parsson 1.1.7 and jakarta.json-api are not in the gradle cache" >&2; exit 1; }
CP="$PARSSON:$JSONAPI"
javac -cp "$CP" -d "$HERE" "$HERE/Probe.java" "$HERE/Records.java"
java -cp "$CP:$HERE" Probe "$@"
