# Engine side: naming granularity and literal anchoring


Computed from two published release assets, `otel-sample-templates.json` and
`otel-sample-encoded.log`, at tag `otel-sample-v1`. The engine is never run.
Reproduce with `python bench/engine_side.py`.


## 0. What the two assets are, measured


| quantity | value |
|---|---|
| templates defined | 2,896 |
| distinct templates referenced by the encoded file | 2,896 |
| defined and never referenced | 0 |
| referenced with no definition | 0 |
| duplicate template hashes | 0 |
| hashes containing a comma | 0 (the parser depends on 0) |

The three counts are equal and both residuals are zero, so the templates file is
the dictionary the encoding run wrote for its own output rather than a library
that existed beforehand. Two consequences, both binding on everything below:

  1. Section 1's resolution rate is a consistency check between two artifacts of
     one run. It cannot come out below 1.0 unless the published assets are
     mismatched, so it is reported as a gate and not as a falsifier.
  2. How the symbol library behind these templates was produced, and whether it
     was compiled with sight of this stream, is not disclosed in the release and
     is not established anywhere in this repository. Reading section 1 as
     evidence that the library covers unseen statements is unsupported. The
     experiment that would support it is a run against a library compiled
     without the statements being encoded, it needs the engine, and it is listed
     as future work.

## 1. Resolution (consistency gate C1)


Every encoded record leads with `~<templateHash>`. Resolution is a lookup of
that hash against the templates file.

| quantity | value |
|---|---|
| events | 159,454 |
| resolved to a template | 159,454 |
| unresolved | 0 |
| malformed records | 0 |
| resolution | 1.0000 |

C1: PASS (0 records failed to resolve). Per section 0 this is an
internal-consistency check on the published artifacts, not a measurement of what
the symbol library covers.

## 2. Symbol content: message body against envelope


Each template covers a whole Fluentd/Kubernetes record. The `log` field holds the
application message; the rest is an envelope of container, image, pod and label
values. Measuring them together pads the literal count with deployment values,
so they are measured apart. A variable slot is an occurrence of `$`. A literal
token is a piece that survives splitting on `$` and on whitespace and the JSON
structural characters `, : " { } [ ] /`. Counts move with that rule, so the rule
is stated rather than assumed.

| portion | literal tokens (median) | alphanumeric literals (median) | variable slots (median) | templates with no alphanumeric literal |
|---|---:|---:|---:|---:|
| message body | 16 | 15 | 4 | 12 |
| envelope | 57 | 43 | 31 | 0 |
| whole record | 72 | 58 | 35 | 0 |

2,398 of 2,896 templates (82.8%) carry a digit welded to a variable slot inside
the envelope: image-tag, registry-host and pod-name fragments left behind after the
variable parts were replaced. Those literals are values of this deployment, not text
from the emitting statement, and a redeploy that changes an image tag or a pod hash
changes the template, so it changes the content hash, so it changes the name. That
is the same identity property this benchmark scores Drain on, and on this artifact
set part of the engine's template identity has it.

On the message body alone, 12 of 2,896 templates (0.41%) carry no alphanumeric literal at all.
Most are fragments of pretty-printed configuration output, where a line of the
record is a brace or a quoted key. An earlier form of this page claimed that no
template lacks literal content. That was true only with the envelope counted, and
it is withdrawn here.

F-anchor: holds. Worst bucket is "2 to 10" at 0.0112 against a floor of 0.05.

## 3. Naming granularity across frequency


Templates bucketed by how many events use them. The columns describe how much of
the emitting statement each name pins down, measured on the message body alone.
There is no resolution column here: per section 0 it is 1.0 in every bucket by
construction of the assets and it would say nothing.

| events per template | templates | events | share of stream | alphanumeric body literals (median) | body variable slots (median) | no alphanumeric body literal |
|---|---:|---:|---:|---:|---:|---:|
| used once | 2,647 | 2,647 | 0.0166 | 15 | 4 | 10 |
| 2 to 10 | 178 | 577 | 0.0036 | 12 | 4 | 2 |
| 11 to 100 | 32 | 1,200 | 0.0075 | 19 | 6 | 0 |
| 101 to 1,000 | 13 | 3,892 | 0.0244 | 17 | 5 | 0 |
| over 1,000 | 26 | 151,138 | 0.9478 | 19.5 | 6.5 | 0 |

2,647 of 2,896 templates (91.4%) are used exactly once, and they account for 1.66% of the stream. Re-keyed on the message body
alone, dropping the envelope entirely, 2,562 of 2,837 distinct bodies (90.3%) still
occur exactly once, so the granularity is a property of the message rather than of
deployment values.

F-degrade: holds. Median alphanumeric body literals is 15 for templates used once against 19.5 for templates used over a thousand times, a ratio of 0.77 against a floor of 0.50.
A name for a rare shape pins down about as much source text as a name for a
common one on this sample. What that does NOT show is where the name came from:
these artifacts cannot distinguish a name drawn from a compiled statement from a
name the encoder assigned by some other route.

## 4. Line reconciliation (consistency gate C2)


Raw lines outnumber events because multi-line records are grouped. A template
that seals a multi-line event holds several newline-separated line templates,
and an event built from it accounts for that many raw lines. A stack trace
becomes one composite event with one template and one pattern. Unlike C1 this
gate reaches outside the pair: it depends on every template's line span summing
to the line count of the third published asset, which the first two do not
contain.

| quantity | value |
|---|---|
| templates spanning several lines | 79 |
| widest template span, in lines | 97 |
| events built from a multi-line template | 26,370 |
| events | 159,454 |
| raw lines implied by template spans | 197,430 |
| continuation lines absorbed into group heads | 37,976 |
| raw lines counted in the published asset | 197,430 |
| **C2** | **PASS** |

159,454 events plus 37,976 continuation lines equals 197,430 raw lines.

## What this establishes


1. Naming granularity. The engine gives this stream 2,896 names for 159,454 events, and 2,647 of those names are used exactly once. Re-keyed on
   the message body alone the singleton share is 90.3%. Name assignment does not wait for repetition.
2. Literal anchoring, scoped. On the message body, 2,884 of 2,896 templates
   carry alphanumeric literal text, at a median of 15 tokens, and that median does not fall with rarity.
3. Grouping. A multi-line record is sealed into one event with one name, and the
   arithmetic closes against the raw asset exactly.

## What this does NOT establish


1. Library coverage. Section 1 is a consistency check between two co-generated
   artifacts. It says nothing about a statement the library has not seen, which is
   the adversarial case. The held-out experiment needs the engine and is future
   work.
2. Provenance of the library. Whether the symbol library behind these templates was
   compiled with sight of this stream is not disclosed in the release assets and is
   not established here.
3. Where the name comes from. The anchoring statistics show that names carry source
   text. They cannot show that the text was drawn from a compiled statement rather
   than derived some other way, because both would look like this from outside.
4. Cross-instance agreement. Two engine deployments handed disjoint halves of one
   stream were never run here. That is the direct counterpart of the Drain split in
   `results/identity.md` and it is future work.
5. Order invariance. A content hash of a template drawn from a pinned symbol
   library is order-invariant by construction. Measuring it would restate the
   construction, so this repository omits the exercise on purpose.
6. Stability of a name across engine versions, library revisions, or redeployment.
   Section 2 shows the last of those three is a live risk on this artifact set: 82.8% of templates carry deployment values in their
   envelope literals, so a new image tag or pod hash moves the name.

How to read this beside the Drain table. `results/identity.md` asks whether two
independently mined names for one line are the same string, which is agreement.
This page asks a weaker and prior question, whether a name exists at all and how
much source text it pins down, which is coverage and granularity. The buckets share
boundaries but partition different event sets: the engine's are whole records,
including multi-line groups, while Drain's are per-line message shapes. Read them
as two questions, not as two columns of one axis.

Prior art, stated so the claim stays narrow: template plus values storage is
long established (CLP/YScope, US10484506B2), and template extraction from log
text is long established (Drain, Spell, IPLoM). The claim on this page is about
naming granularity and literal anchoring on one sample, not about either of those.

