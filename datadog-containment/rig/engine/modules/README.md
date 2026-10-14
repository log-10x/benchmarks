# Log10x Modules

Core module definitions for the [Log10x](https://www.log10x.com/?utm_source=github&utm_medium=readme&utm_campaign=modules&utm_content=hero) engine, the brain that powers log cost analysis, filtering, and optimization. Start with the [MCP Server](https://doc.log10x.com/apps/mcp/), it guides you through installing and configuring the apps below based on k8s discovery of your environment.

**Full Documentation**: [doc.log10x.com](https://doc.log10x.com/)

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            Log10x Engine                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                          Applications                               │  │
│  │                                                                     │  │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────┐   │  │
│  │  │     Runtime Apps        │  │        Setup / Tools            │   │  │
│  │  │                         │  │                                 │   │  │
│  │  │  ├─ Reporter (DaemonSet)│  │  ├─ Dev (local CLI)             │   │  │
│  │  │  ├─ Receiver (sidecar)  │  │  ├─ Compiler (symbol generation)│   │  │
│  │  │  │  Filter + Compact    │  │  └─ MCP scaffold (validation)   │   │  │
│  │  │  └─ Retriever (S3 query)│  │                                 │   │  │
│  │  └─────────────────────────┘  └─────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                           Pipelines                                 │  │
│  │                                                                     │  │
│  │  ┌───────────────────────────────────────────────────────────────┐  │  │
│  │  │  COMPILE: Pull ──► Scan ──► Link ──► Push                     │  │  │
│  │  │           (GitHub, Docker, Helm) → (AST, Bytecode) → Symbols  │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  ┌───────────────────────────────────────────────────────────────┐  │  │
│  │  │  RUN: Input ──► Transform ──► Aggregate ──► Output            │  │  │
│  │  │       (Forwarders, Analyzers) → (Script) → (Events, Metrics)  │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
modules/
├── apps/                           # Pre-built applications (flat topology)
│   ├── compiler/                   # Symbol compilation app
│   ├── dev/                        # Local preview CLI
│   ├── mcp/                        # stdin/stdout scaffold used by the MCP server
│   ├── reporter/                   # DaemonSet pre-SIEM cost insight
│   ├── receiver/                  # Sidecar: Filter + Compact modes
│   └── retriever/                   # S3 data lake indexing + on-demand query
│
├── pipelines/                      # Core pipeline definitions
│   ├── compile/                    # Symbol compilation pipeline
│   │   └── modules/                # pull/, scanner/, link/
│   ├── run/                        # Event processing pipeline
│   │   └── modules/                # input/, transform/, aggregate/, output/
│   ├── doc/                        # Documentation generation pipeline
│   └── shared/                     # Shared utilities
│
└── lib/                            # Shared libraries
    └── script/                     # JavaScript libraries
```

## Applications

### In-Cluster Applications

Deployed alongside log forwarders (Fluentd, Fluent Bit, Filebeat, Logstash).

| App | Purpose | Documentation | Run Guide |
|-----|---------|---------------|-----------|
| **Reporter** | Cost attribution metrics (DaemonSet, pre-SIEM, not in log path) | [Overview](https://doc.log10x.com/apps/reporter/) | [Run](https://doc.log10x.com/apps/reporter/run/) |
| **Receiver** | Two modes: Filter (lossy, budget sampling, mute files) and Compact (lossless volume reduction via SIEM-side expand plugin, where the destination supports it) | [Overview](https://doc.log10x.com/apps/receiver/) | [Run](https://doc.log10x.com/apps/receiver/run/) |

```
┌─────────────────────────────────────────────────────────────────┐
│                    In-Cluster Deployment                         │
│                                                                  │
│   Reporter (DaemonSet) ─── tails pre-SIEM ────► Metrics          │
│                                                                  │
│   Application ──► Log Forwarder ──► Receiver ──► Analyzer       │
│   (logs)          (Fluentd,         (sidecar,     (Splunk,       │
│                    Filebeat)         Filter or     Elastic)      │
│                                      Compact)                    │
│                                                                  │
│   Metrics: ───────────────────────► Prometheus ────► Grafana    │
└─────────────────────────────────────────────────────────────────┘
```

### Storage & Agent Applications

| App | Purpose | Documentation | Run Guide |
|-----|---------|---------------|-----------|
| **Retriever** | S3 data lake indexing & queries | [Overview](https://doc.log10x.com/apps/retriever/) | [Run](https://doc.log10x.com/apps/retriever/run/) |
| **MCP** | Agent control plane, reads Reporter metrics, commands Receiver/Retriever via GitOps | [Overview](https://doc.log10x.com/apps/mcp/) | [Run](https://doc.log10x.com/apps/mcp/tools/) |

For agentless SIEM-side cost analysis, use the [log10x-mcp](https://github.com/log-10x/log10x-mcp) server's `log10x_poc_from_siem_submit` tool.

### Setup & Developer Tools

| App | Purpose | Documentation | Run Guide |
|-----|---------|---------------|-----------|
| **Dev** | Local CLI to preview savings on your logs | [Overview](https://doc.log10x.com/apps/dev/) | [Run](https://doc.log10x.com/apps/dev/run/) |
| **Compile** | Generate symbol libraries from source code (optional, default library covers 150+ frameworks) | [Overview](https://doc.log10x.com/compile/) | [Test](https://doc.log10x.com/compile/test/) / [Deploy](https://doc.log10x.com/compile/deploy/) |

## Pipelines

### Compile Pipeline

Scans source code and generates symbol files for log template extraction.

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  PULL    │───►│  SCAN    │───►│  LINK    │───►│  PUSH    │
│          │    │          │    │          │    │          │
│ GitHub   │    │ javaParser│   │ Cross-ref│    │ S3       │
│ Docker   │    │ pythonAST │   │ analysis │    │ Local    │
│ Helm     │    │ ANTLR     │   │          │    │          │
│ Local    │    │ bytecode  │   │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Documentation**: [Compile Pipeline](https://doc.log10x.com/compile/)

| Module Type | Examples | Docs |
|-------------|----------|------|
| Pull | github, docker, helm, local | [Pull Modules](https://doc.log10x.com/compile/pull/) |
| Scanner | javaParser, pythonAST, scalameta, antlr, bytecode | [Scanner Modules](https://doc.log10x.com/compile/scan/) |

### Run Pipeline

Processes log events in real-time for optimization, filtering, and reporting.

```
┌──────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐
│  INPUT   │───►│ TRANSFORM │───►│ AGGREGATE │───►│  OUTPUT  │
│          │    │           │    │           │    │          │
│ Forwarder│    │ Script    │    │ Group by  │    │ Events   │
│ Analyzer │    │ Fields    │    │ template  │    │ Metrics  │
│ S3       │    │ Timestamp │    │ app       │    │ Stream   │
│ Stdin    │    │ Structure │    │ level     │    │          │
└──────────┘    └───────────┘    └───────────┘    └──────────┘
```

**Documentation**: [Run Pipeline](https://doc.log10x.com/run/)

| Module Type | Examples | Docs |
|-------------|----------|------|
| Input/Forwarder | fluentd, fluentbit, filebeat, logstash, otel | [Forwarders](https://doc.log10x.com/run/input/forwarder/) |
| Input/Analyzer | splunk, elastic, datadog, cloudwatchLogs | [Analyzers](https://doc.log10x.com/run/input/analyzer/) |
| Transform | script, fields, timestamp, structure | [Transform](https://doc.log10x.com/run/transform/) |
| Output/Event | stdout, file, http, unix | [Event Output](https://doc.log10x.com/run/output/event/) |
| Output/Metric | prometheus, datadog, cloudwatch | [Metric Output](https://doc.log10x.com/run/output/metric/) |

## Configuration Reference

All configuration formats and specifications are documented at [doc.log10x.com/config](https://doc.log10x.com/config/).

| Topic | Description | Documentation |
|-------|-------------|---------------|
| **Module Configuration** | module.yaml structure and settings | [Module Config](https://doc.log10x.com/config/module/) |
| **App Configuration** | app.yaml structure and configFolders | [App Config](https://doc.log10x.com/config/app/) |
| **YAML Format** | YAML syntax and +include directives | [YAML Reference](https://doc.log10x.com/config/yaml/) |
| **JavaScript** | Scripting API and functions | [JavaScript](https://doc.log10x.com/config/javascript/) |
| **Symbol Files** | Symbol file format and usage | [Symbols](https://doc.log10x.com/config/symbol/) |
| **Folder Structure** | Configuration folder conventions | [Folders](https://doc.log10x.com/config/folder/) |
| **Matching Rules** | Pattern matching syntax | [Match](https://doc.log10x.com/config/match/) |
| **CLI Options** | Command-line interface reference | [CLI](https://doc.log10x.com/config/cli/) |

## API Reference

| Topic | Description | Documentation |
|-------|-------------|---------------|
| **Input API** | TenXObject structure and input handling | [Input API](https://doc.log10x.com/api/input/) |
| **Output API** | TenXSummary structure and output handling | [Output API](https://doc.log10x.com/api/output/) |
| **JavaScript API** | Scripting functions and objects | [JavaScript API](https://doc.log10x.com/api/js/) |
| **Compile API** | Compiler programmatic interface | [Compile API](https://doc.log10x.com/api/compile/) |

## Architecture

For detailed architecture documentation:

| Topic | Documentation |
|-------|---------------|
| **Engine Architecture** | [Architecture Overview](https://doc.log10x.com/apps/) |
| **Pipeline Architecture** | [Pipeline Design](https://doc.log10x.com/engine/pipeline/) |
| **Module System** | [Module Architecture](https://doc.log10x.com/engine/module/) |
| **Launcher Options** | [Launcher (sidecar, job, function)](https://doc.log10x.com/engine/launcher/) |
| **GitOps Integration** | [GitOps Workflows](https://doc.log10x.com/engine/gitops/) |

## Statistics

| Category | Count |
|----------|-------|
| Total Directories | 180+ |
| YAML Configuration Files | 275+ |
| Applications | 10 |
| Pipeline Types | 4 |
| Input Modules | 15+ |
| Output Modules | 20+ |
| Scanner Modules | 12+ |
| Supported Forwarders | 5 |
| Supported Analyzers | 6 |

## Quick Links

| Resource | URL |
|----------|-----|
| **Documentation Hub** | [doc.log10x.com](https://doc.log10x.com/) |
| **Getting Started** | [doc.log10x.com/home](https://doc.log10x.com/home/) |
| **Installation** | [doc.log10x.com/install](https://doc.log10x.com/install/) |
| **Applications** | [doc.log10x.com/apps](https://doc.log10x.com/apps/) |
| **Configuration** | [doc.log10x.com/config](https://doc.log10x.com/config/) |
| **API Reference** | [doc.log10x.com/api](https://doc.log10x.com/api/) |

## License

This repository is licensed under the [MIT License](LICENSE).

### Log10x Product License Required

This repository contains module definitions for the Log10x engine. While these
definitions are open source, **running Log10x requires a commercial license.**

| What's Open Source | What Requires License |
|-------------------|----------------------|
| Module YAML definitions | Log10x engine/runtime |
| Documentation files | Log10x apps (Reporter, Receiver, Retriever) |
| Schema definitions | Executing pipelines |

**Get a Log10x License:**
- [Pricing](https://www.log10x.com/pricing?utm_source=github&utm_medium=readme&utm_campaign=modules&utm_content=footer)
- [Documentation](https://doc.log10x.com)
- [Contact Sales](mailto:sales@log10x.com)
