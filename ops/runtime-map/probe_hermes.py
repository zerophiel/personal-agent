"""Hermes side of the runtime map: engine build, effective config against DEFAULT_CONFIG, the /opt/data layout, plugins,
skills, pending approvals, cron, gateway platforms and listeners, MCP tools, state.db schema and activity, log templates.
Runs inside the vault container with the engine's own interpreter (collect.py pipes it):
  ssh ubuntu@<vps> 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -' < ops/runtime-map/probe_hermes.py
Read-only: databases are opened with mode=ro. Never opens .env, auth.json or uploaded files. Message text never leaves the
container: only counts, tool names, token usage and timestamps do, and log lines are reduced to masked templates."""
import ast
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
import time
import types
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

D = "/opt/data"
H = "/opt/hermes"
WIB = timezone(timedelta(hours=7))
NEVER_OPEN = {".env", "auth.json"}                                       # listed by name, size and mode only
BYTES_ONLY = ("cache/images", "cache/documents", "cache/spillover")     # uploads: counted, never read
SOUL_MARK = "Kamu adalah"                                                # fallback; the first line of SOUL.md is used when readable
TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9_-]+|\bntn_[A-Za-z0-9]+|\bsecret_[A-Za-z0-9]{20,}"
                   r"|ya29\.[A-Za-z0-9_.-]+|\b1//[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{12,}|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}"
                   r"|-----BEGIN[^-]*-----")
WORD = re.compile(r"[A-Za-z0-9_\-]{20,}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
GROUPED = re.compile(r"\b\d{3,4}(?:[ -]\d{3,4}){2,}\b")
AMOUNT = re.compile(r"(?i:rp)\.?\s*\d(?:[\d.,]*\d)?(?:\s*(?i:jt|juta|rb|ribu|k)\b)?|\d{1,3}(?:[.,]\d{3})+|\d{4,}")
BANKS = ("bca", "mandiri", "jago", "jenius", "cimb", "dbs", "hsbc", "mega", "bni", "bri", "permata", "ocbc", "uob", "citi",
         "maybank", "danamon", "panin", "btn", "sinarmas", "shopee", "spaylater", "mtf")
DOC_KINDS = (("e-statement", r"e-?statement"), ("monthly-statement", r"monthly.?statement"), ("mutasi", r"mutasi"),
             ("tagihan", r"tagihan|billing"), ("rekening-koran", r"rekening.?koran"))
MONTHS = r"(?<![a-z])(?:jan|feb|mar|apr|mei|may|jun|jul|agu|aug|sep|okt|oct|nov|des|dec)"
STAMP = re.compile(r"^\[?(\d{4}-\d{2}-\d{2})[ T](\d{2}):\d{2}:\d{2}[,.]?\d*\]?\s*(?:[+-]\d{2}:?\d{2}|Z)?\s*")
TEXT_KEY = re.compile(r"\b(?:msg|text|content|caption|query|prompt|title|summary|reply|response|preview|body|note)=", re.I)
CATEGORICAL = {"state", "status", "kind", "type", "source", "platform", "role", "decision", "reason", "end_reason", "task",
               "model", "action", "outcome", "provider", "billing_provider", "cost_status", "admission", "verdict", "result",
               "tool_name", "subsystem", "phase", "channel", "chat_type", "mode", "api_mode"}
TEXTY = re.compile(r"content|text|message|summary|prompt|title|body|payload|json|args|arguments|reasoning|name$|error|preview|"
                   r"query|caption|note|detail|key$|_id$|^id$|user|chat|token(?!s)|secret|hash|path|url", re.I)
EVENTS = {   # per WIB day: what the bot did (counts only)
    "inbound_message": r"inbound message",
    "compression": r"(?i)compress",
    "sigterm": r"SIGTERM",
    "unclean_previous_life": r"exited UNCLEANLY",
    "telegram_network_error": r"(?i)(NetworkError|TimedOut|httpx\.ConnectError|ReadError|reconnect)",
    "credential_pool_empty": r"no available entries",
    "tool_error": r"returned error",
    "readonly_config_write": r"Read-only file system",
    "drain_timeout": r"drain timed out",
    "failed_turn": r"(?i)failed turn|turn failed",
    "compression_blocked": r"compression is currently blocked",
    "session_compressed_warning": r"Session compressed \d+ times",
}
FACTS = {   # latest line of each, numbers kept: engine configuration facts, never message data
    "model_context": r"Model context warmed",
    "agent_budget": r"Agent budget:",
    "telegram_menu": r"Telegram menu:",
    "tool_schemas": r"Turn machinery warmed",
    "api_server_listen": r"API server listening on",
    "cold_boot_updates": r"Cold boot: \w+ Telegram updates",
    "secret_redaction": r"Secret redaction:",
    "preflight_compression": r"Preflight compression:",
    "session_storage": r"Session storage:",
    "proxy": r"Proxy detected; passing explicitly",
}


def mixed(word):
    return any(c.isdigit() for c in word) and any(c.isupper() for c in word) and any(c.islower() for c in word)


def scrub(s):
    s = TOKEN.sub("[token]", str(s))
    s = WORD.sub(lambda m: "[blob]" if mixed(m.group()) else m.group(), s)
    s = EMAIL.sub("[email]", s)
    s = GROUPED.sub("[nomor]", s)
    return re.sub(r"\d{9,}", "[angka]", s)


def free(s, width=200):
    """Text the bot or a human wrote (titles, summaries): amounts are masked too."""
    s = scrub(re.sub(r"\s+", " ", s or ""))
    return AMOUNT.sub(lambda m: "Rp [n]" if m.group()[:2].lower() == "rp" else "[n]", s)[:width]


def name(s):
    return re.sub(r"\b[0-9a-f]{12,}\b", "H", re.sub(r"\d{5,}", "[n]", scrub(s)))


def fkind(fname):
    """What an uploaded file is (source, bank, document kind, extension), never its name: statement filenames carry
    the owner's name and account fragments."""
    low = str(fname).lower()
    ext = os.path.splitext(low)[1] or "(none)"
    if "@" in low:
        return f"email-named {ext}"
    bank = next((b for b in BANKS if re.search(rf"(?<![a-z]){b}(?![a-z])", low)), None)
    kind = next((k for k, rx in DOC_KINDS if re.search(rx, low)), None)
    parts = ["telegram-doc" if low.startswith("doc_") else "telegram-img" if low.startswith("img_") else None,
             bank, kind, "dated" if re.search(MONTHS, low) else None]
    return " ".join(p for p in parts if p) + f" {ext}" if any(parts) else f"other {ext}"


def json_keys(s):
    """A JSON object in a log line becomes its top-level keys: the values are data, the keys are the engine's."""
    i = s.find("{")
    if i < 0:
        return s
    try:
        obj = json.loads(s[i:])
    except ValueError:
        return s
    return s[:i] + "{" + ",".join(name(k)[:30] for k in obj) + "}" if isinstance(obj, dict) else s


def template(line, width=150):
    s = json_keys(STAMP.sub("", line.strip()))
    m = TEXT_KEY.search(s)
    if m:
        s = s[:m.end()] + "…"
    s = re.sub(r"\buser=.*?(?=\s[\w.]+=|$)", "user=[owner]", s)
    s = re.sub(r"\bfrom [A-Z][a-z]+(?: [A-Z][a-z]+)+", "from [person]", s)
    s = scrub(s)
    s = re.sub(r"'[^']*'", "'…'", s)
    s = re.sub(r'"[^"]*"', '"…"', s)
    s = re.sub(r"\b[0-9a-f]{8,}\b", "H", s)
    s = re.sub(r"\d+", "N", s)
    return s[:width]


def key_template(k):
    """Engine key names (e.g. gateway.admission.result.v2.<hash>): hex ids first, so their digits never become [angka]."""
    s = re.sub(r"[0-9a-fA-F_-]{8,}", lambda m: "H" if re.search(r"\d", m.group()) else m.group(), str(k))
    return re.sub(r"\d+", "N", scrub(s))[:80]


def ro(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def day(ts):
    if ts is None or ts == "":
        return None
    try:
        return datetime.fromtimestamp(float(ts), WIB).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(ts)[:10]


def top(counter, n=None):
    return [[k, v] for k, v in counter.most_common(n)]


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        return {"<unreadable>": type(exc).__name__}


def load_yaml(path):
    """The engine ships ruamel.yaml, not PyYAML."""
    with open(path, encoding="utf-8") as fh:
        try:
            import yaml
            return yaml.safe_load(fh)
        except ImportError:
            from ruamel.yaml import YAML
            return YAML(typ="safe", pure=True).load(fh)


def when(v):
    """Epoch seconds or milliseconds as WIB time (they would otherwise be masked as [angka]); anything else unchanged."""
    if isinstance(v, bool):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    f = f / 1000 if 1e12 <= f < 4e12 else f
    return datetime.fromtimestamp(f, WIB).isoformat(timespec="seconds") if 1e9 <= f < 4e9 else v


TIMEY = re.compile(r"time|date|_at$|^at$|timestamp|boot|seen", re.I)


def shape(obj, depth=0):
    """Keys and types of a JSON document, never its values. A dict keyed by ids or paths collapses to one sample."""
    if depth >= 4:
        return type(obj).__name__
    if isinstance(obj, dict):
        items = list(obj.items())
        kinds = Counter(type(v).__name__ for _, v in items)
        dom, cnt = kinds.most_common(1)[0] if items else ("", 0)
        if len(items) > 8 and dom in ("dict", "list") and cnt >= 0.8 * len(items):
            sample = next(v for _, v in items if type(v).__name__ == dom)
            out = {name(k)[:48]: shape(v, depth + 1) for k, v in items if type(v).__name__ != dom}
            out[f"<{cnt} keys>"] = shape(sample, depth + 1)
            return out
        out = {name(k)[:48]: shape(v, depth + 1) for k, v in items[:30]}
        if len(items) > 30:
            out["…"] = f"{len(items)} keys"
        return out
    if isinstance(obj, list):
        return [shape(obj[0], depth + 1), f"{len(obj)} items"] if obj else []
    return type(obj).__name__


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict) and obj:
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = obj
    return out


def show(v, width=160):
    return scrub(json.dumps(v, ensure_ascii=False, default=repr))[:width]


# --------------------------------------------------------------------------------------------------------------- engine
def engine():
    out = {"python": sys.version.split()[0], "executable": sys.executable, "release_date": None, "stamp": {}}
    init = os.path.join(H, "hermes_cli", "__init__.py")
    if os.path.exists(init):
        m = re.search(r'__release_date__\s*=\s*"([^"]+)"', open(init).read())
        out["release_date"] = m.group(1) if m else None
    stamp = read_json(os.path.join(H, "install-stamp.json"))
    out["stamp"] = {k: scrub(when(v) if TIMEY.search(k) else v) for k, v in flatten(stamp).items()
                    if not TEXTY.search(k.split(".")[-1]) or "version" in k or "commit" in k or "sha" in k} \
        if isinstance(stamp, dict) else {}
    out["manifest"] = shape(read_json(os.path.join(H, "manifest.json")))
    try:
        from importlib import metadata
        out["packages"] = sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions() if d.metadata["Name"])
    except Exception as exc:
        out["packages"] = [f"<{type(exc).__name__}>"]
    out["bundled_plugins"] = sorted(d for d in os.listdir(os.path.join(H, "plugins")) if not d.startswith(("_", "."))) \
        if os.path.isdir(os.path.join(H, "plugins")) else []
    out["platform_plugins"] = sorted(d for d in os.listdir(os.path.join(H, "plugins", "platforms")) if not d.startswith(("_", "."))) \
        if os.path.isdir(os.path.join(H, "plugins", "platforms")) else []
    out["env_names"] = sorted(k for k in os.environ)   # names only: values are secrets or noise
    out["env_safe"] = {k: scrub(os.environ[k]) for k in ("HERMES_HOME", "TZ", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "PATH", "HOME")
                       if k in os.environ}
    return out


# --------------------------------------------------------------------------------------------------------------- config
def defaults_module():
    """DEFAULT_CONFIG and OPTIONAL_ENV_VARS without running hermes_cli/__init__.py (a pure-data leaf module)."""
    pkg = types.ModuleType("hermes_cli")
    pkg.__path__ = [os.path.join(H, "hermes_cli")]
    sys.modules.setdefault("hermes_cli", pkg)
    sys.path.insert(0, H)
    import importlib
    return importlib.import_module("hermes_cli.config_defaults")


def key_lines(path):
    """dotted key -> (line, doc comment) for every literal key of DEFAULT_CONFIG, from the source."""
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    tree = ast.parse(src)
    out = {}

    def doc(lineno):
        own = lines[lineno - 1]
        trail = own.split("  # ", 1)[1].strip() if "  # " in own else ""
        above = []
        i = lineno - 2
        while i >= 0 and lines[i].strip().startswith("#"):
            above.insert(0, lines[i].strip().lstrip("#").strip())
            i -= 1
        return " ".join(x for x in above + [trail] if x)[:400]

    def walk(node, prefix):
        if not isinstance(node, ast.Dict):
            return
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                key = prefix + k.value
                out[key] = (k.lineno, doc(k.lineno))
                walk(v, key + ".")

    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEFAULT_CONFIG" for t in stmt.targets):
            walk(stmt.value, "")
    return out


def config():
    mod = defaults_module()
    dflt = mod.DEFAULT_CONFIG
    ours = load_yaml(os.path.join(D, "config.yaml")) or {}
    lines = key_lines(mod.__file__)
    flat_d, flat_o = flatten(dflt), flatten(ours)
    overrides = []
    for k in sorted(flat_o):
        parent = next((p for p in (k.rsplit(".", i)[0] for i in range(k.count(".") + 1)) if p in flat_d or p in lines), None)
        known = k in flat_d or k in lines
        line, docs = lines.get(k) or lines.get(parent or "", (None, ""))
        overrides.append({"key": k, "ours": show(flat_o[k]), "default": show(flat_d[k]) if k in flat_d else None,
                          "known": known, "nearest_known": parent, "line": line, "doc": scrub(docs)})
    sections = []
    for top_key, v in dflt.items():
        sections.append({"section": top_key, "line": (lines.get(top_key) or (None,))[0],
                         "keys": len(flatten(v)) if isinstance(v, dict) else 1,
                         "ours": sorted({k for k in flat_o if k == top_key or k.startswith(top_key + ".")})})
    table = [{"key": k, "default": show(v, 120), "line": (lines.get(k) or (None,))[0], "doc": scrub((lines.get(k) or (0, ""))[1])}
             for k, v in sorted(flat_d.items())]
    env = getattr(mod, "OPTIONAL_ENV_VARS", {}) or {}
    env_rows = []
    for k in sorted(env):
        meta = env[k] if isinstance(env[k], dict) else {}
        env_rows.append({"name": k, "category": scrub(meta.get("category", "")), "secret": bool(meta.get("password") or meta.get("secret")),
                         "desc": scrub(str(meta.get("description", "")))[:160]})
    raw = open(os.path.join(D, "config.yaml"), "rb").read()
    return {"config_version_default": dflt.get("_config_version"), "config_version_ours": ours.get("_config_version"),
            "config_sha256": hashlib.sha256(raw).hexdigest(), "defaults_source": mod.__file__, "overrides": overrides,
            "sections": sections, "defaults": table, "optional_env": env_rows,
            "soul_sha256": hashlib.sha256(open(os.path.join(D, "SOUL.md"), "rb").read()).hexdigest()
            if os.path.exists(os.path.join(D, "SOUL.md")) else None}


# --------------------------------------------------------------------------------------------------------------- layout
def layout():
    rows = []
    for entry in sorted(os.listdir(D)):
        p = os.path.join(D, entry)
        st = os.lstat(p)
        row = {"name": name(entry), "mode": oct(st.st_mode & 0o7777), "owner": f"{st.st_uid}:{st.st_gid}",
               "mtime": day(st.st_mtime), "type": "dir" if stat.S_ISDIR(st.st_mode) else "link" if stat.S_ISLNK(st.st_mode) else "file"}
        if row["type"] == "file":
            row["bytes"] = st.st_size
        elif row["type"] == "dir":
            files, size, exts, children = 0, 0, Counter(), Counter()
            for root, dirs, fs in os.walk(p):
                rel = os.path.relpath(root, D)
                for f in fs:
                    try:
                        size += os.lstat(os.path.join(root, f)).st_size
                    except OSError:
                        pass
                    files += 1
                    exts[os.path.splitext(f)[1].lower() or "(none)"] += 1
                    children[name(rel.split(os.sep, 2)[1]) if rel.count(os.sep) >= 1 else "."] += 1
            row.update(files=files, bytes=size, exts=dict(exts.most_common(12)), children=dict(children.most_common(25)))
        rows.append(row)
    ro_mounts = {}
    with open("/proc/self/mountinfo") as fh:
        for line in fh:
            parts = line.split()
            if parts[4].startswith(D) or parts[4] == D:
                ro_mounts[parts[4]] = "ro" if "ro" in parts[5].split(",") else "rw"
    return {"entries": rows, "mounts": ro_mounts}


def json_shapes():
    out = {}
    for rel in ("gateway_state.json", "channel_directory.json", "gateway/restart_loop.json", "runtime/active_sessions.json",
                "spawn-ledger.json", "state/gateway.lifecycle.json", "sessions/sessions.json", "cache/mcp_schema_cache.json",
                "cache/tool_discovery_cache.json", "cache/schema_columns.json", ".skills_prompt_snapshot.json",
                "gateways/default/current"):
        p = os.path.join(D, rel)
        if os.path.isfile(p):
            out[rel] = {"bytes": os.path.getsize(p), "mtime": day(os.path.getmtime(p)), "shape": shape(read_json(p))}
    return out


def gateway():
    gs = read_json(os.path.join(D, "gateway_state.json"))
    platforms = {}
    for pname, pv in ((gs.get("platforms") or {}).items() if isinstance(gs, dict) else []):
        platforms[pname] = {k: scrub(v) for k, v in flatten(pv).items() if not re.search(r"token|secret|key|chat|user", k, re.I)}
    top_level = {k: scrub(when(v) if TIMEY.search(k) else v) for k, v in flatten({k: v for k, v in gs.items() if k != "platforms"}).items()
                 if not TEXTY.search(k.split(".")[-1])} if isinstance(gs, dict) else {}
    loop = read_json(os.path.join(D, "gateway/restart_loop.json"))
    boots = loop.get("boots") if isinstance(loop, dict) else None
    lifecycle = read_json(os.path.join(D, "state/gateway.lifecycle.json"))
    sess = read_json(os.path.join(D, "sessions/sessions.json"))
    kinds, sums = Counter(), Counter()
    if isinstance(sess, dict):
        for k, v in sess.items():
            kinds[re.sub(r":[^:]*\d{5,}[^:]*$|:local-[^:]+$", ":<id>", k)] += 1
            if isinstance(v, dict):
                for fk, fv in v.items():
                    if isinstance(fv, (int, float)) and not isinstance(fv, bool) and re.search(r"token|cost|count", fk):
                        sums[fk] += fv
    active = read_json(os.path.join(D, "runtime/active_sessions.json"))
    spawn = read_json(os.path.join(D, "spawn-ledger.json"))
    chan = read_json(os.path.join(D, "channel_directory.json"))
    return {"platforms": platforms, "state": top_level,
            "restart_loop": {"boots": len(boots) if isinstance(boots, list) else None,
                             "last_boots": [scrub(when(b) if not isinstance(b, dict) else {k: when(v) for k, v in b.items() if not TEXTY.search(k)})
                                            for b in (boots or [])[-8:]] if isinstance(boots, list) else []},
            "lifecycle": {k: scrub(when(v) if TIMEY.search(k) else v) for k, v in flatten(lifecycle).items()
                          if not TEXTY.search(k.split(".")[-1])} if isinstance(lifecycle, dict) else {},
            "sessions_json": {"keys": dict(kinds), "sums": {k: round(v, 4) for k, v in sums.items()}},
            "active_sessions": len(active) if isinstance(active, (list, dict)) else None,
            "spawn_ledger": len(spawn) if isinstance(spawn, (list, dict)) else None,
            "channel_directory": shape(chan)}


def socket_inodes():
    found = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                link = os.readlink(f"/proc/{pid}/fd/{fd}")
                if link.startswith("socket:["):
                    found[link[8:-1]] = int(pid)
        except OSError:
            continue
    return found


def socket_inodes_as(uid):
    """Root in this container has no CAP_SYS_PTRACE, so another uid's /proc/<pid>/fd is unreadable: read it as that uid."""
    r, w = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(r)
            os.setgroups([])
            os.setgid(uid)
            os.setuid(uid)
            os.write(w, json.dumps(socket_inodes()).encode())
        finally:
            os._exit(0)
    os.close(w)
    data = b""
    while True:
        chunk = os.read(r, 65536)
        if not chunk:
            break
        data += chunk
    os.close(r)
    os.waitpid(child, 0)
    return json.loads(data or b"{}")


def sockets():
    inode_pid = socket_inodes()
    procs = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
            cmd = [c.decode(errors="replace") for c in cmd if c][:6]
            rss = re.search(r"VmRSS:\s+(\d+)", open(f"/proc/{pid}/status").read())
            user = re.search(r"Uid:\s+(\d+)", open(f"/proc/{pid}/status").read())
            procs.append({"pid": int(pid), "uid": int(user.group(1)) if user else None, "rss_mb": int(rss.group(1)) // 1024 if rss else 0,
                          "cmd": scrub(" ".join(cmd))[:140]})
        except OSError:
            continue
    for uid in sorted({p["uid"] for p in procs if p["uid"]}):
        try:
            inode_pid.update(socket_inodes_as(uid))
        except OSError:
            pass
    listen = []
    for proto in ("tcp", "tcp6", "udp", "udp6"):
        try:
            rows = open(f"/proc/net/{proto}").read().splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            p = row.split()
            if proto.startswith("tcp") and p[3] != "0A":
                continue
            addr, port = p[1].split(":")
            if len(addr) == 8:
                ip = ".".join(str(int(addr[i:i + 2], 16)) for i in (6, 4, 2, 0))
            else:
                ip = "::" if set(addr) == {"0"} else ("::1" if addr.endswith("01000000") and set(addr[:24]) == {"0"} else "ipv6:" + addr[-8:])
            listen.append({"proto": proto, "ip": ip, "port": int(port, 16), "pid": inode_pid.get(p[9])})
    return {"listen": sorted(listen, key=lambda r: (r["proto"], r["port"])), "processes": sorted(procs, key=lambda r: r["pid"])}


# --------------------------------------------------------------------------------------------------------------- extensions
def plugins_skills_cron():
    out = {"plugins": [], "skills": {}, "pending": [], "cron": {}, "ttl": {}, "backups": [], "receipts": []}
    pdir = os.path.join(D, "plugins")
    for pname in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        manifest = os.path.join(pdir, pname, "plugin.yaml")
        info = {"name": pname, "files": sorted(f for f in os.listdir(os.path.join(pdir, pname)) if not f.startswith("__pycache__"))}
        if os.path.exists(manifest):
            info["manifest"] = {k: scrub(v) for k, v in flatten(load_yaml(manifest) or {}).items()}
        out["plugins"].append(info)
    sdir = os.path.join(D, "skills")
    for cat in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        cp = os.path.join(sdir, cat)
        if os.path.isdir(cp):
            out["skills"][cat] = sorted(s for s in os.listdir(cp) if os.path.isdir(os.path.join(cp, s)))
    snap = read_json(os.path.join(D, ".skills_prompt_snapshot.json"))
    out["skills_snapshot"] = shape(snap)
    for f in sorted(os.listdir(os.path.join(D, "pending", "skills"))) if os.path.isdir(os.path.join(D, "pending", "skills")) else []:
        j = read_json(os.path.join(D, "pending", "skills", f))
        ops = ((j.get("payload") or {}).get("operations") or []) if isinstance(j, dict) else []
        out["pending"].append({"file": name(f), "subsystem": j.get("subsystem"), "action": j.get("action"), "origin": name(str(j.get("origin")))[:80],
                               "created": day(j.get("created_at")), "summary": free(j.get("summary")),
                               "operations": [{k: free(str(v), 60) for k, v in o.items() if k in ("op", "type", "action", "name", "path", "category")}
                                              for o in ops if isinstance(o, dict)]})
    cdir = os.path.join(D, "cron")
    if os.path.isdir(cdir):
        out["cron"]["files"] = sorted(name(f) for f in os.listdir(cdir))
        for f in os.listdir(cdir):
            p = os.path.join(cdir, f)
            if f.endswith(".db"):
                con = ro(p)
                out["cron"][f] = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                                  for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            elif f.endswith(".json"):
                j = read_json(p)
                out["cron"][f] = {"entries": len(j) if isinstance(j, (list, dict)) else None, "shape": shape(j)}
    ttl = os.path.join(D, "ttl")
    for f in sorted(os.listdir(ttl)) if os.path.isdir(ttl) else []:
        n = expired = 0
        for line in open(os.path.join(ttl, f), errors="replace"):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            n += 1
            expired += 1 if float(row.get("exp") or 0) < time.time() else 0
        out["ttl"][f] = {"lines": n, "expired": expired}
    bdir = os.path.join(D, "backups", "config")
    for f in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
        out["backups"].append({"file": name(f), "mtime": day(os.path.getmtime(os.path.join(bdir, f))),
                               "sha256": hashlib.sha256(open(os.path.join(bdir, f), "rb").read()).hexdigest()})
    rdir = os.path.join(D, "logs", "update_receipts")
    for f in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        j = read_json(os.path.join(rdir, f))
        out["receipts"].append({"file": name(f), "fields": {k: scrub(v)[:80] for k, v in flatten(j).items()
                                                            if re.search(r"version|from|to$|status|result|at$|kind|ok", k)}
                                if isinstance(j, dict) else shape(j)})
    for sub in BYTES_ONLY:
        p = os.path.join(D, sub)
        if os.path.isdir(p):
            files = [f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))]
            out.setdefault("uploads", {})[sub] = {
                "files": len(files), "bytes": sum(os.path.getsize(os.path.join(p, f)) for f in files),
                "exts": dict(Counter(os.path.splitext(f)[1].lower() for f in files)),
                "kinds": dict(Counter(fkind(f) for f in files).most_common(15)),
                "newest": day(max((os.path.getmtime(os.path.join(p, f)) for f in files), default=None))}
    return out


def mcp():
    cache = read_json(os.path.join(D, "cache", "mcp_schema_cache.json"))
    servers = {}
    for sname, entry in (cache.items() if isinstance(cache, dict) else []):
        if not isinstance(entry, dict):
            continue
        tools = []
        for t in entry.get("tools") or []:
            schema = t.get("inputSchema") or t.get("input_schema") or t.get("parameters") or {}
            props = schema.get("properties") or {}
            req = set(schema.get("required") or [])
            params = []
            for pname, pv in props.items():
                typ = pv.get("type") or "/".join(x.get("type", "?") for x in pv.get("anyOf", []) if isinstance(x, dict)) or "?"
                params.append(f"{pname}{'' if pname in req else '?'}:{typ}" + (f"={show(pv['default'], 24)}" if "default" in pv else ""))
            desc = (t.get("description") or "").strip().splitlines()
            tools.append({"name": t.get("name"), "params": params, "desc": scrub(desc[0])[:200] if desc else ""})
        servers[sname] = {"fingerprint": str(entry.get("fingerprint"))[:16], "tools": tools,
                          "utility_tools": [u.get("name") if isinstance(u, dict) else str(u) for u in entry.get("utility_tools") or []]}
    disc = read_json(os.path.join(D, "cache", "tool_discovery_cache.json"))
    return {"servers": servers, "discovery_shape": shape(disc)}


# --------------------------------------------------------------------------------------------------------------- state.db
def db_profile(path):
    if not os.path.exists(path):
        return None
    con = ro(path)
    tables = {}
    for r in con.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"):
        t = r["name"]
        cols = [(c[1], c[2]) for c in con.execute(f'PRAGMA table_info("{t}")')]
        try:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except sqlite3.Error as exc:
            n = f"<{type(exc).__name__}>"
        info = {"type": r["type"], "rows": n, "cols": cols, "virtual": "VIRTUAL TABLE" in (r["sql"] or "").upper()}
        if isinstance(n, int) and 0 < n <= 200000 and not info["virtual"]:
            cats = {}
            for c, typ in cols:
                if c.lower() in CATEGORICAL or (c.lower().endswith(("_state", "_status", "_reason", "_kind", "_type")) and not TEXTY.search(c)):
                    vals = con.execute(f'SELECT "{c}", COUNT(*) FROM "{t}" GROUP BY 1 ORDER BY 2 DESC LIMIT 15').fetchall()
                    if len(vals) <= 14:
                        cats[c] = {scrub(v[0])[:60]: v[1] for v in vals}
            if cats:
                info["categories"] = cats
            span = [c for c, _ in cols if re.search(r"(^|_)(at|ts|timestamp|time|started|ended|created|updated|first_seen|last_seen)$", c)]
            if span:
                c = span[0]
                lo, hi = con.execute(f'SELECT MIN("{c}"), MAX("{c}") FROM "{t}"').fetchone()
                info["span"] = [c, day(lo), day(hi)]
            keycol = next((c for c, _ in cols if c.lower() in ("key", "meta_key")), None)
            if keycol and n <= 5000:   # key/value tables: the engine's key names, templated; values never read
                info["keys"] = top(Counter(key_template(k) for (k,) in con.execute(f'SELECT "{keycol}" FROM "{t}"')), 30)
        tables[t] = info
    idx = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY 1")]
    meta = {"user_version": con.execute("PRAGMA user_version").fetchone()[0],
            "journal_mode": con.execute("PRAGMA journal_mode").fetchone()[0],
            "bytes": os.path.getsize(path), "wal_bytes": os.path.getsize(path + "-wal") if os.path.exists(path + "-wal") else 0}
    return {"meta": meta, "tables": tables, "indexes": idx}


SONNET = {"5m": (2.0, 10.0, 0.20, 2.50), "1h": (2.0, 10.0, 0.20, 4.0)}   # USD per MTok, same rates as ops/calibration/bot_usage.py


def activity():
    con = ro(os.path.join(D, "state.db"))
    cols = lambda t: {r[1] for r in con.execute(f'PRAGMA table_info("{t}")')}  # noqa: E731
    sc, mc, uc = cols("sessions"), cols("messages"), cols("session_model_usage")
    start = next((c for c in ("started_at", "created_at", "start_time") if c in sc), None)
    out = {"sessions_by_day": defaultdict(lambda: Counter()), "messages_by_day": defaultdict(lambda: Counter()),
           "events_by_day": {}, "usage_by_day": defaultdict(lambda: defaultdict(float)), "usage_by_month": defaultdict(lambda: defaultdict(float))}
    num = [c for c in ("message_count", "tool_call_count", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
                       "reasoning_tokens", "estimated_cost_usd") if c in sc]
    end_reasons, models, sources = Counter(), Counter(), Counter()
    for r in con.execute(f'SELECT * FROM sessions'):
        d = day(r[start]) if start else None
        src = r["source"] if "source" in sc else "?"
        sources[src] += 1
        b = out["sessions_by_day"][f"{d} {src}"]
        b["sessions"] += 1
        b["children"] += 1 if "parent_session_id" in sc and r["parent_session_id"] else 0
        for c in num:
            b[c] += r[c] or 0
        if "end_reason" in sc:
            end_reasons[str(r["end_reason"])] += 1
        if "model" in sc:
            models[str(r["model"])] += 1
    comp_cols = sorted(c for c in sc if c.startswith("compression"))
    roles = Counter()
    extra = [c for c in ("compacted", "active", "display_kind", "finish_reason") if c in mc]
    for r in con.execute(f"SELECT timestamp, role{''.join(', ' + c for c in extra)} FROM messages"):
        d = day(r["timestamp"]) or "?"
        out["messages_by_day"][d][r["role"]] += 1
        roles[r["role"]] += 1
        if "compacted" in mc and r["compacted"]:
            out["messages_by_day"][d]["compacted"] += 1
        if "display_kind" in mc and r["display_kind"] == "failed_turn":
            out["messages_by_day"][d]["failed_turn"] += 1
    calls, calls_tg, odd = Counter(), Counter(), defaultdict(Counter)
    src = {r[0]: r[1] for r in con.execute("SELECT id, source FROM sessions")} if "source" in sc else {}
    for r in con.execute("SELECT session_id, timestamp, tool_calls FROM messages WHERE role='assistant' AND tool_calls IS NOT NULL"):
        try:
            for tc in json.loads(r["tool_calls"]):
                n = (tc.get("function") or {}).get("name") or tc.get("name")
                calls[n] += 1
                if src.get(r["session_id"]) == "telegram":
                    calls_tg[n] += 1
                if not str(n).startswith("mcp__"):   # engine tools (and the lazy-loading meta tools while tool_search was on)
                    odd[n][f"{day(r['timestamp'])} {src.get(r['session_id'], '?')}"] += 1
        except (ValueError, TypeError, AttributeError):
            calls["<unparsed>"] += 1
    flags = defaultdict(Counter)
    for r in con.execute("SELECT tool_name, content FROM messages WHERE role='tool'"):
        t = (r["content"] or "").lower()   # read in the container for yes/no flags only; the text never leaves
        flags[str(r["tool_name"])]["results"] += 1
        if '"error"' in t or '"iserror": true' in t or t.startswith("error"):
            flags[str(r["tool_name"])]["error_field"] += 1
        if any(k in t for k in ("gagal", "ditolak", "tidak bisa", "tidak ditemukan", "belum cocok")):
            flags[str(r["tool_name"])]["refusal_words"] += 1
        if any(k in t for k in ("unknown tool", "no such tool", "tool not found", "not available")):
            flags[str(r["tool_name"])]["unknown_tool"] += 1
    for r in con.execute("SELECT * FROM session_model_usage"):
        g = lambda c: (r[c] or 0) if c in uc else 0  # noqa: E731
        d = day(r["first_seen"]) if "first_seen" in uc else None
        model = r["model"] if "model" in uc else "?"
        task = r["task"] if "task" in uc else "?"
        rates = SONNET["5m"] if "sonnet" in str(model) else None
        cost = ((g("input_tokens") * rates[0] + g("output_tokens") * rates[1] + g("cache_read_tokens") * rates[2]
                 + g("cache_write_tokens") * rates[3]) / 1e6) if rates else 0.0
        for bucket in (out["usage_by_day"][f"{d} {model} {task}"], out["usage_by_month"][f"{(d or '?')[:7]} {model}"]):
            bucket["rows"] += 1
            for c in ("api_call_count", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens",
                      "estimated_cost_usd"):
                if c in uc:
                    bucket[c] += r[c] or 0
            bucket["list_cost_usd"] += cost
    prompts = {}
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "system_prompts" in tables:   # despite the name: snapshots {tools, version} of the tool schemas sent with each prompt
        snaps = [r[0] for r in con.execute("SELECT prompt FROM system_prompts ORDER BY rowid")]
        try:
            latest = json.loads(snaps[-1]) if snaps else {}
        except ValueError:
            latest = {}
        tools = (latest.get("tools") or []) if isinstance(latest, dict) else []
        names = [str((t.get("function") or {}).get("name") or t.get("name")) for t in tools if isinstance(t, dict)]
        prompts.update(tool_schema_snapshots=len(snaps), latest_tools=len(names),
                       latest_mcp_tools=sum(1 for n in names if n.startswith("mcp__")),
                       latest_engine_tools=sorted(n for n in names if not n.startswith("mcp__")))
    if "system_prompt" in sc:
        soul = open(os.path.join(D, "SOUL.md"), encoding="utf-8").read() if os.path.exists(os.path.join(D, "SOUL.md")) else ""
        soul_lines = [ln.strip() for ln in soul.splitlines() if len(ln.strip()) >= 25]
        soul_heads = {ln.strip() for ln in soul.splitlines() if re.match(r"#{1,4} ", ln.strip())}
        order = f'"{start}" DESC' if start else "rowid DESC"
        row = con.execute(f"SELECT system_prompt FROM sessions WHERE system_prompt IS NOT NULL AND system_prompt != '' "
                          f"ORDER BY {order} LIMIT 1").fetchone()
        last = prompt_text(row[0]) if row else ""
        heads = [ln.strip() for ln in last.splitlines() if re.match(r"#{1,4} |<[a-z_]+>$", ln.strip())]
        prompts.update(
            sessions_with_prompt_text=con.execute("SELECT COUNT(*) FROM sessions WHERE system_prompt IS NOT NULL "
                                                  "AND system_prompt != ''").fetchone()[0],
            distinct_system_prompts=con.execute("SELECT COUNT(DISTINCT system_prompt_hash) FROM sessions").fetchone()[0]
            if "system_prompt_hash" in sc else None,
            latest_chars=len(last), latest_soul_lines_present=f"{sum(1 for ln in soul_lines if ln in last)}/{len(soul_lines)}",
            latest_headings_from_soul=sum(1 for h in heads if h in soul_heads),
            # engine-added headings (masked like free text): what Hermes wraps around SOUL.md
            latest_engine_headings=[free(h, 80) for h in heads if h not in soul_heads][:40],
            latest_mentions_skills_index="<available_skills>" in last or "skills_list" in last,
            latest_mentions_mcp_tools=last.count("mcp__vault_tools__"))
    deliveries = {}
    if "delivery_obligations" in {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
        dc = cols("delivery_obligations")
        if "state" in dc:
            deliveries["by_state"] = {str(k): v for k, v in con.execute("SELECT state, COUNT(*) FROM delivery_obligations GROUP BY 1")}
        if "attempts" in dc:
            deliveries["attempts"] = {str(k): v for k, v in con.execute("SELECT attempts, COUNT(*) FROM delivery_obligations GROUP BY 1")}
        if "last_error" in dc:
            deliveries["errors"] = top(Counter(template(r[0] or "", 100) for r in con.execute(
                "SELECT last_error FROM delivery_obligations WHERE last_error IS NOT NULL AND last_error != ''")), 12)
    out = {k: ({kk: dict(vv) for kk, vv in sorted(v.items())} if isinstance(v, defaultdict) else v) for k, v in out.items()}
    out.update(roles=dict(roles), end_reasons=dict(end_reasons), models=dict(models), sources=dict(sources), compression_columns=comp_cols,
               tool_calls=top(calls), tool_calls_telegram=top(calls_tg), engine_tool_calls={k: dict(v) for k, v in odd.items()},
               tool_result_flags={k: dict(v) for k, v in sorted(flags.items())}, system_prompts=prompts, deliveries=deliveries)
    return out


def prompt_text(raw):
    """system_prompts rows may hold the prompt as JSON blocks; return the plain text."""
    try:
        j = json.loads(raw)
    except (ValueError, TypeError):
        return raw or ""
    if isinstance(j, list):
        return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in j)
    if isinstance(j, dict):
        return str(j.get("text") or j.get("content") or j.get("prompt") or "")
    return str(j)


# --------------------------------------------------------------------------------------------------------------- logs
def logs():
    out = {}
    root = os.path.join(D, "logs")
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "update_receipts"]
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, D)
            info = {"bytes": os.path.getsize(p), "mtime": day(os.path.getmtime(p))}
            if f.endswith(".json"):
                info["shape"] = shape(read_json(p))
                out[rel] = info
                continue
            templates, levels, loggers, per_day, events = Counter(), Counter(), Counter(), Counter(), defaultdict(Counter)
            facts = {}
            first = last = None
            n = 0
            with open(p, errors="replace") as fh:
                for line in fh:
                    n += 1
                    m = STAMP.match(line)
                    d = m.group(1) if m else None
                    if d:
                        first = first or d
                        last = d
                        per_day[d] += 1
                    lm = re.match(r"^\S+ \S+ (DEBUG|INFO|WARNING|ERROR|CRITICAL) ([\w.\-]+):", line)
                    if lm:
                        levels[lm.group(1)] += 1
                        loggers[f"{lm.group(1)} {lm.group(2)}"] += 1
                    for ev, rx in EVENTS.items():
                        if re.search(rx, line):
                            events[ev][d or "?"] += 1
                    for fk, rx in FACTS.items():
                        if re.search(rx, line):
                            facts[fk] = (f"{line[:16]} " if d else "") + scrub(STAMP.sub("", line.strip()))[:220]
                    t = template(line)
                    if t:
                        templates[t] += 1
            keep = templates.most_common() if f == "errors.log" or n < 2000 else [(t, c) for t, c in templates.most_common(80) if c >= 2]
            info.update(lines=n, first=first, last=last, levels=dict(levels), loggers=top(loggers, 40), templates=[[t, c] for t, c in keep][:160],
                        distinct_templates=len(templates), lines_by_day=dict(sorted(per_day.items())), facts=facts,
                        events={k: dict(sorted(v.items())) for k, v in events.items()})
            out[rel] = info
    return out


SECTIONS = {"engine": engine, "config": config, "layout": layout, "json_shapes": json_shapes, "gateway": gateway, "sockets": sockets,
            "extensions": plugins_skills_cron, "mcp": mcp, "activity": activity, "logs": logs}
result = {}
for key, fn in SECTIONS.items():
    try:
        result[key] = fn()
    except Exception as exc:   # one failing section must not hide the others
        result[key] = {"<error>": f"{type(exc).__name__}: {scrub(exc)[:200]}"}
result["databases"] = {}
for rel in ("state.db", "kanban.db", "projects.db", "response_store.db", "runs_idempotency.db", "cron/executions.db"):
    try:
        result["databases"][rel] = db_profile(os.path.join(D, rel))
    except Exception as exc:
        result["databases"][rel] = {"<error>": f"{type(exc).__name__}: {scrub(exc)[:200]}"}
result["collected_at"] = datetime.now(WIB).isoformat(timespec="seconds")
print(json.dumps(result, sort_keys=True, default=str))
