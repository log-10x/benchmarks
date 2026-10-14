# Log10x Configuration

Runtime configuration files for [Log10x](https://www.log10x.com/?utm_source=github&utm_medium=readme&utm_campaign=config&utm_content=hero) applications and pipelines. This is the main working directory where you configure and customize Log10x deployments.

**Full Documentation**: [doc.log10x.com/config](https://doc.log10x.com/config/)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Configuration Flow                              │
│                                                                         │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────────┐    │
│  │   apps/       │    │  pipelines/   │    │       data/           │    │
│  │               │    │               │    │                       │    │
│  │  config.yaml  │───►│  config.yaml  │───►│  symbols, samples     │    │
│  │  (app entry)  │    │  (modules)    │    │  templates            │    │
│  └───────────────┘    └───────────────┘    └───────────────────────┘    │
│         │                    │                        │                 │
│         └────────────────────┼────────────────────────┘                 │
│                              ▼                                          │
│                    ┌────────────────────┐                               │
│                    │   10x Engine       │                               │
│                    │                    │                               │
│                    │ log10x run/compile │                               │
│                    └────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
config/
├── apps/                      # Application entry points
│   ├── edge/                  # Edge applications
│   │   ├── optimizer/         # Log volume reduction
│   │   ├── receiver/          # Rate reduction & mute files
│   │   └── reporter/          # Cost attribution
│   ├── cloud/                 # Cloud applications
│   │   ├── reporter/          # Analyzer cost analysis
│   │   └── retriever/         # S3 data lake (index/query)
│   ├── compiler/              # Symbol compilation
│   └── dev/                   # Local development
│
├── pipelines/                 # Pipeline module configurations
│   ├── compile/               # Compile pipeline modules
│   │   ├── pull/              # Source retrieval (github, docker, helm)
│   │   ├── scanners/          # Code analysis (antlr, text, archive)
│   │   ├── link/              # Symbol linking
│   │   └── push/              # Artifact output
│   ├── run/                   # Run pipeline modules
│   │   ├── input/             # Event sources (forwarders, analyzers)
│   │   ├── initialize/        # Field enrichment (level, k8s, geoIP)
│   │   ├── aggregate/         # Event summarization
│   │   ├── receive/           # Policy enforcement
│   │   ├── output/            # Event & metric outputs
│   │   └── transform/         # Event processing
│   ├── gitops/                # GitOps workflow config
│   └── doc/                   # Documentation generation
│
├── data/                      # Runtime data
│   ├── sample/                # Sample log files for testing
│   ├── templates/             # Log templates
│   ├── compile/sources/       # Source code for compilation
│   └── shared/                # Shared assets
│
└── log4j2.yaml                # Engine logging configuration
```

## Applications

Application configs are entry points that include pipeline modules. Edit these to customize your deployment.

| Application | Config Path | Documentation |
|-------------|-------------|---------------|
| **Receiver** | `apps/receiver/config.yaml` | [Overview](https://doc.log10x.com/apps/receiver/) \| [Run](https://doc.log10x.com/apps/receiver/run/) |
| **Reporter** | `apps/reporter/config.yaml` | [Overview](https://doc.log10x.com/apps/reporter/) \| [Run](https://doc.log10x.com/apps/reporter/run/) |
| **Retriever** | `apps/retriever/*/config.yaml` | [Overview](https://doc.log10x.com/apps/retriever/) \| [Run](https://doc.log10x.com/apps/retriever/run/) |
| **Compiler** | `apps/compiler/config.yaml` | [Overview](https://doc.log10x.com/compile/) \| [Run](https://doc.log10x.com/compile/test/) |
| **Dev** | `apps/dev/config.yaml` | [Overview](https://doc.log10x.com/apps/dev/) \| [Run](https://doc.log10x.com/apps/dev/run/) |

## Pipeline Modules

### Compile Pipeline

| Module | Config Path | Documentation |
|--------|-------------|---------------|
| **Pull/GitHub** | `pipelines/compile/pull/github/` | [Pull Modules](https://doc.log10x.com/compile/pull/) |
| **Pull/Docker** | `pipelines/compile/pull/docker/` | [Pull Modules](https://doc.log10x.com/compile/pull/) |
| **Pull/Helm** | `pipelines/compile/pull/helm/` | [Pull Modules](https://doc.log10x.com/compile/pull/) |
| **Scanners** | `pipelines/compile/scanners/` | [Scanner Modules](https://doc.log10x.com/compile/scan/) |
| **Link** | `pipelines/compile/link/` | [Compile Pipeline](https://doc.log10x.com/compile/) |
| **Push** | `pipelines/compile/push/` | [Compile Pipeline](https://doc.log10x.com/compile/) |

### Run Pipeline

| Module | Config Path | Documentation |
|--------|-------------|---------------|
| **Input/Forwarders** | `pipelines/run/input/forwarder/` | [Forwarders](https://doc.log10x.com/run/input/forwarder/) |
| **Input/Analyzers** | `pipelines/run/input/analyzer/` | [Analyzers](https://doc.log10x.com/run/input/analyzer/) |
| **Input/Object Storage** | `pipelines/run/input/objectStorage/` | [Object Storage](https://doc.log10x.com/run/input/objectStorage/) |
| **Initialize** | `pipelines/run/initialize/` | [Initialize](https://doc.log10x.com/run/initialize/) |
| **Aggregate** | `pipelines/run/aggregate/` | [Aggregate](https://doc.log10x.com/run/aggregate/) |
| **Receive** | `pipelines/run/receive/` | [Receive](https://doc.log10x.com/apps/receiver/) |
| **Output/Event** | `pipelines/run/output/event/` | [Event Output](https://doc.log10x.com/run/output/event/) |
| **Output/Metric** | `pipelines/run/output/metric/` | [Metric Output](https://doc.log10x.com/run/output/metric/) |
| **Transform** | `pipelines/run/transform/` | [Transform](https://doc.log10x.com/run/transform/) |

## Configuration Reference

All configuration formats are documented at [doc.log10x.com/config](https://doc.log10x.com/config/).

| Format | Description | Documentation |
|--------|-------------|---------------|
| **YAML** | Primary config format with `+include` directives | [YAML Reference](https://doc.log10x.com/config/yaml/) |
| **JSON** | REST request format and schema definitions | [JSON Reference](https://doc.log10x.com/config/json/) |
| **JavaScript** | Custom scripting and expressions | [JavaScript](https://doc.log10x.com/config/javascript/) |
| **CLI** | Command-line arguments | [CLI Reference](https://doc.log10x.com/config/cli/) |

## Key Concepts

| Concept | Description | Documentation |
|---------|-------------|---------------|
| **App Configuration** | Entry point config with module includes | [App Config](https://doc.log10x.com/config/app/) |
| **Module Configuration** | Pipeline module settings | [Module Config](https://doc.log10x.com/config/module/) |
| **Symbol Files** | Compiled log templates | [Symbols](https://doc.log10x.com/config/symbol/) |
| **Folder Loading** | Load configs from disk folders | [Folders](https://doc.log10x.com/config/folder/) |
| **GitHub Loading** | Pull configs from GitHub repos | [GitHub](https://doc.log10x.com/config/github/) |
| **Pattern Matching** | Regex-based config parsing | [Match](https://doc.log10x.com/config/match/) |
| **GitOps Workflow** | Centralized config management | [GitOps](https://doc.log10x.com/engine/gitops/) |

## File Structure

Each module folder typically contains:

```
module-name/
├── config.yaml      # Default configuration
├── schema.json      # JSON Schema for validation
└── readme.md        # Module-specific documentation
```

## Getting Started

1. Choose an application from `apps/`
2. Edit its `config.yaml` to uncomment desired modules
3. Configure module-specific settings in `pipelines/`
4. Run with the CLI

For detailed setup instructions, see the documentation for each application.

## Quick Links

| Resource | URL |
|----------|-----|
| **Configuration Hub** | [doc.log10x.com/config](https://doc.log10x.com/config/) |
| **Applications** | [doc.log10x.com/apps](https://doc.log10x.com/apps/) |
| **Run Pipeline** | [doc.log10x.com/run](https://doc.log10x.com/run/) |
| **Compile Pipeline** | [doc.log10x.com/compile](https://doc.log10x.com/compile/) |
| **Architecture** | [doc.log10x.com/apps](https://doc.log10x.com/apps/) |
| **API Reference** | [doc.log10x.com/api](https://doc.log10x.com/api/) |

## License

This repository is licensed under the [MIT License](LICENSE).

### Fork-Friendly, License Required to Run

This repository is designed for you to fork and customize. You are free to:

- Fork this repository for your organization
- Modify configuration files for your specific deployment needs
- Contribute improvements back to the community

**However, running Log10x requires a commercial license.**

| What's Open Source | What Requires License |
|-------------------|----------------------|
| Configuration files in this repo | Log10x engine/runtime |
| Module definitions | Log10x apps (Reporter, Receiver, Retriever) |
| YAML/JSON schemas | Executing pipelines |

The configuration files in this repository are designed for use with the Log10x
engine. Think of this like Kubernetes manifests - the YAML is freely available,
but you need a cluster to run it.

**Get a Log10x License:**
- [Pricing](https://www.log10x.com/pricing?utm_source=github&utm_medium=readme&utm_campaign=config&utm_content=footer)
- [Documentation](https://doc.log10x.com)
- [Contact Sales](mailto:sales@log10x.com)
