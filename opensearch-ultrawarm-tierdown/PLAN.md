# Plan: per-statement tier down to UltraWarm on Amazon OpenSearch Service

Order of calls, all through `osreq.py` (SigV4, every reading to `results/raw/requests.jsonl`).

1. `aws opensearch create-domain --cli-input-json file://plan/create-domain.json`
   (`__SOURCE_IP__` replaced with the run machine's address at create time).
   Poll `describe-domain` until `Processing: false`; record the Active time. Then
   poll `GET _cat/nodes?format=json` and `GET _warm` until warm nodes answer;
   record that time.
2. `PUT _index_template/tenx-tierdown-tpl` and `PUT _index_template/tenx-app-tpl`.
3. `PUT _plugins/_ism/policies/tenx-tier-down` and `.../tenx-keep`. The policies
   carry `ism_template`, so they must exist before the bootstrap indices.
4. `PUT tenx-tierdown-000001` and `PUT tenx-app-000001` with the bootstrap aliases.
   `GET _plugins/_ism/explain/tenx-*` shows both attached.
5. `POST _bulk` with `data/bulk.ndjson` (400 held to `tenx-tierdown`, 200 kept to
   `tenx-app`), then `POST tenx-*/_refresh` and `_cat/indices`.
6. Watch: every minute `_cat/indices?format=json&bytes=b`, `GET _hot`, `GET _warm`,
   `_plugins/_ism/explain/tenx-*`, `GET _ultrawarm/migration/_status?v`.
7. After `tenx-tierdown-000001` is in `_warm`: term query per held `tenx_hash`
   against it, `routeState` terms aggregation, `_source` compared to the bulk file.
8. `POST _dashboards/api/saved_objects/index-pattern/tenx-all` with
   `plan/index-pattern.json`; read it back; search the title it stores.
9. CloudWatch `AWS/ES` metrics for the domain (warm storage, migration force-merge
   latency, FreeStorageSpace), Cost Explorer by usage type. Repeat step 7 an hour later.
10. Delete the domain.
