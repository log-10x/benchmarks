# Retriever Query Console

A local query console for the Log10x Retriever. Submits queries via SQS or REST, tracks progress via CloudWatch Logs, and exports queries as curl, CLI, SQS, or CronJob commands.

Two modes: a **web GUI** with Monaco editor and live query log, and a **CLI** for scripting and terminal workflows.

## Prerequisites

- Python 3.8+
- `boto3`, required for SQS submission and CloudWatch log polling (`pip3 install boto3`)
- AWS credentials configured (`aws configure` or environment variables)

## Quick Start

**Web GUI:**

```bash
python3 console.py --serve
```

Opens at `http://localhost:8080` with autocomplete, sample queries, live log streaming, and export to curl/CLI/SQS/CronJob.

**CLI:**

```bash
python3 console.py \
  --search 'severity_level=="ERROR"' --since 30m \
  --bucket my-bucket --queue-url $LOG10X_QUERY_QUEUE_URL --follow
```

## Files

| File | Description |
|------|-------------|
| `console.py` | Server and CLI entry point |
| `index.html` | Web GUI (served by `console.py --serve`) |
| `test_e2e.py` | End-to-end tests |

## Documentation

Full CLI options, REST API reference, and sample queries: [Defining Queries](https://doc.log10x.com/apps/retriever/query/)
