-- The offloaded objects, read in place.
--
-- The S3 engine takes the column names from the JSON the collector wrote:
-- the jsonlogencoding extension in body_with_inline_attributes mode writes
-- {"body": ..., "logAttributes": {...}} per record, as one JSON array per
-- object. `service` and `day` are not in the file at all; they come from the
-- object path, which is why use_hive_partitioning is on.
DROP TABLE IF EXISTS default.otel_logs_cold;
CREATE TABLE default.otel_logs_cold
(
  body           String,
  logAttributes  Map(String, String),
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('http://cse-minio:9000/coldlogs/**.json', 'minioadmin', 'minioadmin', 'JSONEachRow')
SETTINGS use_hive_partitioning = 1;

-- The S3 engine rejects ALIAS columns, so the rename to the ClickStack column
-- names is a view. The Merge table below reads the view, not the S3 table.
DROP VIEW IF EXISTS default.otel_logs_coldv;
CREATE VIEW default.otel_logs_coldv AS
SELECT toDateTime64(toUInt64OrZero(logAttributes['TimestampSec']), 9) AS Timestamp,
       CAST(service AS LowCardinality(String))                        AS ServiceName,
       body                                                           AS Body,
       CAST(logAttributes['SeverityText'] AS LowCardinality(String))  AS SeverityText,
       logAttributes                                                  AS LogAttributes,
       day                                                            AS day
FROM default.otel_logs_cold;

-- Hot and cold as one table. `_table` names the side a row came from.
DROP TABLE IF EXISTS default.otel_logs_all;
CREATE TABLE default.otel_logs_all
(
  Timestamp     DateTime64(9),
  ServiceName   LowCardinality(String),
  Body          String,
  SeverityText  LowCardinality(String),
  LogAttributes Map(String, String),
  day           Date
) ENGINE = Merge(default, '^(otel_logs|otel_logs_coldv)$');

-- The cold side of the counts table, one pass over the objects.
INSERT INTO default.counts_by_type (Minute, ServiceName, tenx_hash, message_pattern, source, cnt)
SELECT toStartOfMinute(Timestamp)       AS Minute,
       ServiceName,
       LogAttributes['tenx_hash']       AS tenx_hash,
       LogAttributes['message_pattern'] AS message_pattern,
       'cold'                           AS source,
       count()                          AS cnt
FROM default.otel_logs_coldv
GROUP BY Minute, ServiceName, tenx_hash, message_pattern;
