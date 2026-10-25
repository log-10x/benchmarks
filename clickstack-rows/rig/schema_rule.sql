-- Arm B's table, a copy of otel_logs, with a copy of its counts view.
CREATE TABLE IF NOT EXISTS default.otel_logs_rule AS default.otel_logs;

CREATE TABLE IF NOT EXISTS default.counts_by_type_rule AS default.counts_by_type;

CREATE MATERIALIZED VIEW IF NOT EXISTS default.counts_by_type_rule_mv
TO default.counts_by_type_rule (Minute DateTime, ServiceName LowCardinality(String), tenx_hash String, message_pattern String, source LowCardinality(String), cnt UInt64) AS
SELECT toStartOfMinute(Timestamp)          AS Minute,
       ServiceName,
       LogAttributes['tenx_hash']          AS tenx_hash,
       LogAttributes['message_pattern']    AS message_pattern,
       'hot'                               AS source,
       count()                             AS cnt
FROM default.otel_logs_rule
GROUP BY Minute, ServiceName, tenx_hash, message_pattern;
