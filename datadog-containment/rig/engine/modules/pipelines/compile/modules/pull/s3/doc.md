---
icon: fontawesome/brands/aws
---

Pulls S3 objects to disk for [compile](https://doc.log10x.com/compile/) pipeline [scanning](https://doc.log10x.com/compile/scan/). Objects may be archives and binaries the [archive](https://doc.log10x.com/compile/scanner/archive/) scanner expands, or symbol unit tars from earlier compiles, linked into the library with [mergeExistingUnits](https://doc.log10x.com/compile/link/#mergeexistingunits).

Objects are listed and downloaded with the [AWS CLI](https://docs.aws.amazon.com/cli/) set per entry by [s3PullCommand](https://doc.log10x.com/compile/pull/s3/#s3pullcommand). The CLI's credential chain and `--endpoint-url` (S3-compatible stores) apply.

A key may carry a pin: `releases/app.jar#versionId=<id>` pulls that object version, `releases/app.jar@sha256:<64 hex>` fails the pull when the content differs. The fetch manifest records each object's key, version id, ETag and sha256, with `pinned: true` for a pinned key.

A pull that lists keys or prefixes fails when the CLI cannot run, exits non-zero, a key is not found or a prefix matches nothing.
