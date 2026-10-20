#!/bin/bash
# Indexed events by index and service over the last N hours (default 3), Datadog's usage metric.
H=${1:-3}
curl -s -G -H "DD-API-KEY: $DD_API_KEY" -H "DD-APPLICATION-KEY: $DD_APP_KEY" https://$DD_API_HOST/api/v1/query --data-urlencode "from=$(( $(date +%s) - H*3600 ))" --data-urlencode "to=$(date +%s)" --data-urlencode "query=sum:datadog.estimated_usage.logs.ingested_events{*} by {datadog_index,service,datadog_is_excluded}.as_count().rollup(sum, 3600)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status'), [(s['scope'], sum(p[1] or 0 for p in s['pointlist'])) for s in d.get('series',[])])"
