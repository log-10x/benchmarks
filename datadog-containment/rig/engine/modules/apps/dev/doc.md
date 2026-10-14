---
icon: material/play-circle-outline
hidden: true
---

Run the dev app on your log files locally to preview how edge and cloud apps will process them. No API key needed for previewing savings on local logs.

## :material-clipboard-play-outline: Setup Guide

???+ tenx-bootstrap "Step 1: Install"

    - :simple-linux: [Single line script](https://doc.log10x.com/install/singleline/ "curl https://raw.githubusercontent.com/log-10x/pipeline-releases/main/install.sh | bash"){data-copy="curl https://raw.githubusercontent.com/log-10x/pipeline-releases/main/install.sh | bash"} | [DEB](https://doc.log10x.com/install/linux/#ubuntu-debian) | [RPM](https://doc.log10x.com/install/linux/#red-hat-centos-7)
    - :simple-macos: [Homebrew](https://doc.log10x.com/install/macos/ "brew install log-10x/tap/log10x"){data-copy="brew install log-10x/tap/log10x"}
    - :material-microsoft-windows: [PowerShell script](https://doc.log10x.com/install/win/)
    - :simple-docker: [Docker image](https://doc.log10x.com/install/docker/)

???+ tenx-config "Step 2: Set Environment Variables"

    Set these environment variables before running. See [path configuration](https://doc.log10x.com/install/paths/) for details.

    | Variable | Description |
    |----------|-------------|
    | `TENX_CONFIG` | Path to your [configuration directory](https://doc.log10x.com/install/paths/#config) |
    | `TENX_LICENSE_KEY` | Your Log10x license JWT ([licensing](https://doc.log10x.com/manage/license/)). Not needed for previewing savings on local logs. |

    ```bash
    export TENX_CONFIG=/path/to/your/config
    export TENX_LICENSE_KEY="$(cat license.jwt)"   # skip if just previewing local logs
    ```

    For production deployments, prefer mounting the license as a file and setting `TENX_LICENSE_FILE`, see [deployment](https://doc.log10x.com/engine/gitops/#best-practices).

???+ tenx-analyzerinputs "Step 3: Set Up Input Logs"

    The dev app reads the `.log` files in `$TENX_CONFIG/data/sample/input` and any file named with [inputFilePath](https://doc.log10x.com/run/input/file/#inputfilepath), and nothing else.

    === "Bundled Sample"

        Run on the 500-line OpenTelemetry k8s sample that ships with the configuration:

        ```bash
        tenx @apps/dev inputFilePath $TENX_CONFIG/data/sample/otel-sample.log
        ```

    === "Sample Otel Logs"

        Download [sample logs](https://log10x-public-assets.s3.amazonaws.com/samples/otel-k8s/medium/input/otel-sample.log) (20 MB OpenTelemetry k8s):

        ```bash
        mkdir -p $TENX_CONFIG/data/sample/input
        curl -o $TENX_CONFIG/data/sample/input/otel-sample.log \
          https://log10x-public-assets.s3.amazonaws.com/samples/otel-k8s/medium/input/otel-sample.log
        ```

    === "Your Own Logs"

        Copy your log files to the input directory:

        ```bash
        mkdir -p $TENX_CONFIG/data/sample/input
        cp /path/to/your/logs/* $TENX_CONFIG/data/sample/input/
        ```

??? tenx-symbols "Step 4: Symbol Paths (optional)"

    Symbol libraries tell the engine how to recognize log patterns from your frameworks and applications. A [default library](https://doc.log10x.com/compile/pull/#default-symbols) with 150+ frameworks is included. Set [symbolPaths](#symbols) to add your own.

??? tenx-initializers "Step 5: Enrichments (optional)"

    Enrichments add context (severity, HTTP codes) for richer aggregation reports.

    **To enable:**

    1. In the [app config](#mainConfig), uncomment the desired enrichment `include` entries
    2. In the [initializers](#initializers) section below, configure each enrichment's settings

???+ tenx-mainconfig "Step 6: Run"

    === ":material-laptop: Nix/Win/OSX"

        **Best for**: Quick local testing and development.

        The CLI automatically loads configuration from `$TENX_CONFIG`:

        ```bash
        tenx @apps/dev
        ```

    === ":material-docker: Docker (+ :material-laptop: local logs)"

        **Best for**: Isolated testing with no install.

        The image carries its own configuration. Mount the input and output folders only:

        ```bash
        mkdir -p $TENX_CONFIG/data/sample/output
        docker run --rm \
          -v $TENX_CONFIG/data/sample/input:/etc/tenx/config/data/sample/input \
          -v $TENX_CONFIG/data/sample/output:/etc/tenx/config/data/sample/output \
          -e TENX_LICENSE_KEY="$(cat license.jwt)" \
          log10x/pipeline-10x:1.1.81 \
          @apps/dev
        ```

        Skip `-e TENX_LICENSE_KEY` to run with the image's built-in limited license (fine for previewing savings on local logs).

    === ":material-docker: Docker (+ :material-github: GitOps config)"

        **Best for**: CI/CD pipelines with version-controlled configuration.

        Use the [@github](https://doc.log10x.com/config/github) macro to pull configuration from a repository:

        ```bash
        docker run --rm \
          -e TENX_LICENSE_KEY="$(cat license.jwt)" \
          log10x/pipeline-10x:1.1.81 \
          '@github={"token": "<gh-token>", "repo": "my-user/my-repo"}' \
          @apps/dev
        ```

        Skip `-e TENX_LICENSE_KEY` to run with the image's built-in limited license (fine for previewing savings on local logs).

???+ tenx-top10-events "Step 7: Analyze Output"

    The [File Output](#file) generates the following files in `$TENX_CONFIG/data/sample/output`:

    === ":material-chart-line: aggregated.csv"

        Statistical analysis of your log patterns: top event types by volume and bytes, error rates, and level distributions.

        See [analysis tables](https://doc.log10x.com/apps/dev/#preview-cost-savings) for sample output.

    === ":material-package-variant-closed: encoded.log"

        Your original events losslessly compact.

        See [reduction ratios](https://doc.log10x.com/apps/dev/#production-use) for sample output.

    === ":material-code-json: templates.json"

        Unique TenXTemplate patterns discovered in your logs, enabling lossless volume reduction.

        See [template analysis](https://doc.log10x.com/apps/dev/#production-use) for sample output.

    === ":material-restore: decoded.log"

        Perfect reconstruction of compact events, validating [lossless expanding](https://doc.log10x.com/run/transform/#expand).

        **To validate lossless encoding:**

        ```bash
        # Clear input and copy encoded output
        rm -f $TENX_CONFIG/data/sample/input/*.log
        cp $TENX_CONFIG/data/sample/output/encoded.log $TENX_CONFIG/data/sample/input/

        # Re-run to decode
        tenx @apps/dev

        # Compare with original, files match exactly
        diff $TENX_CONFIG/data/sample/output/decoded.log /path/to/original.log
        ```

??? tenx-delete "Step 8: Teardown"

    Nothing runs in the background, uninstall removes only what was installed.

    === ":simple-macos: Homebrew"

        ```bash
        brew uninstall log10x
        ```

    === ":simple-linux: Linux"

        ```bash
        sudo rm -rf /opt/tenx-edge /etc/tenx /etc/profile.d/tenx-edge.sh
        ```

        If installed via DEB: `sudo apt-get remove tenx-edge`
        If installed via RPM: `sudo yum remove tenx-edge`

    === ":material-microsoft-windows: Windows"

        Uninstall from **Settings > Apps > Installed apps**.

    === ":simple-docker: Docker"

        ```bash
        docker rmi log10x/pipeline-10x:1.1.81
        ```
