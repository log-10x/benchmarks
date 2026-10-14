---
icon: material/code-json
---

Extracts [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values from text/binary files using plain text tokenization or [Jackson](https://github.com/FasterXML/jackson) parsers.

Parses input by splitting lines with delimiters or using a [JsonFactory](https://fasterxml.github.io/jackson-core/javadoc/2.8/com/fasterxml/jackson/core/JsonFactory.html) for structured token reading.

When source code for a log format is unavailable (e.g., third-party services), a sample log can be scanned at compile time as an optional input to extract its symbols. Nothing is learned at run time.

!!! note "Size limit"

    Files over 50KB are skipped to avoid slow parsing of machine-generated content.
