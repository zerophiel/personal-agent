#!/usr/bin/env python3
"""Runtime map of the live bot. Runs the three read-only probes on the VPS over ssh, scrubs their output a second time
and renders docs/runtime/ (stable: README, host, containers, proxies, timers, hermes, hermes-defaults, vault-tools,
ledger-schema.sql, infra-files; snapshots: bot-activity, state). Run from the repo root:
  python3 ops/runtime-map/collect.py [--raw DIR]        (or: make runtime-map)
Nothing is written on the VPS. No secret, balance or message text reaches the docs: the probes export names, counts,
dates and masked templates only, and every string is scrubbed again here before it is rendered."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HOST = "ubuntu@43.157.242.194"
HERMES_SRC = os.path.expanduser("~/.graphify/repos/NousResearch/hermes-agent-v0.22.5")   # local engine copy (graph + grep)
PROBES = {
    "host": ("sudo python3 -", "probe_host.py"),
    "hermes": ("sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -", "probe_hermes.py"),
    "vault_tools": ("sudo docker exec -i personal-agent-vault-tools-1 python -", "probe_vault_tools.py"),
}
SKIP_DIRS = {".git", ".claude", "graphify-out", "__pycache__"}
RUNTIME_PREFIXES = ("compose/", "config/", "host/", "scripts/", "services/", "Makefile")
UNIT_DIRS = ("host/", "services/applier/systemd/")   # make deploy installs host/; the applier's install.sh its own
TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9_-]+|\bntn_[A-Za-z0-9]+|\bsecret_[A-Za-z0-9]{20,}"
                   r"|ya29\.[A-Za-z0-9_.-]+|\b1//[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{12,}|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}"
                   r"|-----BEGIN[^-]*-----")
OWNER = re.compile(r"(?i)\bdanuarta(?:\s+wiratama)?\b|\bwiratama\b")   # the owner's legal name (statement holder name)
MONEY = re.compile(r"(?i:rp)\.?\s*\d(?:[\d.,]*\d)?(?:\s*(?i:jt|juta|rb|ribu|k)\b)?|\b\d{1,3}(?:\.\d{3})+\b(?!\.\d)")
DIGEST = re.compile(r"(?=[0-9a-f]*[a-f])(?:[0-9a-f]{40}|[0-9a-f]{64})")   # a whole sha1/sha256 value (file hashes for drift)
PURPOSE = {   # /opt/data inside the vault container (HERMES_HOME)
    "config.yaml": "our Hermes profile; read-only bind mount of services/hermes/vault/config.yaml",
    "SOUL.md": "the bot's persona and rules; read-only bind mount of services/hermes/vault/SOUL.md",
    "plugins": "Hermes plugins; cardguard is a read-only bind mount of services/hermes/vault/plugins/cardguard",
    ".env": "Hermes's own env file in HERMES_HOME (never opened by the collector)",
    "auth.json": "Hermes credential store / pool (never opened by the collector); the pool is empty, the API key comes from env",
    "state.db": "sessions, messages, model usage, delivery obligations, routing, admissions, system prompts (SQLite WAL)",
    "sessions": "sessions.json: gateway session key -> session, token and cost counters",
    "logs": "agent.log (INFO+), gateway.log, errors.log (WARNING+), boot/exit/shutdown diagnostics, update receipts",
    "cache": "MCP schema cache, tool discovery cache, uploads (images, documents: counted, never read), spillover",
    "skills": "bundled Hermes skills (the skills toolset is disabled in config.yaml: instructions live in SOUL.md)",
    "pending": "approval queue: skills proposed by the bot wait here (skills.write_approval: true)",
    "cron": "Hermes cron store (cronjob toolset disabled; no jobs); host timers do the scheduling",
    "ttl": "cardguard TTL file: /rincian messages to delete after expiry",
    "backups": "Hermes's own config backups (config.yaml.good.*)",
    "gateway_state.json": "gateway platforms (telegram, api_server) and listener state",
    "gateway": "restart_loop.json: boot history used by the restart-loop guard",
    "gateways": "per-profile gateway pointer (default/current)",
    "state": "gateway.lifecycle.json",
    "runtime": "active_sessions.json",
    "spawn-ledger.json": "processes the gateway spawned",
    "installs": "install bootstrap metadata",
    "channel_directory.json": "chats the gateway knows (counts only)",
    ".skills_prompt_snapshot.json": "cached skills index for the system prompt",
    "kanban.db": "kanban store (toolset disabled)",
    "projects.db": "projects store",
    "response_store.db": "api_server /v1/responses history",
    "runs_idempotency.db": "api_server run idempotency keys",
}
LOG_NOTES = [   # what a frequent log line means, checked against the engine source (HERMES_SRC)
    ("credential pool: no available entries", "agent/credential_pool.py:2123",
     "INFO, throttled. The pool in auth.json is empty; the Anthropic key is read from the environment. Benign."),
    ("Re-anchored stale current_turn_user_idx", "agent/turn_iteration_prep.py:251",
     "A mid-turn compaction rebuilt the messages; Hermes re-anchors the turn so tool output is not lost. Counts mid-turn compactions."),
    ("Could not persist destructive_slash_confirm=false", "gateway/run_busy.py:1562",
     "The owner picked 'always' on a /new confirm before approvals.destructive_slash_confirm: false was set; config.yaml is read-only."),
    ("Failed to save config: Read-only file system", "cli.py:789",
     "A setting change tried to write config.yaml, which is mounted read-only by design (agents cannot change their own config)."),
    ("config migration skipped: This config predates version 12", "hermes_cli/config_migrations.py:25",
     "Our config has no _config_version; below-floor configs are left untouched and defaults are deep-merged at read time. Benign "
     "for a read-only config (a version marker would make Hermes try to persist migrations)."),
    ("router: catalog fetch failed / Model catalog", "plugins/model-providers/router/__init__.py:207",
     "Model catalog refresh goes to hosts squid does not allow. Harmless: the model id is pinned in config.yaml."),
]
PROXY_NOTES = [   # checked against the squid access log
    ("hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com",
     "Hermes model-catalog and provider refreshes (see hermes.md log notes). Harmless: the model is pinned in config.yaml."),
    ("dns.google, cloudflare-dns.com", "DNS-over-HTTPS fallbacks of the HTTP clients; name resolution uses Docker DNS instead."),
    ("169.254.169.254", "AWS IMDSv2 credential probes (/latest/api/token, iam/security-credentials), all on 2026-10-27 11:04-11:12 "
     "during the first Hermes setup, none since: an AWS credential chain looking for instance credentials. Blocked; there are none."),
]
CONFIG_READERS = {   # our keys outside DEFAULT_CONFIG -> the engine code that reads them (checked by hand in HERMES_SRC)
    "agent.reasoning_effort": "gateway/run_config_loaders.py:151 (_load_reasoning_config: a per-model override wins, else this key)",
    "model.default": "hermes_cli/runtime_provider.py:260 (DEFAULT_CONFIG has model: \"\" at hermes_cli/config_defaults.py:34)",
    "model.provider": "hermes_cli/runtime_provider.py:359",
    "gateway.platforms.telegram.extra.disable_link_previews": "plugins/platforms/telegram/adapter.py:603",
    "unauthorized_dm_behavior": "gateway/config.py:645 (default \"pair\": a stranger gets a pairing code), gateway/authz_mixin.py:716",
    "plugins.enabled": "hermes_cli/plugins.py:1455",
    "mcp_servers.*.url": "tools/mcp_tool_transport.py:118",
    "mcp_servers.*.headers": "tools/mcp_tool_transport.py:118",
    "mcp_servers.*.connect_timeout": "tools/mcp_tool_transport.py:424",
    "mcp_servers.*.timeout": "tools/mcp_tool_common.py:48",
    "mcp_servers.*.tools.resources": "tools/mcp_tool_registration.py:191",
    "mcp_servers.*.tools.prompts": "tools/mcp_tool_registration.py:191",
}
LISTENERS = {   # localhost listeners inside the vault container
    8642: "api_server platform (OpenAI-compatible, gateway/platforms/api_server.py): reachable only inside the container",
    "ephemeral": "gateway runtime/dashboard API: start_gateway_api(host=127.0.0.1, port=0) at boot (gateway/run_runtime.py:499, "
                 "gateway/run_api.py:137); a new port on every boot",
}
ENGINE_NOTES = [   # engine behaviours that matter to the owner, verified in HERMES_SRC; changing them is a human config edit
    ("Messages sent while the bot restarts are dropped",
     "platforms.telegram.extra.drop_pending_on_cold_boot (default true): on a cold boot the Telegram adapter discards the updates "
     "queued while it was offline (plugins/platforms/telegram/adapter.py:3099-3111; log line 'Cold boot: dropping Telegram updates'). "
     "A message the owner sends during a deploy restart is lost and has to be sent again; false in config.yaml would replay them."),
    ("Strangers are ignored", "unauthorized_dm_behavior: ignore. The engine default (pair) answers an unknown user with a pairing code."),
    ("Background skill/memory review is idle",
     "auxiliary.background_review.enabled defaults to true, but a review only fires when the skill_manage tool is loaded or memory "
     "review is on (agent/turn_finalizer.py:764-790). The skills toolset and memory are off, so it last ran on 2026-10-28 (the two "
     "pending skill proposals; about USD 0.40)."),
    ("Curator", "curator.enabled defaults to true: weekly upkeep of agent-created skills only (there are none); consolidate is false, "
     "so no LLM call."),
    ("Context compression", "compression.threshold_tokens 100000 since 2026-10-30 18:21 (was 60000: three compactions in six minutes "
     "lost the owner's answers). A preflight-compression log line older than the gateway restart shows the old threshold."),
    ("Telegram command menu", "The engine puts at most 60 commands in the Telegram menu and hides the rest (typing them still works)."),
    ("Engine tools besides MCP", "Only clarify and vision_analyze are loaded next to the 56 vault_tools tools (latest tool-schema "
     "snapshot). tool_call, tool_search, tool_describe, terminal, session_search, skill_view and unprefixed MCP names in old "
     "sessions date from 27-28 Oct, before the toolsets were locked down."),
]


# ------------------------------------------------------------------------------------------------------------- scrub
def mixed(word):
    return any(c.isdigit() for c in word) and any(c.isupper() for c in word) and any(c.islower() for c in word)


def scrub(s):
    if DIGEST.fullmatch(s):   # a hash is compared, not shown: masking its digit runs made a quarter of all hashes "differ"
        return s
    s = TOKEN.sub("[token]", s)
    s = re.sub(r"[A-Za-z0-9_\-]{20,}", lambda m: "[blob]" if mixed(m.group()) else m.group(), s)
    s = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b", "[email]", s)   # not user@<ip>: the ssh target stays readable
    s = OWNER.sub("[owner]", s)
    s = re.sub(r"\b\d{3,4}(?:[ -]\d{3,4}){2,}\b", "[nomor]", s)
    return re.sub(r"\d{9,}", "[angka]", s)


def amounts(s):
    """Example amounts in tool descriptions and other prose: masked like the probes' free text."""
    return MONEY.sub(lambda m: "Rp [n]" if m.group()[:2].lower() == "rp" else "[n]", str(s))


def deep_scrub(obj):
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, list):
        return [deep_scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {scrub(str(k)): deep_scrub(v) for k, v in obj.items()}
    return obj


# ------------------------------------------------------------------------------------------------------------- helpers
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def local_tree():
    out = {}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), ROOT)
            if f == ".git" or (rel.startswith("secrets/") and ".dec" in f):
                continue
            out[rel] = sha(os.path.join(root, f))
    return out


def cell(v, width=None):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        v = ", ".join(str(x) for x in v)
    elif isinstance(v, dict):
        v = ", ".join(f"{k}: {x}" for k, x in v.items())
    s = str(v).replace("|", "\\|").replace("\n", " ").strip()
    return s if width is None or len(s) <= width else s[:width - 1] + "…"


def table(headers, rows, width=None):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(cell(x, width) for x in r) + " |" for r in rows]
    return "\n".join(lines) if rows else "_(none)_"


def fence(text, lang=""):
    return f"```{lang}\n{text.rstrip()}\n```"


def header(title, what, data):
    return (f"# {title}\n\n{what}\n\nGenerated by `ops/runtime-map/collect.py` from the live VPS on {data['collected_at']} "
            f"(regenerate: `make runtime-map`). Sanitized: no secrets, balances or message text (see README.md).\n")


def write(out, name, text):
    with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
        fh.write(scrub(text).rstrip() + "\n")


def reader_for(key):
    if key in CONFIG_READERS:
        return CONFIG_READERS[key]
    parts = key.split(".")
    if parts[0] == "mcp_servers" and len(parts) > 2:
        for n in range(len(parts), 2, -1):
            if f"mcp_servers.*.{'.'.join(parts[2:n])}" in CONFIG_READERS:
                return CONFIG_READERS[f"mcp_servers.*.{'.'.join(parts[2:n])}"]
    return None


def engine_refs(keys):
    """Where the engine reads a config key DEFAULT_CONFIG does not list: the verified CONFIG_READERS entry, else the best
    source lines naming the quoted leaf (a .get("leaf") or ["leaf"] first, in files that also name the section)."""
    out = {k: reader_for(k) for k in keys}
    todo = [k for k in keys if not out[k]]
    if not os.path.isdir(HERMES_SRC) or not todo:
        return out
    hits = {k: [] for k in todo}
    for root, dirs, files in os.walk(HERMES_SRC):
        dirs[:] = [d for d in dirs if d not in ("graphify-out", "tests", "__pycache__")]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for k in todo:
                parts = k.split(".")
                leaf = re.escape(parts[-1])
                if not re.search(rf"['\"]{leaf}['\"]", text):
                    continue
                in_section = len(parts) > 1 and parts[0] in text
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(rf"['\"]{leaf}['\"]", line):
                        score = 2 * bool(re.search(rf"get\(\s*['\"]{leaf}['\"]|\[\s*['\"]{leaf}['\"]\s*\]", line)) + in_section
                        hits[k].append((-score, f"{os.path.relpath(p, HERMES_SRC)}:{i}"))
    for k, v in hits.items():
        out[k] = (", ".join(x for _, x in sorted(v)[:3]) + " (automatic search: confirm by hand)") if v else "NOT FOUND in the engine"
    return out


def listener_note(r):
    if r["ip"] == "127.0.0.11":
        return "Docker embedded DNS"
    if r["port"] in LISTENERS:
        return LISTENERS[r["port"]]
    return LISTENERS["ephemeral"] if r["ip"].startswith("127.") and r["proto"] == "tcp" else ""


# ------------------------------------------------------------------------------------------------------------- renderers
def render_readme(h, he, vt, drift):
    return f"""# Runtime map of the live bot

What runs on the VPS, as it really is, so a change starts from facts instead of a fresh scan. Generated by
`ops/runtime-map/collect.py` on {h['collected_at']}; regenerate with `make runtime-map` after every deploy or when
the bot behaves unexpectedly. Then refresh the project graph (`make graph`, and `/graphify --update` in Claude Code for docs).

## Files

| file | what | changes |
|---|---|---|
| [host.md](host.md) | VPS: OS, ports, firewall, SSH, cron, /opt layout, secret names, images | rarely |
| [containers.md](containers.md) | every container: image, user, command, env names, mounts, networks, limits, hardening | on deploy |
| [proxies.md](proxies.md) | squid egress zones: allowed domains, config drift | on deploy |
| [timers.md](timers.md) | systemd pa-* units: schedule, command, hardening, drift | on deploy |
| [hermes.md](hermes.md) | Hermes engine: build, processes, listeners, platforms, config overrides vs defaults, /opt/data, plugins, skills, MCP tools, state.db schema, logs | on deploy / upgrade |
| [hermes-defaults.md](hermes-defaults.md) | every DEFAULT_CONFIG key of the engine with its default and doc comment, plus OPTIONAL_ENV_VARS | on Hermes upgrade |
| [vault-tools.md](vault-tools.md) | vault-tools container, ledger tables, columns, row counts, entity catalog (no money), thresholds keys | on deploy |
| [ledger-schema.sql](ledger-schema.sql) | the live ledger DDL from sqlite_master (schema v{vt['ledger'].get('user_version')}) | on migration |
| [infra-files.md](infra-files.md) | Makefile, Dockerfiles, squid confs, systemd units, stack.env, .gitignore verbatim (they have no graphify parser) | on edit |
| [bot-activity.md](bot-activity.md) | snapshot: sessions, messages, tool calls, tool errors, tokens and cost, log templates, restarts | daily |
| [state.md](state.md) | snapshot: ledger coverage, /usulan, plans, backups, timer results, deploy drift, proxy traffic | daily |

## Graphs

- Project graph: `graphify-out/graph.json` (repo code AST + docs including this folder). Start with
  `graphify-out/GRAPH_REPORT.md`, then `graphify query "<question>"`, `graphify path "A" "B"`, `graphify explain "X"`.
- Hermes engine graph (local only, too big for git): `{HERMES_SRC.replace(os.path.expanduser('~'), '~')}/graphify-out/graph.json`
  from the engine files copied out of the vault container (bundled CPython/node/chromium removed). Query with
  `graphify query "<question>" --graph <that path>`; read code in the same copy.

## Sanitization rules (enforced by the probes and again by collect.py)

- Never opened: Hermes `.env`, `auth.json`, `/opt/personal-agent-secrets/*`, `/run/secrets/*`, restic.env, pdf_passwords,
  uploaded images and documents. Secrets appear by name and file mode only.
- Container env: names only, values only for proxy/TZ/path keys. Command and healthcheck strings are scrubbed;
  `docker compose config` is never printed (it interpolates secrets).
- state.db: counts, tool names, token usage and timestamps only. Message content is read inside the container for a
  yes/no ("looks like an error") and never exported. Log lines become templates: cut at `msg=`/`text=`, `user=` masked,
  quoted strings, hex and digits masked.
- Ledger: no balance, limit, outstanding, amount, target or last4 column; thresholds by key only; free text (/usulan,
  subscription names) has amounts masked (`Rp <n>`, grouped thousands, runs of 4+ digits; card last-4 in aliases stays).
- Uploaded and ingested files: counted and classified by source, bank and document kind; their names (which carry the
  owner's name and account fragments) are never exported.
- Every string: tokens, emails, grouped numbers and digit runs of 9+ masked; file names have digit runs of 5+ masked.

## Deploy drift at collection time

{drift}
"""


def render_host(h):
    o, u, s = h["os"], h["usage"], h["security"]
    out = [header("Host (VPS)", "The Tencent Cloud VPS that runs the stack (`ubuntu@43.157.242.194`).", h)]
    out.append("## Machine\n\n" + table(["item", "value"], [
        ("OS", o["pretty"]), ("kernel", o["kernel"]), ("CPUs", o["cpus"]), ("memory (MB)", o["mem_total_mb"]),
        ("timezone", o["timezone"]), ("docker", o["docker"]), ("compose", o["compose"]),
        ("root disk", f"{u['disk_root_gb']} GB, {u['disk_root_used_pct']}% used"), ("memory available (MB)", u["mem_available_mb"]),
        ("uptime (days)", u["uptime_days"])]))
    out.append("## Docker disk use\n\n" + table(["type count size reclaimable"], [(x,) for x in u["docker_df"]]))
    out.append("## Listening sockets\n\nPublic exposure is decided here and by the firewall: containers publish no ports.\n\n"
               + table(["proto", "local", "process"], [(r["proto"], r["local"], r["process"]) for r in h["listening"]]))
    out.append("## Firewall\n\n" + fence("\n".join(s["ufw"]) or "(ufw output empty)") +
               f"\n\niptables -S rules: {s['nft_or_iptables_rules']}; fail2ban: {s['fail2ban']}; "
               f"docker daemon.json: {'present' if s['docker_daemon_json'] else 'absent'}")
    if s["docker_daemon_json"]:
        out.append(fence(s["docker_daemon_json"], "json"))
    out.append("## SSH\n\n" + table(["sshd -T key", "value"], sorted(s["sshd"].items())) +
               "\n\nauthorized_keys entries: " + cell(s["ssh_authorized_keys"]))
    out.append("## Unattended upgrades\n\n" + table(["key", "value"], sorted(s["auto_upgrades"].items())))
    out.append("## Cron (outside systemd)\n\nRoot crontab (Tencent Cloud agents, not ours):\n\n" + fence("\n".join(s["root_crontab"]) or "(empty)")
               + "\n\n/etc/cron.d: " + cell(s["cron_d"]) + ". The stack's own schedules are systemd timers (timers.md).")
    out.append("## /opt/personal-agent-data\n\nPersistent state, root-owned. Backed up by restic (pa-backup).\n\n" + table(
        ["entry", "type", "mode", "owner", "bytes"], [(r["name"], r["type"], r["mode"], r["owner"], r["bytes"]) for r in h["opt"]["data"]]))
    out.append(f"## /opt/personal-agent-secrets (mode {h['opt']['secrets_dir_mode']})\n\nNames and modes only; mounted into containers "
               "as compose secrets (/run/secrets/<name>).\n\n" + table(["secret", "mode", "owner"],
                                                                         [(r["name"], r["mode"], r["owner"]) for r in h["opt"]["secrets"]]))
    out.append("## Docker images\n\n" + table(["repository", "tag", "id", "created", "size"],
                                              [(r["repo"], r["tag"], r["id"], r["created"], r["size"]) for r in h["images"]]))
    return "\n\n".join(out)


def render_containers(h):
    out = [header("Containers", "Every container of the compose project `personal-agent` (compose/docker-compose.yml).", h)]
    rows = [(c["name"], c["service"], c["user"], c["restart"], c["read_only"], c["memory_mb"], c["cpus"], cell(c["networks"]),
             c["state"]["status"], c["state"]["health"]) for c in h["containers"]]
    out.append("## Summary\n\n" + table(["container", "service", "user", "restart", "read-only", "mem MB", "cpus", "networks", "status",
                                         "health"], rows))
    for c in h["containers"]:
        part = [f"## {c['name']}", table(["item", "value"], [
            ("image", c["image"]), ("image id", c["image_id"]), ("user", c["user"]), ("workdir", c["workdir"]),
            ("entrypoint", c["entrypoint"]), ("command", c["cmd"]), ("healthcheck", c["healthcheck"]),
            ("cap_drop", c["cap_drop"]), ("cap_add", c["cap_add"]), ("security_opt", c["security_opt"]),
            ("privileged", c["privileged"]), ("read-only rootfs", c["read_only"]), ("tmpfs", c["tmpfs"]),
            ("pids limit", c["pids_limit"]), ("memory MB / cpus", f"{c['memory_mb']} / {c['cpus']}"), ("log", c["log"]),
            ("published ports", c["ports"]), ("network mode", c["network_mode"]), ("networks", c["networks"]),
            ("env names", c["env_names"]), ("env values (safe keys)", c["env_safe"])])]
        part.append(table(["mount type", "source", "destination", "rw"],
                          [(m["type"], m["source"], m["dest"], m["rw"]) for m in c["mounts"]]))
        out.append("\n\n".join(part))
    out.append("## Networks\n\n`internal: true` networks have no route out; only the squid containers also join `egress`.\n\n" + table(
        ["network", "driver", "internal", "containers"], [(n["name"], n["driver"], n["internal"], cell(n["containers"])) for n in h["networks"]]))
    out.append("## Volumes\n\nAnonymous volumes come from image VOLUME lines; named ones from compose. Never deleted automatically.\n\n"
               + table(["volume", "anonymous", "used by", "labels"], [(v["name"], v["anonymous"], cell(v["used_by"]), cell(v["labels"]))
                                                                     for v in h["volumes"]]))
    return "\n\n".join(out)


def render_proxies(h, local):
    out = [header("Egress proxies (squid)", "Each zone's containers reach the internet only through their squid; the allowlist is "
                  "`acl ... dstdomain` in config/squid/<zone>.conf.", h)]
    out.append("## Notes on denied traffic\n\n" + table(["denied", "what it is"], PROXY_NOTES))
    for svc, z in sorted(h["squid"].items()):
        repo = f"config/squid/{svc.split('-', 1)[1]}.conf"
        same = local.get(repo) == z["conf_sha256"]
        out.append(f"## {svc}\n\nConfig vs repo `{repo}`: {'identical' if same else 'DIFFERENT (deploy drift)'}\n\n"
                   + table(["allowed domain"], [(d,) for d in z["allow_domains"]]) + "\n\n" + fence("\n".join(z["directives"]), "squid"))
    return "\n\n".join(out)


def render_timers(h, local):
    out = [header("Host timers and services (systemd)", "Units `pa-*` in /etc/systemd/system, installed from host/ by "
                  "scripts/install-timers.sh, and the applier's from services/applier/systemd/ by its install.sh. They "
                  "run the scheduled jobs; no LLM is involved in any of them.", h)]
    rows = []
    for u in h["units"]:
        k = dict((a, b) for a, b in u["keys"])
        sched = ", ".join(b for a, b in u["keys"] if a in ("OnCalendar", "OnUnitActiveSec", "OnBootSec", "PathChanged", "PathModified"))
        src = next((d + u["name"] for d in UNIT_DIRS if d + u["name"] in local), None)
        rows.append((u["name"], k.get("Description"), sched, k.get("ExecStart"),
                     "not in repo" if src is None else "same" if local[src] == u["sha256"] else "DIFFERENT"))
    out.append(table(["unit", "description", "schedule / trigger", "runs", "vs repo"], rows))
    for u in h["units"]:
        out.append(f"## {u['name']}\n\n" + table(["key", "value"], u["keys"]))
    return "\n\n".join(out)


def render_hermes(h, he, local):
    e, cfg, lay = he["engine"], he["config"], he["layout"]
    vault = next((c for c in h["containers"] if c["service"] == "vault"), {})
    out = [header("Hermes (vault bot engine)", "Hermes Agent in container personal-agent-vault-1: the Telegram bot "
                  "@danoevault_agent. Its code is the engine graph (README.md); this file is how it is configured and what it holds.", he)]
    stamp = "; ".join(f"{k}={v}" for k, v in sorted(e.get("stamp", {}).items()))
    out.append("## Engine\n\n" + table(["item", "value"], [
        ("image", vault.get("image")), ("release date", e.get("release_date")), ("install stamp", stamp or "(none)"),
        ("python", f"{e.get('python')} ({e.get('executable')})"), ("command", vault.get("cmd")),
        ("HERMES_HOME and env", e.get("env_safe")), ("bundled plugins", e.get("bundled_plugins")),
        ("platform adapters", e.get("platform_plugins"))]))
    out.append("Environment variable names in the container (values never read): " + cell(e.get("env_names")))
    sk = he["sockets"]
    out.append("## Processes and listeners\n\ns6-svscan (pid 1) supervises the dashboard, main-hermes and gateway services; the "
               "gateway is the Telegram bot. A 127.x address is reachable only from inside this container.\n\n" +
               table(["pid", "uid", "RSS MB", "command"], [(p["pid"], p["uid"], p["rss_mb"], p["cmd"]) for p in sk["processes"]]) + "\n\n" +
               table(["proto", "address", "port", "pid", "what"], [(r["proto"], r["ip"], r["port"], r["pid"], listener_note(r))
                                                                   for r in sk["listen"]]))
    out.append("## Engine behaviours that matter\n\nChecked in the engine source; changing any of them is a config.yaml edit by a human.\n\n"
               + table(["behaviour", "detail"], ENGINE_NOTES))
    gw = he["gateway"]
    out.append("## Gateway platforms\n\n" + "\n\n".join(f"**{p}**\n\n" + table(["field", "value"], sorted(v.items()))
                                                        for p, v in sorted(gw["platforms"].items())) +
               "\n\nGateway state: " + cell(gw["state"]) + f"\n\nRestart-loop guard: {gw['restart_loop']['boots']} boots recorded. "
               f"Active sessions: {gw['active_sessions']}. Spawn ledger entries: {gw['spawn_ledger']}. Session keys: "
               + cell(gw["sessions_json"]["keys"]))
    unknown = [o["key"] for o in cfg["overrides"] if not o["known"]]
    refs = engine_refs(unknown)
    rows = [(o["key"], o["ours"], o["default"] if o["default"] is not None else "(not in DEFAULT_CONFIG)",
             f"L{o['line']}" if o["line"] else "", ("" if o["known"] else f"read by {refs.get(o['key'])}.")
             + (" " if o["doc"] else "") + cell(o["doc"], 220)) for o in cfg["overrides"]]
    out.append("## Config: our overrides\n\n`/opt/data/config.yaml` (sha256 "
               f"{cfg['config_sha256'][:12]}, repo {'identical' if local.get('services/hermes/vault/config.yaml') == cfg['config_sha256'] else 'DIFFERENT'})"
               f" against DEFAULT_CONFIG in `{cfg['defaults_source'].replace('/opt/hermes/', '')}` (line numbers below). "
               "Everything not listed runs on the default (hermes-defaults.md). A key outside DEFAULT_CONFIG is checked "
               f"against the engine source. Config version: ours {cfg['config_version_ours']}, engine default {cfg['config_version_default']}.\n\n"
               + table(["key", "ours", "default", "src", "notes"], rows))
    out.append("## Config sections\n\n" + table(["section", "line", "keys", "we set"],
                                                 [(s["section"], s["line"], s["keys"], cell(s["ours"])) for s in cfg["sections"]]))
    out.append("SOUL.md sha256 " + str(cfg["soul_sha256"])[:12] + (", identical to the repo." if local.get("services/hermes/vault/SOUL.md") ==
                                                                   cfg["soul_sha256"] else ", DIFFERENT from the repo."))
    rows = []
    for r in lay["entries"]:
        rows.append((r["name"], r["type"], r["mode"], r["owner"], r.get("bytes"), r.get("files", ""), cell(r.get("children", ""), 160),
                     PURPOSE.get(r["name"], "")))
    out.append("## /opt/data (HERMES_HOME)\n\nMounts: " + cell(lay["mounts"]) + "\n\n" +
               table(["entry", "type", "mode", "owner", "bytes", "files", "contents", "purpose"], rows))
    out.append("## JSON state files (keys only)\n\n" + table(["file", "bytes", "updated", "shape"],
                                                              [(k, v["bytes"], v["mtime"], cell(json.dumps(v["shape"]), 300))
                                                               for k, v in sorted(he["json_shapes"].items())]))
    x = he["extensions"]
    out.append("## Plugins\n\n" + "\n\n".join(f"**{p['name']}**: files {cell(p['files'])}; manifest {cell(p.get('manifest'))}"
                                               for p in x["plugins"]))
    out.append("## Skills\n\nThe `skills` toolset is disabled (config.yaml): the model cannot load these. Bundled categories:\n\n"
               + table(["category", "skills"], [(k, cell(v, 400)) for k, v in sorted(x["skills"].items())]) +
               "\n\nPending approvals (skills the bot proposed; nothing runs until a human approves):\n\n" +
               table(["file", "subsystem", "action", "created", "summary", "operations"],
                     [(p["file"], p["subsystem"], p["action"], p["created"], p["summary"], cell(p["operations"])) for p in x["pending"]]))
    out.append("## Cron, TTL, config backups, uploads\n\n" + table(["item", "value"], [
        ("cron", cell(json.dumps(x["cron"]), 400)), ("ttl", cell(x["ttl"])),
        ("config backups", cell([f"{b['file']} ({b['mtime']})" for b in x["backups"]])),
        ("update receipts", cell([f"{r['file']}: {r['fields']}" for r in x["receipts"]], 600))] +
        [(f"uploads {k}", f"{v['files']} files, {v['bytes']} bytes, newest {v['newest']}; kinds: {cell(v.get('kinds'))}")
         for k, v in sorted(x.get("uploads", {}).items())]))
    rows = []
    for sname, s in sorted(he["mcp"]["servers"].items()):
        for t in s["tools"]:
            rows.append((t["name"], cell(t["params"]), amounts(t["desc"])))
        out.append(f"## MCP server `{sname}`\n\n{len(s['tools'])} tools in the schema cache (fingerprint {s['fingerprint']}); "
                   f"utility tools: {cell(s['utility_tools'])}. The model sees them as `mcp__{sname}__<name>`; `?` marks an optional "
                   "parameter.\n\n" + table(["tool", "parameters", "description (first line)"], rows))
        rows = []
    out.append(render_dbs(he["databases"]))
    lg = he["logs"]
    out.append("## Log files\n\n" + table(["file", "bytes", "lines", "first", "last", "levels", "distinct templates"],
                                          [(k, v.get("bytes"), v.get("lines"), v.get("first"), v.get("last"), cell(v.get("levels")),
                                            v.get("distinct_templates")) for k, v in sorted(lg.items())]) +
               "\n\nLoggers by volume (agent.log):\n\n" + table(["level logger", "lines"], (lg.get("logs/agent.log") or {}).get("loggers", [])))
    out.append("## What frequent log lines mean\n\n" + table(["line", "engine source", "meaning"], LOG_NOTES))
    return "\n\n".join(out)


def render_dbs(dbs):
    out = ["## Databases in /opt/data"]
    for rel, prof in sorted(dbs.items()):
        if not prof or "<error>" in prof:
            out.append(f"### {rel}\n\n{prof}")
            continue
        m = prof["meta"]
        rows = []
        for t, info in sorted(prof["tables"].items()):
            notes = []
            if info.get("span"):
                notes.append(f"{info['span'][0]} {info['span'][1]}..{info['span'][2]}")
            if info.get("categories"):
                notes.append("; ".join(f"{c}: {cell(v)}" for c, v in info["categories"].items()))
            if info.get("keys"):
                notes.append("keys: " + ", ".join(f"{k} ({n})" for k, n in info["keys"]))
            rows.append((t, "virtual" if info.get("virtual") else info["type"], info["rows"], cell([c for c, _ in info["cols"]], 900),
                         cell(notes, 500)))
        out.append(f"### {rel}\n\nuser_version {m['user_version']}, journal {m['journal_mode']}, {m['bytes']} bytes "
                   f"(+{m['wal_bytes']} WAL). Indexes: {cell(prof['indexes'], 600)}\n\n" + table(["table", "type", "rows", "columns", "profile"], rows))
    return "\n\n".join(out)


def render_defaults(he):
    cfg = he["config"]
    out = [header("Hermes DEFAULT_CONFIG", "Every key of the engine's DEFAULT_CONFIG with its default and the doc comment above it "
                  f"(`{cfg['defaults_source'].replace('/opt/hermes/', '')}`). Keys we override are in hermes.md. Kept out of the graph "
                  "(.graphifyignore): grep it.", he)]
    by = {}
    for r in cfg["defaults"]:
        by.setdefault(r["key"].split(".")[0], []).append(r)
    for sec, rows in by.items():
        out.append(f"## {sec}\n\n" + table(["key", "default", "line", "doc"], [(r["key"], r["default"], r["line"], cell(r["doc"], 300))
                                                                             for r in rows]))
    out.append("## OPTIONAL_ENV_VARS\n\n" + table(["name", "category", "secret", "description"],
                                                   [(r["name"], r["category"], r["secret"], r["desc"]) for r in cfg["optional_env"]]))
    return "\n\n".join(out)


def render_vault_tools(h, vt):
    c = next((x for x in h["containers"] if x["service"] == "vault-tools"), {})
    lg = vt["ledger"]
    out = [header("vault-tools (MCP server and ledger)", "Container personal-agent-vault-tools-1 runs services/vault-tools: the MCP "
                  "server Hermes calls (http://vault-tools:8000/mcp) and the SQLite ledger /data/ledger.db. All money is computed "
                  "here in integer Rupiah; the LLM only calls tools.", vt)]
    out.append("## Runtime\n\n" + table(["item", "value"], [
        ("python", vt["python"]), ("uid", vt["user"]), ("cwd", vt["cwd"]), ("image", c.get("image")), ("command", c.get("cmd")),
        ("healthcheck", c.get("healthcheck")), ("env names", vt["env_names"]), ("env (safe keys)", vt["env_safe"]),
        ("secrets (/run/secrets)", [f"{s['name']} {s['mode']}" for s in vt["secrets"]]), ("packages", vt["packages"])]))
    sk = vt["sockets"]
    what = {8000: "MCP server (streamable HTTP /mcp, bearer token): no published port, reachable on net-vault only",
            "127.0.0.11": "Docker embedded DNS"}
    out.append("## Processes and listeners\n\n" + table(["pid", "uid", "RSS MB", "command"],
                                                       [(p["pid"], p["uid"], p["rss_mb"], p["cmd"]) for p in sk["processes"]]) + "\n\n"
               + table(["proto", "address", "port", "pid", "what"], [(r["proto"], r["ip"], r["port"], r["pid"],
                                                                      what.get(r["ip"]) or what.get(r["port"], "")) for r in sk["listen"]]))
    out.append("## /data\n\n" + table(["entry", "type", "mode", "bytes", "updated"],
                                      [(r["name"], r["type"], r["mode"], r["bytes"], r["mtime"]) for r in vt["data"]]))
    out.append("## /ingest (read-only; filled by ingest-gmail and pa-uploads)\n\nFile kinds are derived from the names (source, "
               "bank, document kind); the names themselves carry the owner's name and are never exported.\n\n" + table(
        ["dir", "files", "bytes", "extensions", "file kinds", "oldest", "newest"],
        [(r["dir"], r["files"], r["bytes"], cell(r["exts"]), cell(r.get("kinds"), 500), r["oldest"], r["newest"]) for r in vt["ingest"]]))
    out.append(f"## Ledger\n\nschema user_version {lg['user_version']}, journal {lg['journal_mode']}, {lg['bytes']} bytes (+{lg['wal_bytes']} WAL). "
               "DDL: ledger-schema.sql. Code: services/vault-tools/vault_tools/ledger.py (DDL + _migrate).\n\n" +
               table(["table", "rows", "columns", "foreign keys"], [(t, lg["rows"][t], cell(cols, 700), cell(lg["foreign_keys"].get(t)))
                                                                    for t, cols in sorted(lg["columns"].items())]))
    parts = ["## Entity catalog (no money columns)"]
    for t, rows in lg["catalog"].items():
        if rows:
            keys = list(rows[0].keys())
            parts.append(f"### {t} ({len(rows)})\n\n" + table(keys, [[r[k] for k in keys] for r in rows]))
        else:
            parts.append(f"### {t}\n\n_(empty)_")
    out.append("\n\n".join(parts))
    out.append("## Thresholds (keys only; values live in the ledger, read them with ringkasan_data)\n\n" + cell(lg["thresholds"]))
    out.append("## Category rules and owner keywords (counts per category; the patterns stay in the ledger)\n\n" +
               table(["category", "rules", "keywords"], [(k, lg["category_rules"].get(k, 0), lg["category_keywords"].get(k, 0))
                                                         for k in sorted(set(lg["category_rules"]) | set(lg["category_keywords"]))]))
    out.append("## Public holidays data (cuti bersama)\n\n" + table(["file", "entries per key"], [(k, cell(v)) for k, v in vt["cuti"].items()]))
    return "\n\n".join(out)


def render_activity(he):
    a = he["activity"]
    out = [header("Bot activity snapshot", "What the vault bot did, from state.db and its logs. Counts only. Changes daily.", he)]
    out.append("## Totals\n\n" + table(["item", "value"], [
        ("sessions by source", a.get("sources")), ("messages by role", a.get("roles")), ("session end reasons", a.get("end_reasons")),
        ("session models", a.get("models")), ("compression columns in sessions", a.get("compression_columns")),
        ("system prompts and tool-schema snapshots", a.get("system_prompts")), ("delivery obligations", a.get("deliveries"))]))
    keys = sorted({k for v in a["sessions_by_day"].values() for k in v})
    out.append("## Sessions per WIB day and source\n\n`children` = sessions with a parent (a compaction or /new continues the chat).\n\n"
               + table(["day source"] + keys, [[d] + [round(v.get(k, 0), 4) for k in keys] for d, v in a["sessions_by_day"].items()]))
    keys = sorted({k for v in a["messages_by_day"].values() for k in v})
    out.append("## Messages per WIB day\n\n" + table(["day"] + keys, [[d] + [v.get(k, 0) for k in keys] for d, v in a["messages_by_day"].items()]))
    keys = sorted({k for v in a["usage_by_day"].values() for k in v})
    out.append("## Model usage per day, model and task\n\n`list_cost_usd` = tokens at the rates in ops/calibration/bot_usage.py "
               "(Sonnet, 5-minute cache); Hermes reports cost_status unknown for this model.\n\n" +
               table(["day model task"] + keys, [[d] + [round(v.get(k, 0), 4) for k in keys] for d, v in a["usage_by_day"].items()]))
    keys = sorted({k for v in a["usage_by_month"].values() for k in v})
    out.append("## Model usage per month (vault cap USD 45)\n\n" + table(["month model"] + keys, [[d] + [round(v.get(k, 0), 4) for k in keys]
                                                                                             for d, v in a["usage_by_month"].items()]))
    tg, flags = dict(a["tool_calls_telegram"]), a.get("tool_result_flags") or {}
    out.append("## Tool calls\n\nResult flags are computed inside the container over each tool result; no result text is exported. "
               "`error field`: the result JSON has an \"error\" key. `refusal words`: the text says gagal, ditolak, tidak bisa or tidak "
               "ditemukan (usually a tool refusing bad input, not a crash). `unknown tool`: the engine said the tool does not exist.\n\n"
               + table(["tool", "calls (all)", "calls (telegram)", "results", "error field", "refusal words", "unknown tool"], [
                   (t, n, tg.get(t, 0), flags.get(t, {}).get("results", ""), flags.get(t, {}).get("error_field", ""),
                    flags.get(t, {}).get("refusal_words", ""), flags.get(t, {}).get("unknown_tool", "")) for t, n in a["tool_calls"]]))
    out.append("## Engine (non-MCP) tool calls per day and source\n\n" + table(["tool", "calls by day and source"], [
        (t, cell(v)) for t, v in sorted((a.get("engine_tool_calls") or {}).items())]))
    facts = [(f, k, v) for f, lv in sorted(he["logs"].items()) for k, v in sorted((lv.get("facts") or {}).items())]
    out.append("## Engine facts from the logs (latest line of each)\n\nCompare the time with the last gateway start in hermes.md: "
               "an older line describes the previous configuration.\n\n" + table(["log", "fact", "latest line"], facts))
    for f, v in sorted(he["logs"].items()):
        if not v.get("templates"):
            continue
        ev = v.get("events") or {}
        out.append(f"## {f}\n\n{v.get('lines')} lines {v.get('first')}..{v.get('last')}, levels {cell(v.get('levels'))}.\n\n"
                   + (table(["event"] + sorted({d for x in ev.values() for d in x if d}),
                            [[k] + [x.get(d, "") for d in sorted({d for y in ev.values() for d in y if d})] for k, x in sorted(ev.items())])
                      + "\n\n" if ev else "") + table(["template", "count"], v["templates"]))
    gw = he["gateway"]["restart_loop"]
    out.append("## Restart history (gateway restart_loop.json, last boots)\n\n" + table(["boot"], [(b,) for b in gw["last_boots"]]))
    return "\n\n".join(out)


def render_state(h, he, vt, drift_md, local):
    lg = vt["ledger"]
    cov = lg["coverage"]
    out = [header("State snapshot", "Volatile facts: what the ledger covers, open /usulan, plans, backups, timer results, deploy drift "
                  "and proxy traffic. Counts and dates only. Changes daily.", vt)]
    out.append("## Ledger rows\n\n" + table(["table", "rows"], sorted(lg["rows"].items())))
    out.append("## Card statements per card\n\n" + table(["card", "statements", "first", "last", "last due", "reconciled", "paid marked",
                                                         "lines ok"], [(r["card"], r["n"], r["first"], r["last"], r["last_due"], r["reconciled"],
                                                                        r["paid_marked"], r["lines_ok"]) for r in cov["statements"]]) +
               "\n\nlines_status: " + cell(cov["statement_lines_status"]))
    months = sorted({m for v in cov["transactions_by_source_month"].values() for m in v})
    out.append("## Transactions per source and month\n\n" + table(["source"] + months, [[s] + [v.get(m, "") for m in months]
                                                                                       for s, v in sorted(cov["transactions_by_source_month"].items())])
               + f"\n\nSpan {cell(cov['transactions_span'])}. By owner: {cell(cov['transactions_by_owner'])}. Flags: {cell(cov['transactions_flags'])}."
               f"\n\nCategories: {cell(cov['transactions_categories'])}")
    out.append("## Bank mutation files per account\n\n" + table(["account", "files", "first", "last", "reconciled"],
                                                                [(r["account"], r["n"], r["first"], r["last"], r["reconciled"]) for r in cov["mutation_files"]]))
    cyc = sorted({c for v in cov["card_lines"].values() for c in v})
    out.append("## Card statement lines per card and cycle\n\n" + table(["card"] + cyc, [[k] + [v.get(c, "") for c in cyc]
                                                                                    for k, v in sorted(cov["card_lines"].items(), key=lambda kv: str(kv[0]))])
               + f"\n\nKinds: {cell(cov['card_line_kinds'])}. Instalments per card: {cell(cov['card_installments'])}; "
               f"scanned statements: {cov['card_installment_scans']}.")
    out.append("## Payments, reports, progress\n\n" + table(["item", "value"], [
        ("card payments", cell(cov["card_payments"])), ("debt payments", cell(cov["debt_payments"])),
        ("balance reports", cell(cov["balance_reports"])), ("fund reports", cell(cov["fund_reports"])),
        ("plan progress per payday", cell(cov["plan_progress"])), ("plans", cell(cov["plans"])),
        ("net snapshots", cell(cov["net_snapshots"])), ("subscriptions by status", cell(cov["subscriptions_by_status"])),
        ("processed Gmail messages", cell(cov["processed_messages"])), ("skipped files by reason", cell(cov["skipped_files"])),
        ("doc files", cell(cov["doc_files"])), ("ingest checks", cov["ingest_checks"])]))
    out.append("## change_log (rows changed by hand)\n\n" + table(["table", "action", "rows", "last"],
                                                                  [(r["tbl"], r["action"], r["n"], r["last"]) for r in cov["change_log"]]))
    out.append("## /usulan (feature_requests; amounts masked)\n\n" + table(["id", "created", "status", "title", "resolution"],
                                                                           [(u["id"], u["created"], u["status"], u["title"], u["resolution"])
                                                                            for u in lg["usulan"]]))
    baks = [r for r in vt["data"] if ".bak" in r["name"]]
    out.append(f"## Ledger backups in /data ({len(baks)})\n\nMade before each deploy that touches data (RUNBOOK). Restic keeps the "
               "off-container copies.\n\n" + table(["file", "bytes", "made"], [(r["name"], r["bytes"], r["mtime"]) for r in baks]))
    rows = []
    for u in h["units"]:
        s = u["state"]
        rows.append((u["name"], s.get("ActiveState"), s.get("SubState"), s.get("Result"), s.get("ExecMainStatus"),
                     s.get("LastTriggerUSec") or s.get("ExecMainExitTimestamp"), s.get("NextElapseUSecRealtime"), u["journal_last"]))
    out.append("## Timer and job results\n\n" + table(["unit", "active", "sub", "result", "exit", "last run", "next", "last journal line"], rows))
    for u in h["units"]:
        if u["journal_7d"]:
            out.append(f"### {u['name']} journal, 7 days (templates)\n\n" + table(["template", "count"], u["journal_7d"]))
    out.append("## Containers now\n\n" + table(["container", "status", "health", "started", "restarts", "OOM", "exit"],
                                               [(c["name"], c["state"]["status"], c["state"]["health"], c["state"]["started_at"],
                                                 c["state"]["restart_count"], c["state"]["oom_killed"], c["state"]["exit_code"]) for c in h["containers"]]))
    for svc, v in sorted(h["docker_logs"].items()):
        out.append(f"### {svc} container log, 7 days ({v['lines_7d']} lines, templates)\n\n" + table(["template", "count"], v["templates"]))
    for svc, z in sorted(h["squid"].items()):
        out.append(f"## Proxy traffic: {svc} (log {z['log_first']}..{z['log_last']}; tmpfs, resets on restart)\n\n" +
                   table(["allowed host", "requests"], z["allowed"]) + "\n\n" + table(["denied host", "requests"], z["denied"]) +
                   ("\n\nBy client container:\n\n" + table(["container verdict host", "requests"], z["by_client"]) if z.get("by_client") else ""))
    out.append("## Deploy drift\n\n" + drift_md)
    return "\n\n".join(out)


def render_infra():
    files = ["Makefile", ".gitignore", "config/stack.env"] + sorted(
        os.path.join(d, f) for d in ("config/squid", "host") for f in os.listdir(os.path.join(ROOT, d))) + sorted(
        f"services/{s}/Dockerfile" for s in os.listdir(os.path.join(ROOT, "services")) if os.path.exists(os.path.join(ROOT, "services", s, "Dockerfile")))
    out = ["# Infrastructure files\n\nThe repo files graphify has no parser for (Makefile, Dockerfiles, squid, systemd, env), copied verbatim "
           "so they are part of the project graph. Generated by `ops/runtime-map/collect.py`; the files themselves are the source of truth.\n"]
    for rel in files:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        desc = next((ln.split("=", 1)[1] for ln in text.splitlines() if ln.startswith("Description=")), "")
        lang = "makefile" if rel == "Makefile" else "dockerfile" if rel.endswith("Dockerfile") else "ini" if rel.startswith("host/") else ""
        out.append(f"## {rel}\n\n{desc}\n\n" + fence(text, lang))
    return "\n\n".join(out)


def render_drift(h, he, local):
    vps = h["deployed_tree"]
    same = [p for p in local if vps.get(p) == local[p]]
    diff = sorted(p for p in local if p in vps and vps[p] != local[p])
    only_repo = sorted(p for p in local if p not in vps)
    only_vps = sorted(p for p in vps if p not in local)
    run = lambda ps: [p for p in ps if p.startswith(RUNTIME_PREFIXES)]  # noqa: E731
    lines = [f"Compared {len(local)} repo files with {len(vps)} files in /opt/personal-agent: {len(same)} identical.",
             f"- runtime files that differ: {cell(run(diff)) or 'none'}",
             f"- runtime files not deployed yet: {cell(run(only_repo)) or 'none'}",
             f"- runtime files only on the VPS: {cell(run(only_vps)) or 'none'}",
             f"- docs/ops/tests not deployed or different (harmless): {len(set(diff + only_repo) - set(run(diff + only_repo)))}"]
    return "\n".join(lines)


def run_probe(host, name):
    cmd, script = PROBES[name]
    with open(os.path.join(HERE, script), "rb") as fh:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", host, cmd], stdin=fh, capture_output=True, timeout=900)
    if p.returncode != 0:
        sys.exit(f"probe {name} failed ({p.returncode}): {scrub(p.stderr.decode(errors='replace'))[-800:]}")
    return deep_scrub(json.loads(p.stdout))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "runtime"))
    ap.add_argument("--raw", help="also save the scrubbed probe JSON here (outside the repo)")
    ap.add_argument("--from-raw", help="render from JSON saved by --raw instead of probing")
    args = ap.parse_args()
    if args.from_raw:
        data = {n: json.load(open(os.path.join(args.from_raw, f"{n}.json"))) for n in PROBES}
    else:
        data = {n: run_probe(args.host, n) for n in PROBES}
    if args.raw:
        os.makedirs(args.raw, exist_ok=True)
        for n, d in data.items():
            json.dump(d, open(os.path.join(args.raw, f"{n}.json"), "w"), indent=1, sort_keys=True)
    h, he, vt = data["host"], data["hermes"], data["vault_tools"]
    h.setdefault("collected_at", h.get("usage", {}).get("collected_at"))
    for n, d in data.items():
        errs = [k for k, v in d.items() if isinstance(v, dict) and "<error>" in v]
        if errs:
            print(f"warning: probe {n} sections failed: {errs}", file=sys.stderr)
    local = local_tree()
    drift = render_drift(h, he, local)
    os.makedirs(args.out, exist_ok=True)
    docs = {
        "README.md": render_readme(h, he, vt, drift), "host.md": render_host(h), "containers.md": render_containers(h),
        "proxies.md": render_proxies(h, local), "timers.md": render_timers(h, local), "hermes.md": render_hermes(h, he, local),
        "hermes-defaults.md": render_defaults(he), "vault-tools.md": render_vault_tools(h, vt), "bot-activity.md": render_activity(he),
        "state.md": render_state(h, he, vt, drift, local), "infra-files.md": render_infra(),
    }
    for name, text in docs.items():
        write(args.out, name, text)
    sql = (f"-- Live ledger schema (sqlite_master of /data/ledger.db), user_version {vt['ledger']['user_version']}, collected "
           f"{vt['collected_at']} by ops/runtime-map/collect.py.\n-- Source of truth for changes: services/vault-tools/vault_tools/ledger.py "
           "(DDL + _migrate). Money columns are INTEGER Rupiah.\n\n" + ";\n\n".join(vt["ledger"]["ddl"]) + ";\n")
    write(args.out, "ledger-schema.sql", sql)
    print(f"wrote {len(docs) + 1} files to {os.path.relpath(args.out, ROOT)}")


if __name__ == "__main__":
    main()
