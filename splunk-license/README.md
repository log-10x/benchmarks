# Splunk license-metered volume, with and without 10x in front

Splunk bills on what its license meter counts, which is neither the file size on disk nor what the forwarder sent. This test sends the same capture to Splunk twice, once as it is and once after the 10x engine has turned it into compact events, and reads the meter for each. The compact arm metered 63.91% fewer bytes, and every compact event read back as its original text.

Compact events cannot be read without their template dictionary, so the dictionary goes to Splunk too and its metered bytes count against the compact arm. The 10x Splunk app expands each compact event back to its original text at search time.

## Result

License-metered bytes for the run on 2026-10-10, from Splunk's own license usage log.

| Arm | What Splunk ingested | Metered bytes | GB/day |
|---|---|---:|---:|
| Baseline | the capture as it is | 214,841,731 | 0.200087 |
| Compact | compact events | 74,338,244 | 0.069233 |
| Compact | template dictionary | 3,194,224 | 0.002975 |
| Compact | total | 77,532,468 | 0.072208 |

The compact total is 63.91% below the baseline. Measured as files on disk, the same two arms give 63.87%. The gap is line breaks, which the meter does not count and which make up more of the smaller compact arm (0.21% against 0.09%).

- All 157,228 compact events came back byte-identical to the text that went in, with the search head in UTC and in the instance's own timezone.
- Per Kubernetes container with at least 100 events, the reduction ran from 57.86% for ad to 69.27% for opensearch. These figures leave the dictionary out, which makes each one slightly better than in a deployment.

## How it was measured

The data is a 215,039,161 byte capture of 197,430 lines from 36 Kubernetes containers in a small demo cluster, each line in a Fluentd envelope. Both arms went through the same Universal Forwarder to one Splunk Enterprise 10.4.3 instance on the download trial license, into separate indexes on the same license day. On this version the daily `type=RolloverSummary` line carries only the day's total, so the split by index comes from the per-minute `type=Usage` records, as the Monitoring Console does. The per-index bytes add up to the rollup's daily total of 292,374,199 bytes exactly.

## Limits

- One capture from one demo cluster on one license day. A production estate has its own data, sourcetypes and forwarder topology.
- The figure is ingest only. Indexed storage, search speed and retention were not measured.
- Splunk Cloud, which meters by a different path, was not tested.

## Run it

The license figures can be recomputed from the saved rollup lines without Splunk or Docker:

```sh
# from the repository root
python3 splunk-license/report.py --dir splunk-license --data splunk-license/data \
  --results splunk-license/results-2026-10-10 --check

# the full run: a throwaway Splunk container, torn down at the end
splunk-license/run.sh
```

A full run needs Docker, about 10 GB of free disk and roughly two hours, most of it waiting for the license day to end. The run touches no existing Splunk.

The full record, with every Splunk setting, the encode settings the app needs and all the results tables, is in [RECORD.md](RECORD.md).
