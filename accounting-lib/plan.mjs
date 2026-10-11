// Ask the released log10x MCP server for its plan on one capture, over MCP stdio, and keep
// what it wrote: the plan object, its notes and headline, and the caps file it rendered.
//
//   node plan.mjs <siem> <target_percent> <out.json> [key=value ...]
//
// Environment: CAPTURE, the capture file; SPAN, the time span the capture covers (the
// tool's `window` argument). The server runs from the node_modules next to this file, so
// the caller installs log10x-mcp there first and copies this file beside it.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const mcpVersion = require("log10x-mcp/package.json").version;
const [, , siem, target, out, ...rest] = process.argv;
if (!siem || !target || !out || !process.env.CAPTURE) {
  console.error("usage: CAPTURE=<file> SPAN=<window> node plan.mjs <siem> <target_percent> <out.json> [key=value ...]");
  process.exit(2);
}
const extra = Object.fromEntries(
  rest.map((kv) => {
    const [k, v] = kv.split("=");
    return [k, v === "true" ? true : v === "false" ? false : isNaN(+v) ? v : +v];
  }),
);
const transport = new StdioClientTransport({
  command: "node",
  args: [require.resolve("log10x-mcp/build/index.js")],
  env: { ...process.env },
  stderr: "pipe",
});
let stderr = "";
transport.stderr?.on("data", (d) => { stderr += d.toString(); });
const client = new Client({ name: "accounting-benchmark", version: "0" });
await client.connect(transport);

const args = {
  source: "file",
  path: process.env.CAPTURE,
  siem,
  window: process.env.SPAN || "10h",
  target_percent_reduction: +target,
  ...extra,
};
const t0 = Date.now();
const res = await client.callTool({ name: "log10x_poc_from_local", arguments: args }, undefined, { timeout: 3_600_000 });
const elapsed_ms = Date.now() - t0;
await client.close();

const text = res.content?.[0]?.text ?? "";
let envelope = null;
try { envelope = JSON.parse(text); } catch { envelope = null; }
if (res.isError || !envelope) {
  writeFileSync(out, JSON.stringify({ mcp_version: mcpVersion, args, error: text.slice(0, 4000), stderr: stderr.slice(-4000) }, null, 1));
  console.error("plan failed:", text.slice(0, 400));
  process.exit(1);
}
const data = envelope.data ?? {};
const capsPath = data.report_caps_path;
const tool_caps_csv = capsPath && existsSync(capsPath) ? readFileSync(capsPath, "utf8") : null;
const actionsPath = data.report_actions_path;
const tool_actions_csv = actionsPath && existsSync(actionsPath) ? readFileSync(actionsPath, "utf8") : null;
writeFileSync(out, JSON.stringify({
  mcp_version: mcpVersion,
  args,
  elapsed_ms,
  summary: envelope.summary ?? null,
  notes: data.notes ?? [],
  events_pulled: data.events_pulled,
  total_bytes: data.total_bytes,
  distinct_patterns: data.distinct_patterns,
  feasibility: data.feasibility ?? null,
  plan: data.plan ?? null,
  tool_caps_csv,
  tool_actions_csv,
  engine_policy: data.engine_policy ?? null,
  markdown: data.markdown ?? null,
}, null, 1));
console.log(`plan ${siem} ${target}%: ${data.events_pulled} events sampled, ${(data.plan?.planned ?? []).length} patterns planned, ${Math.round(elapsed_ms / 1000)} s`);
