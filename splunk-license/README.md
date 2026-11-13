# Splunk license-metered volume, with and without 10x in front

An ingest-based Splunk Enterprise license is measured in daily indexing volume, the uncompressed data indexed each day. 10x stores the text each log statement repeats once, in a dictionary, and sends every event as its values. The 10x app for Splunk expands each event to its original text at search time. For one public Kubernetes log capture sent through a Universal Forwarder, Splunk's license meter counted 63.91% fewer bytes in compact form, dictionary included.

## What the license meter counted

| Reading on Splunk's license meter | Value |
|---|---|
| Capture sent as is | 214,841,731 bytes |
| Compact events | 74,338,244 bytes |
| Template dictionary | 3,194,224 bytes |
| Compact form in total | 77,532,468 bytes |
| Reduction | 63.91% |
| Lowest container (`ad`) | 57.86% |
| Highest container (`opensearch`) | 69.27% |

The meter counts the text of each event. The capture is 215,039,161 bytes on disk and 214,841,731 on the meter, and the difference is its 197,430 line breaks. Each compact event was metered at the length of its own text, with event time set from the line.

- The template dictionary is counted like any other data, and its 3,194,224 bytes are inside the compact total.
- The two container rows cover events only, because the dictionary is not split by container, and containers with fewer than 100 events are not ranked.
- Through the app's own macro, 157,228 of 157,228 compact events expanded byte-identical, with the search head set to UTC and again to Etc/GMT-2.

## How the meter was read

[The capture](https://github.com/log-10x/config/releases/tag/otel-sample-v2) is 215,039,161 bytes and 197,430 lines of output from 36 Kubernetes containers in an OpenTelemetry demo cluster. The engine joins the lines of a multi-line event into one event, so the 197,430 lines are 157,228 events, and the run stops if any line is left unassigned. Both forms went through the same Universal Forwarder into the same Splunk Enterprise 10.4.3 instance on the same license day. The 10x engine writes the compact form of the capture as two files, the compact events and the template dictionary, and the forwarder sends each to an index of its own. Splunk Enterprise runs in a container, and both arms were metered on the same license day. Splunk's license usage log reports usage per index, and the per-index entries add up to the day's rollup total to the byte: 292,374,199.

## Limits

- The 63.91% belongs to this capture.
- The figure is ingest only. Indexed storage, search speed and retention were not measured.
- The meter reading here is from Splunk Enterprise, and Splunk Cloud, workload pricing included, is outside this benchmark.

## Rerunning the benchmark

```sh
# from the repository root
python3 splunk-license/report.py --dir splunk-license --data splunk-license/data \
  --results splunk-license/results-2026-10-10 --check

# the full run: a throwaway Splunk container, torn down at the end
splunk-license/run.sh
```

The repository's CI recomputes the license figures from the kept rollup lines, so an edited results table fails. The run needs Docker and about 10 GB of disk and takes about two hours, most of it waiting for the license day to end.

The full record, with every Splunk setting, the encode settings the app needs and all the results tables, is in [RECORD.md](RECORD.md).
