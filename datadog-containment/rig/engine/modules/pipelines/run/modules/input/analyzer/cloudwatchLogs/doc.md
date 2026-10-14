---
icon: fontawesome/brands/aws
---

Configures an AWS CloudWatch Logs input from which to read events to transform into typed [TenXObjects](https://doc.log10x.com/api/js/#TenXObject).

Instances of this [module](https://doc.log10x.com/engine/module/) define a connection to an AWS CloudWatch Logs service
from which to retrieve log messages, as well as the querying logic used
such as chronological direction, start values, time ranges, and page size
of each API request sent.

Cloudwatch Logs inputs commonly run within scheduled jobs (e.g., k8s CronJob) 
to retrieve a recent sample amount of events (e.g., 200MB in the last 10min) to [transform](https://doc.log10x.com/run/transform/) into TenXObjects as part of the [Dev app](https://doc.log10x.com/apps/dev/) app.
