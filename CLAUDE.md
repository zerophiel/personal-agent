# personal-agent

Owner-only personal finance bot on Hermes Agent v0.22.5, deployed from this repo to the VPS. State and decisions:
docs/PROGRESS.md; security rules: docs/SECURITY.md.

## private/: never read or list it

`~/personal-agent/private/` is the full plaintext copy of the VPS data and secrets, by the owner's decision of
2026-11-06 (docs/SECURITY.md). It is git-ignored and never leaves the laptop through this repo. The assistant, its
subagents and any other AI working in this folder never read, list, search or print anything under it, with any tool:
even its file names hold private details. It moves only through `make mirror` and `make restore`, whose output holds
counts and statuses only. `.claude/settings.json` denies Read and Edit there; Bash is covered by this rule alone.

## Working rules

The owner's standing rules. The security ones are in docs/SECURITY.md, section "What a session may see".

- Language: every line the owner sees is in Bahasa Indonesia, right after a context compaction too; the owner is "kamu".
  Code, configs, commits and docs are in English (docs/GMAIL_OAUTH.md is Indonesian). Bot SOULs and every message a bot
  sends the owner are in Indonesian.
- Authority: no deploy, no change on the VPS, no merge to `main` and no project decision without the owner's OK. An OK
  covers the step it was given for, not the next. The owner's own money choices stay the owner's. Work on a branch; no
  force-push.
- The repo is the recipe: no manual change on the VPS without the same change in the repo, since what only the VPS knows
  is lost at the next rebuild. `make capture` brings host config and versions back after one made there. Back up the
  ledger before any data change (docs/calibration.md).
- The copy: `make mirror` before a migration and after work worth keeping; the folder is only as fresh as its last run. A
  move follows docs/REBUILD.md.
- The address: the VPS address and login live only in `config/vps.env`. Read them from there, never type one from memory,
  never repeat the address in visible text, and use `make -s` for targets that would echo it.
- The bots: anything for the children is never proposed as a cut. Money is computed by deterministic code in integer
  Rupiah; living money is read from the ledger. No proactive messages to the owner: never start `pa-gmail-token`,
  `pa-ingest` or `pa-ingest-alert` by hand. At most one or two one-shot tests of a bot, never writing real data. The owner
  sends `/new` after a SOUL or tool change. The Gmail allowlist changes only with the owner. No Opus or Fable for a bot.

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
