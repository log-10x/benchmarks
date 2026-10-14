---
title: "Validate"
description: "How log10x_validate runs your candidate config, and how to reproduce a failing run locally"
icon: material/play-circle-outline
---

When an agent calls `log10x_validate`, the server spawns `tenx @apps/mcp` as a subprocess. The subprocess reads log lines on stdin and writes `TenXObject`s + `TenXTemplate`s as JSON lines on stdout. No filesystem, no network. The server parses the output and returns it to the agent.

You almost never invoke `@apps/mcp` directly, the server handles the subprocess lifecycle. This page exists for debugging: when `log10x_validate` returns something unexpected and you want to see exactly what the engine did with your candidate config.

## Reproduce a `log10x_validate` run locally

Pipe the same log lines the agent piped, against the same candidate config:

```bash
echo "<your log line>" | tenx @apps/mcp
```

Stack your candidate config after the base app:

```bash
echo "<your log line>" | tenx @apps/mcp @/path/to/your-config.yaml
```

The stdout is exactly what `log10x_validate` returned to the agent. Diff against the agent's reported output to find where they diverge, typically either (a) the agent's interpretation of the output, or (b) a config stacking order issue.

## Why `@apps/mcp` is narrower than `@apps/dev`

`@apps/mcp` omits `httpCode` and `lookup` enrichment because their embedded scripts reference engine builtins that move between releases. Keeping the validate runtime pinned to stable primitives means `log10x_validate` behaves consistently across engine upgrades, agents get the same answer in March as they did in January.

If you need richer enrichment for local exploration (the full pipeline including HTTP code classification and lookup tables), use [Dev](https://doc.log10x.com/apps/dev/) directly instead of `@apps/mcp`.
