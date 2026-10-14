<!--
  This file is the workspace runbook for the log10x repositories: production
  protection, the console deploy procedures, version bumping, docgen, and the
  Terraform template escaping rules.

  It is in version control as of 2026-09-07, and the reason is SOC 2 deficiency
  D-94. Until then it existed only as an untracked file in one person's
  workspace: no history, no review before a change took effect, and no way to
  establish what it said on any past date.

  That was not theoretical. Deficiency D-43 records what it drifted into: a
  documented staging deploy step that wrote a config.js pointing at the
  PRODUCTION Auth0 tenant and the PRODUCTION API, and prose asserting staging
  shared both. The deployed staging config does neither. Following the
  procedure as written would have collapsed the environment separation that
  actually exists, and nothing in the change process could have caught it
  because the file was outside change control entirely.

  Change it through a pull request. A runbook that directs a production deploy
  should be read once by someone before it takes effect.
-->

# Claude Code Rules for Log10x

## CRITICAL: READER FIRST trigger

When the user sends a message containing the exact phrase `READER FIRST` (uppercase), in that response you are **forbidden from**:
- Writing code edits, mockups, drafted copy, or any proposed text
- Calling Edit, Write, NotebookEdit, or any drafting tool
- Apologizing for prior failures or relitigating them (waste of tokens)

You **MUST** produce exactly two labeled blocks and stop:

```
Reader: [who is reading, what they know, what they don't know, where they are in the funnel]
Job of this beat: [what the reader needs in the first N seconds, before any mechanism appears]
```

Then wait for the user's confirmation or correction of those two lines before any draft.

**If you slip and produce a draft in the same response as `READER FIRST`:** the user will reply with `READER FIRST` again with no other text. You must back up to the protocol immediately — do not complete the slipped draft, do not argue.

**Why this exists:** to counter recency-bias and racing-to-please. The user has observed Claude pattern-matching to the latest input and rushing to draft instead of constructing a stable reader-model first. The trigger forces a structural pause. It is not optional advice — it is a hard rule.

The trigger is per-turn (you re-arm by re-invoking). It does not persist as a "mode" across subsequent turns automatically. If the user wants you in thinking mode for an extended pass, they re-invoke periodically.

## CRITICAL: Production Protection

**NEVER deploy to production unless the user message contains the exact phrase:**

```
DEPLOY TO PROD
```

(in uppercase)

### Production Resources - DO NOT TOUCH without explicit approval:
- S3 bucket: `log10x-console` (production)
- CloudFront: `E1ZA6ENI06V2YF` (console.log10x.com)
- Domain: `console.log10x.com`
- API: `prometheus.log10x.com`
- Auth0: `auth.log10x.com`

### Staging Resources - Safe to deploy:
- S3 bucket: `log10x-console-staging`
- CloudFront: `E1GJUPY3N18OAP` (console-staging.log10x.com)
- Domain: `console-staging.log10x.com`
- API: `api-staging.log10x.com`, gateway `prometheus-staging.log10x.com`
- Auth0: `auth-staging.log10x.com` (separate tenant `dev-hfiebyt6tcp8cfkx`)

**Staging and production are separate end to end, at the identity layer.**
An earlier version of this file claimed one Auth0 tenant and one API served
both. That was wrong. Verified 2026-09-07 by reading the deployed `config.js`
in each bucket: staging carries `auth-staging.log10x.com`,
`api-staging.log10x.com` and a Stripe **test** key; production carries
`auth.log10x.com`, `api.log10x.com` and a Stripe **live** key. The backend
repo's own `CLAUDE.md` has said this correctly all along.

## Grafana: REMOVED from the product (2026-09-03)

The hosted-Grafana surface is gone. `ui/src/lib/grafana.js` no longer exists,
nothing in the console links to Grafana, and the dashboards, the
`terraform/grafana` module and `deploy-grafana.yml` have been deleted from this
repo. If you are reading a note that calls the SAML flow mission critical, it
predates this and is wrong.

**Do NOT restore or "fix" any of it.** The dashboards were named for a product
taxonomy that no longer ships (`edge_reporter`, `edge_reducer`, `edge_optimizer`,
`cloud_reporter`, `cloud_streamer`).

**Still live, do not confuse with the above:**

- **Amazon Managed Prometheus**, workspaces `ws-5e1f18a6…` (prod) and
  `ws-7780a46a…` (staging). This is the metrics backend: engines write through
  the gateway, the console reads through `/api/v1/query`. Keep.
- **Two AWS Managed Grafana workspaces** (`g-e683d93d26` prod,
  `g-3fb6644a79` stage) are still ACTIVE at **$18/month combined**, kept
  deliberately for internal visibility only. Nothing in the product points at
  them. Delete them when that visibility is replaced.
- `analyzer_vendor` and `analyzer_cost` in user metadata are read by the
  deployed prometheus-proxy. They are not dead profile fields.

## Widget Build

The console components are also packaged as a standalone widget for the comsite (marketing site).

```bash
cd backend/terraform/console/ui && npm run build:widget
cp dist-widget/log10x-widget.js /Users/talweiss/eclipse-workspace/l1x-co/config/comsite/log10x/js/log10x-widget.js
```

Output goes to `dist-widget/log10x-widget.js`, then must be copied to `config/comsite/log10x/js/` for the local dev server (localhost:9001) to pick it up.

## Deployment Commands

The console is a Vite-built React app. Source is in `backend/terraform/console/ui/src/`.
Build output goes to `ui/dist/`. Runtime config is injected via a separate `config.js` file in S3 (not baked into the build).

### Deploy to Staging (DEFAULT - always deploy here first):
```bash
# 1. Build
cd backend/terraform/console/ui && npm run build

# 2. Sync built assets to S3 (preserve config.js, analytics.js, and status/)
aws s3 sync dist/ s3://log10x-console-staging/ --delete --exclude "config.js" --exclude "analytics.js" --exclude "status/*" --exclude "cache/*" --exclude "demo-metrics-replay/*"

# 3. Do NOT write config.js by hand. Terraform owns it in both buckets
#    ("Runtime configuration injected by Terraform ... the only Terraform-
#    templated asset"). The --exclude above is what keeps it intact. To change
#    it, change the tfvars and apply; a hand-uploaded file puts S3 out of sync
#    with state and the next apply reverts it. The step that used to sit here
#    pasted PROD Auth0 and a PROD API host over the staging config, which would
#    have collapsed the separation between the two environments.

# 4. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E1GJUPY3N18OAP --paths '/*'
```

### Deploy to Production (ONLY when user says "DEPLOY TO PROD"):
```bash
# 1. Build (if not already built)
cd backend/terraform/console/ui && npm run build

# 2. Sync built assets — KEEP existing config.js, analytics.js, and status/
#    status/heartbeat.json is the Upptime health check endpoint — DO NOT DELETE
aws s3 sync dist/ s3://log10x-console/ --delete --exclude "config.js" --exclude "analytics.js" --exclude "status/*" --exclude "cache/*" --exclude "demo-metrics-replay/*"

# 3. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E1ZA6ENI06V2YF --paths '/*'
```

**IMPORTANT: Production config.js is managed separately.** Do NOT upload a new config.js during quick deploys — the existing one in S3 has prod-specific values (Stripe live keys, prod Grafana client ID). Only update it via Terraform or manually with extreme care.

**IMPORTANT: `demo-metrics-replay/snapshot.json.gz`** is a 1MB demo fixture that lives ONLY in S3. It is not in the repo and `npm run build` does not produce it, so a sync with `--delete` and no exclude removes it and breaks the console demo. The bucket has versioning enabled, so recovery is `aws s3api delete-object --bucket log10x-console --key demo-metrics-replay/snapshot.json.gz --version-id <delete-marker-id>`.

**IMPORTANT: `status/heartbeat.json`** is an Upptime E2E health check file. The `--exclude "status/*"` flag prevents `--delete` from removing it. If accidentally deleted, restore with: `echo '{"status": "healthy"}' | aws s3 cp - s3://log10x-console/status/heartbeat.json --content-type "application/json"`

## Version Bumping

**ALWAYS bump the version number when deploying console changes.**

The version is in `backend/terraform/console/ui/src/config.js`:
```javascript
export const APP_VERSION = 'v2026.03.15.5';
```

**Version format:** `vYYYY.MM.DD.N` where N is the deployment number for that day (starts at 1).

Example: `v2026.02.01.1` → first deployment on Feb 1, 2026

## Stack Pages: DEAD — do not regenerate

**The per-vendor stack pages (splunk.html, datadog.html, dynatrace.html, …) no longer exist.** They were deleted from the live site and replaced with redirects to the homepage with the stack selector preset.

- They are **not** in the deployed tree (`log-10x/dotcom`, `origin/main` — check with `git ls-tree`).
- CloudFront redirects every vendor slug to `/?siem=<key>` via `STACK_REDIRECTS` in `dotcom/terraform/functions/url-rewrite.js.tftpl` (the function's own comment: *"Direct hit on a deleted vendor page"*).

**Do NOT** edit, regenerate, or "fix" these files. Stale copies still sit in `config/comsite/log10x/` (`stack.html`, `vendors.json`, `generate-stack-pages.py`, and the 15 generated HTML files) — that tree is **legacy/local and is not deployed**. Editing it changes nothing users see. If a vendor needs a landing surface, it is a homepage selector state (`/?siem=<key>`), not a page.

**Still live:** `config/comsite/PRICING.md` remains the source of truth for all $/GB vendor pricing figures used elsewhere (console, docs, comparison pages).

## Project Structure

- `config/` - Configuration files, documentation (mksite)
- `backend/terraform/console/ui/` - Console frontend (Vite + React JSX)
- `backend/terraform/console/ui/src/components/` - React components (App.jsx, Dashboard.jsx, GettingStarted.jsx, etc.)
- `backend/terraform/console/ui/src/lib/` - Shared utils (grafana.js, format.js, colors.js)
- `backend/terraform/console/ui/src/config.js` - Runtime config + version
- `backend/terraform/console/files/index.html.tpl` - Legacy Terraform template (still used by `terraform apply`)
- `backend/grafana/dashboards/` - Grafana dashboard JSON files
- `backend/lambdas/` - Lambda functions (Java)

## Documentation: Docgen for Module Pages

Module `doc.md` files under `config/modules/` are **source files** that docgen processes into `config/mksite/docs/` pages. Do NOT edit the generated `index.md` — changes will be overwritten.

**Source → Generated mapping:**

- `config/modules/apps/doc.md` → `config/mksite/docs/apps/index.md`
- `config/modules/apps/cloud/doc.md` → `config/mksite/docs/apps/cloud/index.md`
- `config/modules/apps/edge/doc.md` → `config/mksite/docs/apps/edge/index.md`
- Pattern: `config/modules/<path>/doc.md` → `config/mksite/docs/<path>/index.md`

**Individual per-app pages** (e.g., `config/mksite/docs/apps/edge/reporter/index.md`) are **NOT** auto-generated — those `index.md` files are the source of truth and can be edited directly.

**Asset references** in `doc.md` use relative paths that resolve in the generated output location. Assets live in `config/mksite/docs/assets/`.

**Screenshots + CTA buttons** belong on **individual per-app pages** (the `index.md` files), NOT on category-level `doc.md` files (e.g., `apps/edge/doc.md`, `apps/cloud/doc.md`). The only exception is the top-level `apps/doc.md` which has a hero screenshot.

**CTA buttons** in `doc.md` should NOT include `target="_blank"` — docgen adds it automatically.

## Terraform Template Escaping

**Only applies to `index.html.tpl`** (used by `terraform apply`, NOT by the Vite build).
The JSX source files in `ui/src/` use normal JavaScript — no escaping needed.

When editing `index.html.tpl`, JavaScript template literals with `${...}` must be escaped as `$${...}` for Terraform's templatefile() function.
