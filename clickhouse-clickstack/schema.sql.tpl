-- The ClickStack `otel_logs` schema, copied from ClickHouse's own documentation:
-- https://clickhouse.com/docs/use-cases/observability/clickstack/ingesting-data/schemas
-- (the DDL its `_snippets/_schema_otel_logs.md` renders).
--
-- Two substitutions and one removal, and nothing else:
--
--   __TABLE__  the arm and codec this copy holds
--   __CODEC__  the column compression codec under test: ZSTD(1) is the
--              ClickStack default, ZSTD(3) and LZ4 are the other two settings.
--              `Timestamp` keeps its Delta(8) first stage in every case.
--   TTL        the published DDL ends `TTL toDateTime(Timestamp) + ${TABLES_TTL}`.
--              Nothing here tests retention and the placeholder has no value
--              outside a ClickStack install, so the TTL clause is dropped. Every
--              other line, including the two block-number settings and all eight
--              skip indexes, is as published.

CREATE TABLE IF NOT EXISTS bench.__TABLE__
(
  `Timestamp` DateTime64(9) CODEC(Delta(8), __CODEC__),
  `TraceId` String CODEC(__CODEC__),
  `SpanId` String CODEC(__CODEC__),
  `TraceFlags` UInt8,
  `SeverityText` LowCardinality(String) CODEC(__CODEC__),
  `SeverityNumber` UInt8,
  `ServiceName` LowCardinality(String) CODEC(__CODEC__),
  `Body` String CODEC(__CODEC__),
  `ResourceSchemaUrl` LowCardinality(String) CODEC(__CODEC__),
  `ResourceAttributes` Map(LowCardinality(String), String) CODEC(__CODEC__),
  `ScopeSchemaUrl` LowCardinality(String) CODEC(__CODEC__),
  `ScopeName` String CODEC(__CODEC__),
  `ScopeVersion` LowCardinality(String) CODEC(__CODEC__),
  `ScopeAttributes` Map(LowCardinality(String), String) CODEC(__CODEC__),
  `LogAttributes` Map(LowCardinality(String), String) CODEC(__CODEC__),
  `EventName` String CODEC(__CODEC__),
  `__hdx_materialized_k8s.cluster.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.cluster.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.container.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.container.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.deployment.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.deployment.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.namespace.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.namespace.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.node.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.node.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.pod.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.pod.name'] CODEC(__CODEC__),
  `__hdx_materialized_k8s.pod.uid` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.pod.uid'] CODEC(__CODEC__),
  `__hdx_materialized_deployment.environment.name` LowCardinality(String) MATERIALIZED ResourceAttributes['deployment.environment.name'] CODEC(__CODEC__),
  `ResourceAttributeItems` Array(String) ALIAS arrayMap((arr) -> concat(arr.1, '=', arr.2), ResourceAttributes::Array(Tuple(String, String))),
  `ScopeAttributeItems` Array(String) ALIAS arrayMap((arr) -> concat(arr.1, '=', arr.2), ScopeAttributes::Array(Tuple(String, String))),
  `LogAttributeItems` Array(String) ALIAS arrayMap((arr) -> concat(arr.1, '=', arr.2), LogAttributes::Array(Tuple(String, String))),
  INDEX idx_trace_id TraceId TYPE text(tokenizer = 'array'),
  INDEX idx_res_attr_key mapKeys(ResourceAttributes) TYPE text(tokenizer = 'array'),
  INDEX idx_res_attr_items ResourceAttributeItems TYPE text(tokenizer = 'array'),
  INDEX idx_scope_attr_key mapKeys(ScopeAttributes) TYPE text(tokenizer = 'array'),
  INDEX idx_scope_attr_items ScopeAttributeItems TYPE text(tokenizer = 'array'),
  INDEX idx_log_attr_key mapKeys(LogAttributes) TYPE text(tokenizer = 'array'),
  INDEX idx_log_attr_items LogAttributeItems TYPE text(tokenizer = 'array'),
  INDEX idx_lower_body lower(Body) TYPE text(tokenizer = 'splitByNonAlpha')
)
ENGINE = MergeTree
PARTITION BY toDate(Timestamp)
ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)
SETTINGS index_granularity = 8192, ttl_only_drop_parts = 1, enable_block_number_column = 1, enable_block_offset_column = 1;
