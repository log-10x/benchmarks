#!/usr/bin/env python3
"""Which distribution is providing the `drain3` module, and at what version.

The `drain3` import name is provided by two distributions: upstream `drain3`
(logpai, pinned at 0.9.11 for the committed artifacts) and the maintained fork
`drain3-improved` (jpodivin). Both install the same module name, so
`importlib.metadata.version("drain3")` raises PackageNotFoundError under the
fork. Every script that prints the library version goes through here so a run
records which distribution it actually ran against.
"""

import importlib.metadata as _im

# Order matters only for the error message; exactly one of these is installed in
# a correctly built environment, because they occupy the same import name.
CANDIDATES = ("drain3", "drain3-improved")


def distribution() -> tuple[str, str]:
    """Return (distribution name, version) for whatever provides `drain3`."""
    for name in CANDIDATES:
        try:
            return name, _im.version(name)
        except _im.PackageNotFoundError:
            continue
    raise _im.PackageNotFoundError(
        "no distribution providing the drain3 module is installed; expected one "
        f"of {', '.join(CANDIDATES)}")


def label() -> str:
    """`drain3 0.9.11`, or `drain3-improved 0.10.0`. Printed on every artifact."""
    name, version = distribution()
    return f"{name} {version}"


if __name__ == "__main__":
    print(label())
