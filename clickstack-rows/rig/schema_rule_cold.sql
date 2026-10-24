-- Arm B's bucket, read in place the way clickstack-e2e/conf/schema_cold.sql reads arm A's.
DROP TABLE IF EXISTS default.otel_logs_rule_cold;
CREATE TABLE default.otel_logs_rule_cold
(
  body           String,
  logAttributes  Map(String, String),
  service        LowCardinality(String),
  day            Date
) ENGINE = S3('http://cse-minio:9000/coldrule/**.json', 'minioadmin', 'minioadmin', 'JSONEachRow')
SETTINGS use_hive_partitioning = 1;

DROP VIEW IF EXISTS default.otel_logs_rule_coldv;
CREATE VIEW default.otel_logs_rule_coldv AS
SELECT toDateTime64(toUInt64OrZero(logAttributes['TimestampSec']), 9) AS Timestamp,
       CAST(service AS LowCardinality(String))                        AS ServiceName,
       body                                                           AS Body,
       CAST(logAttributes['SeverityText'] AS LowCardinality(String))  AS SeverityText,
       logAttributes                                                  AS LogAttributes,
       day                                                            AS day
FROM default.otel_logs_rule_cold;
