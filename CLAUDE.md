# personal-agent

Owner-only personal finance bot on Hermes Agent v0.22.5, deployed from this repo to the VPS. State and decisions:
docs/PROGRESS.md; security rules: docs/SECURITY.md.

## Project map: read it before doing anything

The owner's standing rule (2026-10-31): every task starts from the map, not from a fresh scan.

- Repo graph, code and docs including the live-bot snapshot: `graphify query "<question>"`, `graphify explain
  "<concept>"`, `graphify path "<A>" "<B>"` on graphify-out/graph.json; overview in graphify-out/GRAPH_REPORT.md.
- Live bot on the VPS (Hermes config vs defaults, SOUL and plugin, MCP tools, cron, state.db, logs, ledger schema,
  containers, proxies, timers, backups, drift): docs/runtime/README.md. It is a snapshot: run `make runtime-map`
  (read-only probes, scrubbed) before relying on live state, then review the diff before committing it.
- Hermes engine source, local only:
  `graphify query "<question>" --graph ~/.graphify/repos/NousResearch/hermes-agent-v0.22.5/graphify-out/graph.json`.
- Keep it current: after code edits `make graph` (AST only, free); after doc edits `/graphify . --update`; after a
  deploy `make runtime-map`, then `/graphify . --update`.
- Enforced by hooks: ops/graphify/graph_first.py adds the map and what changed since the build to every request, and
  `GRAPHIFY_HOOK_STRICT=1` (.claude/settings.json) makes graphify's read guard deny the first raw Read of an indexed
  file in a session until a query has run in the last 30 minutes.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
