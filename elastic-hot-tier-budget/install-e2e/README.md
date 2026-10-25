# Install proof: the hot-tier run from the tools alone

Does `log10x_setup_recurring hot_tier_gb` run against a cluster set up only by the frozen-tier recipe from `log10x_advise_retriever` and a Receiver installed only from `log10x_advise_install` with `log_destination: "elasticsearch"`, with no hand-set engine option and no hand-added ILM phase?

**Result: yes.** Four `tenx-recur` runs, all exit 0 at their reads: a dry run and an applied run with only kept lines on hot, then, once the applied limits sent lines to `tenx-tierdown`, a dry run and an applied run with documents in both aliases. Each run read the kept lines' hours on hot from the recipe's own policy: `A kept line stays on hot 168 hours (ILM policy tenx-keep (rollover max_age 1d + frozen min_age 6d))`.

log10x-mcp 1.30.90, engine image `ghcr.io/log-10x/edge-10x:1.1.150` (the values render `log10x/edge-10x:1.1.147@sha256:a043ccd828742c4eccee09abb654ce6a7357b6123f73300ed04f8605e874b8c4`; `launch.json` records both), Elasticsearch 9.5.5, one hot node and one warm and frozen node, 2026-10-25 23:46 to 23:53 UTC. No time scaling.

## What ran

`MCP=<log10x-mcp build> ./run.sh <step>`, in this order:

1. `render 0.002`: `render.mjs` calls the three tools' handlers from the build. `advise_retriever` with `destination: "elasticsearch"`: the frozen-tier block is `results/recipe.txt`, its six `PUT` requests with the comment lines dropped are `results/recipe-requests.json`. `advise_install` with app `receiver`, forwarder `fluentbit`, `log_destination: "elasticsearch"`, builtin licence, airgapped, metrics backend `elastic`: the plan is `results/install-plan.md`, the sidecar and the policy seed are `results/receiver.json`. `setup_recurring` with `hot_tier_gb: 0.002` on `github_actions`, every replay container in `nodes_by_container`: `results/policy.yaml` and `results/apply-instructions.md`. The size is 2 MB so that the run holds lines on the first pass.
2. `policy-init`: a local bare repo stands in for the policy repo: `policy.yaml` on `main`, the seed files from advise_install's ConfigMap (`caps.csv`, `actions.csv`, `totals.csv`, `regulator-unit: bytes`) under `log10x/policy/` on `log10x-policy`.
3. `up`: the two Elasticsearch nodes, then `setup-es.mjs`: the trial licence and a filesystem repository registered as `found-snapshots` (cluster preparation, so that the recipe applies as rendered), then the six requests, all 200; `tenx-tierdown-000001` on the warm node, `tenx-app-000001` on hot. Then Fluent Bit (`../rig/fluent-bit`, which sends `tier_down` lines to `tenx-tierdown` and the rest to `tenx-app`) and the Receiver from `results/compose.receiver.yaml`: the args exactly as the values render them, including `symbolMessageHashField tenx_hash` and `outputEncodeField fullText("tenx_hash","routeState","message_pattern","severity_level","utf8Size")`.
4. `feed start 8`: the OTel demo sample at 56 lines a second (`../rig/forward_send.py`, the first 12,000 rows of the replay source).
5. `tick --dry-run`, then `tick`: exit 0 both; the applied run committed the four files to `log10x-policy`.
6. `sync`: the committed `caps.csv`, `actions.csv` and `totals.csv` copied into the Receiver's policy mount, Receiver restarted.
7. About three minutes later, `tenx-app` held 7,440 documents and `tenx-tierdown` 2,340, every `tier_down` document with `utf8Size`. `tick --dry-run`, then `tick`: exit 0 both.
8. `feed stop`, `down`: every e100 container, volume and network removed.

Summary line of the last run (`results/ticks/20261025T235320Z/run.json`): `applied: Hot tier: 4 MB of 2 MB (0.002 GB set in the policy) on 1 hot node; at these limits it settles at about 4.6 GB within 168 hours, with 442 MB a day of counted lines moved to the frozen tier.` It settles above the size because the always-pass sample alone keeps about 592 MB a day, which the report states.

## Rig substitutions (no cluster)

The values read the policy files through the Kubernetes pull lane (`K8S_ENABLED`, `K8S_CONFIGMAP`, `K8S_NAMESPACE`); here `K8S_ENABLED=false` and the three lookup files are mounted at `/policy`. `CONFIG_GENERATION_FILE` is left out, since the seed has no `config-generation.csv`. `TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit`, because Fluent Bit is a separate container. The applied files reach the Receiver by `sync` and a restart, in place of the ConfigMap or git pull. No engine option was added or changed. `launch.json` lists each substitution.

## Not shown

Kept lines reaching frozen after 6 days; a tier_down mount; the GitHub Actions workflow or a Kubernetes CronJob; the git pull lane (`policy_git`); an Elastic Cloud deployment.
