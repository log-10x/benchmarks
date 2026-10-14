---
icon: material/origin
---

Adds a name to every event, made of the known words of the log statement that most likely wrote it, such as `Receive_ListRecommendations_for_product_ids`. Events from one statement share that name whatever IDs or timestamps they carry, unless a value that is itself a known word splits them. The [Reporter](https://doc.log10x.com/apps/reporter/) reports cost by this name, the [Receiver](https://doc.log10x.com/apps/receiver/) samples or mutes by it, and [metric outputs](https://doc.log10x.com/run/output/metric/) publish counts per name.

## :material-tag-outline: Fields { #pattern-identity-pattern-vs-template }

The module writes these fields on each event:

| Field | Example | Option |
|---|---|---|
| `message_pattern` | `Receive_ListRecommendations_for_product_ids` | [`symbolMessageField`](#symbolmessagefield), on in the shipped configuration |
| Pattern hash | An 11-character hash of the name, for joins and metric tags | [`symbolMessageHashField`](#symbolmessagehashfield), off by default; metrics carry it either way |
| Origin | `recommendation_server.py:ListRecommendations` | [`symbolOriginField`](#symboloriginfield), off by default |
| Skeleton | The message with `~` for each word of the name and `$` for each value | [`symbolSkeletonField`](#symbolskeletonfield), off by default |

A template is the exact shape of one line format, which [compact](https://doc.log10x.com/run/transform/#compact) uses to store events. One log statement can produce several templates. Templates of one statement that differ only in values outside the library, such as timestamps and numbers, share one name; a value made of library words is read as part of the name, as the browser names are in the Web example below.

In the engine's metrics, `tenx_hash` is the pattern hash. On a Splunk compact event, the field of that name holds the template hash.

## :material-target: Message Extraction

The module names each event in five steps, run in this order:

??? tenx-extractors "1. Pick the text"

    The module reads the field named by `inputField`, such as `log`, so envelope keys such as `stream` and `kubernetes` stay out of the name. With several fields listed, it reads the first one the event has.

    For a multi-line event, it reads the first line that holds a message. In a stack trace that is the exception line. The .NET console logger writes `info: cart.cartstore.ValkeyCartStore[0]` and then `GetCartAsync called with userId=8d3b2c1a` as two records, and the second one names the event.

??? tenx-symbolinitializer "2. Find the source"

    Each phrase the [symbol library](https://doc.log10x.com/compile/link/#symbol-library) knows points to the places in code that can print it. The module picks the place that best explains the line, comparing in this order:

    1. Words from the message itself. A phrase matched only inside a JSON value or brackets ranks lower, so a long error string carried in an attribute does not outweigh the short message it belongs to.
    2. The length of the longest phrase that place prints.
    3. How many distinct words of the line that place explains, and their total length.

    Any remaining tie resolves the same way on every run and every node.

??? tenx-safety "3. Check the evidence"

    The source is accepted when at least two words of the message match it; otherwise the event is named by step 5 and gets no origin. A path such as `/var/lib/app` counts as one word, and parts of IDs do not count. With [`symbolContexts`](#symbolcontexts) set to `any`, one word is enough.

??? tenx-text "4. Build the name"

    The name is the matched words in the order they appear, joined with `_`, up to [`symbolMaxLen`](#symbolmaxlen) characters (120 by default).

    - The name stops at a timestamp, a bracket or the end of the line, so request IDs, thread names and node IDs printed before the message stay out.
    - A logger or class name printed between the timestamp and the message stays in, as in `oteldemo_AdService_Targeted_ad_request_received_for`.
    - When the message quotes an exception after `:`, at most half the length goes to the quoted text, so two statements quoting the same exception keep different names.
    - Numbers, IDs, timestamps, repeated words and any word outside the symbol library never enter the name. A value that is itself a known word can, as the browser names do in the Web example below.

    A known word that is part of a value is skipped, so lines from `opensearch-0` and `opensearch-1` share one name:

    - a word joined by `-`, `_`, `.` or `$` to a number or another value, as in `req-b3e2` or `subdir2`;
    - a word inside a `host:port` such as `www.evernote.com:443`, or inside a path that has a value in it;
    - an upper-case code that mixes letters and digits, such as `L9ECAV7KIM`.

??? tenx-default "5. Fall back"

    - **One word found:** the name is the line's known words from the start of the message. Bracketed prefixes, `msg=`-style keys and [reserved](https://doc.log10x.com/run/transform/symbol/#symbolsequencereserved) words are skipped. A logger name such as `org.apache.kafka.log.LocalLog` is kept, since it often tells two statements apart.
    - **No known word:** the name is `template_` plus a hash of the line's shape, its fixed words and punctuation with the values removed. The name holds while the shape holds. A stack frame or other line listed in [`messageNegators`](#messagenegators) that arrives as its own event is named the same way.

The brackets, `key=value` separators, message keys and reserved words these steps use are options of the [Symbol](https://doc.log10x.com/run/transform/symbol/#symbolpreambleenclosures) unit, set in its config file.

:material-github: See the [JavaScript implementation](https://github.com/log-10x/modules/blob/main/pipelines/run/modules/initialize/message/message-template.js) of this module on Github.

## :material-swap-horizontal: When Names Change

A name stays the same across IDs, timestamps, nodes, restarts, pod renames and the order events arrive in. The same engine version, symbol library and configuration always give the same name. A name changes when:

- the statement's text changes in code;
- the symbol library is recompiled and a word on the line changes between value and known word;
- an engine upgrade changes the naming rules.

## :material-file-document-outline: Examples

=== ":simple-opentelemetry: OTel Demo"

    ```json
    {
      "stream": "stderr",
      "log": "2025-04-17 14:32:40,287 INFO [main] [recommendation_server.py:47] - Receive ListRecommendations for product ids:['L9ECAV7KIM', '0PUK6V6EV0']",
      "kubernetes": { "container_name": "recommendationservice", "namespace_name": "default" }
    }
    ```

    **Pattern:** `Receive_ListRecommendations_for_product_ids`

    **Origin:** `recommendation_server.py:ListRecommendations`

=== ":simple-dotnet: .NET"

    A header record from the .NET console logger, then the message:

    ```json
    { "stream": "stdout", "log": "info: cart.cartstore.ValkeyCartStore[0]", "kubernetes": { "container_name": "cart" } }
    { "stream": "stdout", "log": "      GetCartAsync called with userId=02fec73e-9f03-11f0-9b9e-a666c4b68b87", "kubernetes": { "container_name": "cart" } }
    ```

    **Pattern:** `GetCartAsync_called_with_userId`

    **Origin:** `ValkeyCartStore.cs:ValkeyCartStore`

=== ":fontawesome-brands-java: Java"

    ```json
    {
      "stream": "stdout",
      "log": "2025-10-01 20:12:37 - oteldemo.AdService - Targeted ad request received for [accessories] trace_id=262794c5d52cea66092b4d8de7d1c6ed span_id=11dc1636e05888c3 trace_flags=01 ",
      "kubernetes": { "container_name": "ad", "namespace_name": "default" }
    }
    ```

    **Pattern:** `oteldemo_AdService_Targeted_ad_request_received_for`

    **Origin:** `AdService.java:getAds`

=== ":material-web: Web"

    ```json
    {
      "stream": "stdout",
      "log": "192.168.43.96 - - [01/Aug/2025:22:21:50 +0000] \"GET /products/LensCleaningKit.jpg HTTP/1.1\" 200 101928 \"http://frontend-proxy:8080/\" \"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/133.0.0.0 Safari/537.36\"",
      "kubernetes": { "container_name": "image-provider", "namespace_name": "default" }
    }
    ```

    **Pattern:** `GET_HTTP_http_frontend_proxy_Mozilla_X_Linux_AppleWebKit_KHTML_like_Gecko_Safari`

    **Origin:** none
