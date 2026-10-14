## 1️⃣0️⃣❎ Compact receiver module

Per-pattern compaction decision via a declarative cap-file. Decides whether each event is emitted via encode() (compact templateHash+vars form, volume reduction where the destination supports it) or as fullText. GitOps-controlled, the MCP writes per-pattern entries via PR, engine hot-reloads the cap-file without restart.

To learn more see the compact receiver [module documentation](https://doc.log10x.com/run/receive/compact "Per-pattern compaction decision via a declarative cap-file. Decides whether each event is emitted via encode() (compact templateHash+vars form, volume reduction where the destination supports it) or as fullText. GitOps-controlled, the MCP writes per-pattern entries via PR, engine hot-reloads the cap-file without restart.").

