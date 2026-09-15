-- Counts per type, fed from the hot inserts. Created BEFORE any data flows, so
-- the materialized view sees every hot insert. The cold rows never pass through
-- an insert into ClickHouse, so their counts are added after the run by the
-- INSERT ... SELECT in schema_cold.sql.
CREATE TABLE IF NOT EXISTS default.counts_by_type
(
  Minute DateTime,
  ServiceName LowCardinality(String),
  tenx_hash String,
  message_pattern String,
  source LowCardinality(String),
  cnt UInt64
) ENGINE = SummingMergeTree(cnt)
ORDER BY (Minute, ServiceName, tenx_hash, message_pattern, source);

CREATE MATERIALIZED VIEW IF NOT EXISTS default.counts_by_type_hot_mv
TO default.counts_by_type (Minute DateTime, ServiceName LowCardinality(String), tenx_hash String, message_pattern String, source LowCardinality(String), cnt UInt64) AS
SELECT toStartOfMinute(Timestamp)          AS Minute,
       ServiceName,
       LogAttributes['tenx_hash']          AS tenx_hash,
       LogAttributes['message_pattern']    AS message_pattern,
       'hot'                               AS source,
       count()                             AS cnt
FROM default.otel_logs
GROUP BY Minute, ServiceName, tenx_hash, message_pattern;
