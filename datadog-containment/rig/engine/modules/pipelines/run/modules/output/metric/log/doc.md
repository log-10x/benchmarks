---
icon: material/math-log
---

Publish [TenXSummary](https://doc.log10x.com/api/js/#TenXSummary) instance values as metric counters to a target log4j2 appender.
    
The specified appender can write values to any [log4j2 destination](https://logging.apache.org/log4j/2.x/manual/appenders.html) as INFO messages using micrometer's [simple](https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/java/io/micrometer/core/instrument/simple/SimpleMeterRegistry.java#L181) format.
