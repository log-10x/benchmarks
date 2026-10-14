---
icon: material/bucket-outline
---

The S3 Logs module enables reading log and trace events from a single [AWS S3](https://aws.amazon.com/s3/) object for analysis and transformation into [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

### :material-hammer-wrench: How It Works

The S3 Logs input fetches a single S3 object by key using the [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html) API. The object's line-delimited content is then split into individual events for processing.

```mermaid
graph LR
    A["Timer<br/>Trigger"] --> B["GetObject<br/>API"]
    B --> C["Stream<br/>Content"]
    C --> D["Split by<br/>Newlines"]
    D --> E["Transform to<br/>TenXObjects"]
    E --> F["Close<br/>Route"]

    classDef trigger fill:#2563eb88,stroke:#1d4ed8,color:#ffffff
    classDef api fill:#ea580c88,stroke:#c2410c,color:#ffffff
    classDef process fill:#05966988,stroke:#047857,color:#ffffff

    class A trigger
    class B api
    class C,D,E process
    class F trigger
```

### :material-key: Authentication

The module supports the [AWS default credential provider chain](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/credentials-chain.html):

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Java system properties
3. Web identity token (for EKS/IRSA)
4. Shared credentials file (`~/.aws/credentials`)
5. ECS container credentials
6. EC2 instance profile credentials

Explicit credentials can also be provided via configuration:

```yaml
s3Logs:
  - name: MyS3LogsInput
    bucket: my-bucket
    key: logs/app.log
    awsAccessKeyID: AKIAIOSFODNN7EXAMPLE
    awsSecretKey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### :material-speedometer: Backpressure Controls

Control resource usage with backpressure options:

| Option | Description | Default |
|--------|-------------|---------|
| `totalBytesLimit` | Max bytes to read | 50MB |
| `totalEventsLimit` | Max events to read | 10000 |
| `totalDuration` | Max time to keep input open | 5min |

### :material-code-tags: Example Configuration

```yaml
tenx: run

include: run/modules/input/analyzer/s3Logs

s3Logs:
  - name: ProductionLogs
    bucket: my-company-logs
    key: logs/2024/01/15/application.log
    awsRegion: us-west-2
    totalBytesLimit: $=parseBytes("100MB")
    totalEventsLimit: 50000
    printProgress: true
```

### :material-link-variant: Related Modules

- [CloudWatch Logs Input](https://doc.log10x.com/run/input/analyzer/cloudwatchLogs/) - Read from CloudWatch Logs
- [Object Storage Query](https://doc.log10x.com/run/input/objectStorage/query/) - Query-based object storage access
