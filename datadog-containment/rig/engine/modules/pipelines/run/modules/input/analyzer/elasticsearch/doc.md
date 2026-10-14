---
icon: simple/elasticsearch
---

Reads events from Elasticsearch clusters and transforms them into TenXObjects.

Instances of this [module](https://doc.log10x.com/engine/module/) define a connection to a hosted/on-premises 
ElasticSearch cluster from which events to retrieve, as well as the querying logic used
such as chronological direction, start values, time ranges, and page size
of each API request sent.
 
ElasticSearch inputs commonly run within scheduled jobs (e.g., k8s CronJob) 
to retrieve a recent sample amount of events (e.g., 200MB in the last 10min) to [transform](https://doc.log10x.com/run/transform/) into TenXObjects as part of the [Dev app](https://doc.log10x.com/apps/dev/) app.


