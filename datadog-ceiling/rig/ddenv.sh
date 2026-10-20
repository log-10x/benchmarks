#!/bin/bash
# Exports the run org's Datadog keys from SSM into the environment of the command, never
# printing them: DD_API_KEY (intake and the Receiver's metrics), DD_APP_KEY (queries with
# DD_API_KEY), DD_SITE. DD_PAT is unset so every query uses the key pair.
set -euo pipefail
g() { aws ssm get-parameter --region us-east-1 --profile l1x-admin --with-decryption --name "$1" --query Parameter.Value --output text; }
export DD_API_KEY="$(g /l1x/tooling/datadog-run-api-key)"
export DD_APP_KEY="$(g /l1x/tooling/datadog-run-app-key)"
export DD_SITE=us5.datadoghq.com
export DD_API_HOST=api.us5.datadoghq.com
unset DD_PAT DATADOG_PAT
exec "$@"
