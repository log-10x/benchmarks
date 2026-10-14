---
icon: material/web
---

Enrich TenXObjects with an extracted HTTP [status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes), if present in the underlying event's text. 

This module applies a heuristic that extracts HTTP status codes from tokenized log events in two phases: template-level identification to locate a valid candidate token, and instance-level extraction to parse the code value. It uses configurable arrays for validation and preclusion, ensuring efficiency (O(1) per check) and minimizing false positives.

This process ensures the [template](https://doc.log10x.com/run/template/) identifies the correct [variable token](https://doc.log10x.com/run/transform/structure/#variables) position once, and instances extract the HTTP code efficiently via direct access using the [token](https://doc.log10x.com/api/js/#TenXBaseObject+token) function.

Use the [lookup initializer](https://doc.log10x.com/run/initialize/lookup/) to map codes (e.g., 200) to messages (e.g., `OK`). 