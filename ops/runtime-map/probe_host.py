"""Host side of the runtime map: OS, listening ports, firewall, containers, networks, volumes, pa-* timers, squid zones,
the deployed tree. Runs as root on the VPS (collect.py pipes it):
  ssh ubuntu@<vps> 'sudo python3 -' < ops/runtime-map/probe_host.py
Read-only. Never opens a secret: env values only for SAFE_ENV keys, secret files by name and mode only, no `docker compose
config` (it interpolates secrets into the output). Prints one JSON object; free text is reduced to masked templates."""
import hashlib
import json
import os
import re
import stat
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone

PROJECT = "personal-agent"
WIB = timezone(timedelta(hours=7))
DEPLOY = "/opt/personal-agent"
DATA = "/opt/personal-agent-data"
SECRETS = "/opt/personal-agent-secrets"
SAFE_ENV = {"HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy", "TZ", "LANG", "HOME", "PATH",
            "PYTHONUNBUFFERED", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "PYTHON_VERSION", "VIRTUAL_ENV", "XDG_RUNTIME_DIR", "CC", "CXX",
            "PLAYWRIGHT_BROWSERS_PATH", "LEDGER_DB", "HERMES_HOME", "HERMES_PYTHON", "HERMES_RUNTIME_DIR", "HERMES_SKIP_CONFIG_MIGRATION",
            "HERMES_TUI_DIR", "HERMES_WEB_DIST", "HERMES_WRITE_SAFE_ROOT", "MY_TELEGRAM_ID", "TELEGRAM_ALLOWED_USERS",
            "TELEGRAM_HOME_CHANNEL"}   # Telegram ids are masked by scrub(); tokens and keys are never in this set
TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9_-]+|\bntn_[A-Za-z0-9]+|\bsecret_[A-Za-z0-9]{20,}"
                   r"|ya29\.[A-Za-z0-9_.-]+|\b1//[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{12,}|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}")
TS = re.compile(r"^(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*|\w{3} \d{1,2} \d{2}:\d{2}:\d{2})\s+(?:\S+\s+\S+?(?:\[\d+\])?:\s+)?")


def mixed(word):
    return any(c.isdigit() for c in word) and any(c.isupper() for c in word) and any(c.islower() for c in word)


def scrub(s):
    s = TOKEN.sub("[token]", str(s))
    s = re.sub(r"[A-Za-z0-9_\-]{20,}", lambda m: "[blob]" if mixed(m.group()) else m.group(), s)
    s = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email]", s)
    s = re.sub(r"\b\d{3,4}(?:[ -]\d{3,4}){2,}\b", "[nomor]", s)
    return re.sub(r"\d{9,}", "[angka]", s)


def template(line, width=150):
    s = TS.sub("", line.strip())
    s = re.sub(r"'[^']*'", "'…'", s)
    s = re.sub(r'"[^"]*"', '"…"', s)
    s = re.sub(r"\b[0-9a-f]{8,}\b", "H", s)
    s = re.sub(r"\d+", "N", s)
    return scrub(s)[:width]


def run(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return p.stdout
    except Exception as exc:  # a missing tool is a fact for the map, not a crash
        return f"<{type(exc).__name__}>"


def short_image(ref):
    """A digest has long digit runs that scrub() would mangle: keep its first 12 hex characters."""
    return re.sub(r"@sha256:([0-9a-f]{12})[0-9a-f]+", r"@sha256:\1…", ref or "")


def short_volume(vol):
    return vol[:12] if re.fullmatch(r"[0-9a-f]{64}", vol or "") else vol


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def top(counter, n):
    return [[k, v] for k, v in counter.most_common(n)]


def os_info():
    rel = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', open("/etc/os-release").read(), re.M))
    mem = re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read())
    return {"pretty": rel.get("PRETTY_NAME"), "kernel": run(["uname", "-r"]).strip(), "cpus": os.cpu_count(),
            "mem_total_mb": int(mem.group(1)) // 1024 if mem else None,
            "docker": run(["docker", "version", "--format", "{{.Server.Version}}"]).strip(),
            "compose": run(["docker", "compose", "version", "--short"]).strip(),
            "timezone": run(["timedatectl", "show", "-p", "Timezone", "--value"]).strip()}


def usage():
    st = os.statvfs("/")
    mem = dict(re.findall(r"(\w+):\s+(\d+)", open("/proc/meminfo").read()))
    return {"disk_root_gb": round(st.f_blocks * st.f_frsize / 1e9, 1), "disk_root_used_pct": round(100 * (1 - st.f_bavail / st.f_blocks), 1),
            "mem_available_mb": int(mem.get("MemAvailable", 0)) // 1024, "uptime_days": round(float(open("/proc/uptime").read().split()[0]) / 86400, 1),
            "docker_df": [scrub(x) for x in run(["docker", "system", "df", "--format", "{{.Type}} {{.TotalCount}} {{.Size}} {{.Reclaimable}}"]).splitlines()],
            "collected_at": run(["date", "-Iseconds"]).strip()}


def listening():
    out = []
    for proto, flag in (("tcp", "-tlnpH"), ("udp", "-ulnpH")):
        for line in run(["ss", flag]).splitlines():
            parts = line.split()
            local = next((p for p in parts if re.search(r":\d+$", p) or p.endswith(":*")), "")
            procs = sorted(set(re.findall(r'\("([^"]+)"', line)))
            if local:
                out.append({"proto": proto, "local": local, "process": ",".join(procs)})
    return sorted(out, key=lambda r: (r["proto"], r["local"]))


def security():
    sshd = {}
    for line in run(["sshd", "-T"]).splitlines():
        k, _, v = line.partition(" ")
        if k in ("port", "permitrootlogin", "passwordauthentication", "pubkeyauthentication", "kbdinteractiveauthentication",
                 "x11forwarding", "allowusers", "allowgroups", "maxauthtries", "clientaliveinterval"):
            sshd[k] = scrub(v)
    auto = open("/etc/apt/apt.conf.d/20auto-upgrades").read() if os.path.exists("/etc/apt/apt.conf.d/20auto-upgrades") else ""
    return {"ufw": [scrub(x) for x in run(["ufw", "status", "verbose"]).splitlines() if x.strip()],
            "nft_or_iptables_rules": len([x for x in run(["iptables", "-S"]).splitlines() if x.startswith("-A")]),
            "sshd": sshd,
            "auto_upgrades": dict(re.findall(r'(APT::Periodic::\S+)\s+"([^"]*)"', auto)),
            "fail2ban": run(["systemctl", "is-active", "fail2ban"]).strip() or "absent",
            "root_crontab": [scrub(x) for x in run(["crontab", "-l", "-u", "root"]).splitlines() if x.strip() and not x.startswith("#")],
            "cron_d": sorted(os.listdir("/etc/cron.d")) if os.path.isdir("/etc/cron.d") else [],
            "docker_daemon_json": scrub(open("/etc/docker/daemon.json").read()) if os.path.exists("/etc/docker/daemon.json") else None,
            "ssh_authorized_keys": {u: len([x for x in open(p).read().splitlines() if x.strip() and not x.startswith("#")])
                                    for u, p in (("ubuntu", "/home/ubuntu/.ssh/authorized_keys"), ("root", "/root/.ssh/authorized_keys"))
                                    if os.path.exists(p)}}


def containers():
    ids = run(["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"]).split()
    if not ids:
        return []
    out = []
    for c in json.loads(run(["docker", "inspect", *ids])):
        cfg, hc, lab = c["Config"], c["HostConfig"], c["Config"].get("Labels") or {}
        env = [e.partition("=") for e in cfg.get("Env") or []]
        out.append({
            "name": c["Name"].lstrip("/"), "service": lab.get("com.docker.compose.service"), "oneoff": lab.get("com.docker.compose.oneoff"),
            "image": scrub(short_image(cfg.get("Image"))),"user": cfg.get("User") or "(image default)", "workdir": cfg.get("WorkingDir"),
            "entrypoint": scrub(cfg.get("Entrypoint")), "cmd": scrub(cfg.get("Cmd")),
            "env_names": sorted(k for k, _, _ in env),
            "env_safe": {k: scrub(v) for k, _, v in env if k in SAFE_ENV or k.endswith("_FILE")},
            "healthcheck": scrub((cfg.get("Healthcheck") or {}).get("Test")),
            "restart": (hc.get("RestartPolicy") or {}).get("Name"), "read_only": hc.get("ReadonlyRootfs"), "privileged": hc.get("Privileged"),
            "cap_drop": hc.get("CapDrop"), "cap_add": hc.get("CapAdd"), "security_opt": hc.get("SecurityOpt"),
            "tmpfs": sorted((hc.get("Tmpfs") or {}).keys()), "memory_mb": (hc.get("Memory") or 0) // (1 << 20),
            "cpus": (hc.get("NanoCpus") or 0) / 1e9, "cpu_shares": hc.get("CpuShares"), "pids_limit": hc.get("PidsLimit"),
            "oom_score_adj": hc.get("OomScoreAdj"), "log": [hc.get("LogConfig", {}).get("Type"), hc.get("LogConfig", {}).get("Config")],
            "ports": scrub(hc.get("PortBindings")), "network_mode": hc.get("NetworkMode"),
            "networks": sorted((c.get("NetworkSettings") or {}).get("Networks", {}).keys()),
            "mounts": sorted([{"type": m.get("Type"), "source": short_volume(m.get("Name")) if m.get("Type") == "volume" else scrub(m.get("Source")),
                               "dest": m.get("Destination"), "rw": m.get("RW")} for m in c.get("Mounts") or []], key=lambda m: m["dest"]),
            "state": {"status": c["State"].get("Status"), "health": (c["State"].get("Health") or {}).get("Status"),
                      "started_at": c["State"].get("StartedAt"), "restart_count": c.get("RestartCount"),
                      "oom_killed": c["State"].get("OOMKilled"), "exit_code": c["State"].get("ExitCode")},
            "image_id": (c.get("Image") or "")[:19]})
    return sorted(out, key=lambda r: r["name"])


def networks():
    ids = run(["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]).split()
    if not ids:
        return []
    return sorted([{"name": n["Name"], "driver": n["Driver"], "internal": n["Internal"],
                    "subnet": ",".join(c.get("Subnet", "") for c in (n.get("IPAM") or {}).get("Config") or []),
                    "containers": sorted(v["Name"] for v in (n.get("Containers") or {}).values()),
                    "ips": {v["IPv4Address"].split("/")[0]: v["Name"] for v in (n.get("Containers") or {}).values() if v.get("IPv4Address")}}
                   for n in json.loads(run(["docker", "network", "inspect", *ids]))], key=lambda r: r["name"])


def volumes(conts):
    used = {}
    for c in conts:
        for m in c["mounts"]:
            if m["type"] == "volume":
                used.setdefault(m["source"], []).append(f'{c["name"]}:{m["dest"]}')
    names = run(["docker", "volume", "ls", "-q"]).split()
    info = json.loads(run(["docker", "volume", "inspect", *names])) if names else []
    return sorted([{"name": short_volume(v["Name"]), "anonymous": bool(re.fullmatch(r"[0-9a-f]{64}", v["Name"])),
                    "labels": {k: v2 for k, v2 in (v.get("Labels") or {}).items() if k.startswith("com.docker")},
                    "used_by": sorted(used.get(short_volume(v["Name"]), []))} for v in info], key=lambda r: r["name"])


def units():
    out = []
    root = "/etc/systemd/system"
    for f in sorted(os.listdir(root)):
        if not f.startswith("pa-"):
            continue
        p = os.path.join(root, f)
        keys = [(k.strip(), scrub(v.strip())) for k, _, v in (x.partition("=") for x in open(p).read().splitlines())
                if _ and not k.strip().startswith(("#", ";"))]
        props = "Result,ExecMainStatus,ExecMainExitTimestamp,ActiveState,SubState,LastTriggerUSec,NextElapseUSecRealtime,UnitFileState"
        state = dict(x.partition("=")[::2] for x in run(["systemctl", "show", f, "-p", props]).splitlines() if "=" in x)
        journal = Counter()
        last = ""
        if f.endswith(".service"):
            for line in run(["journalctl", "-u", f, "--since", "7 days ago", "-o", "short-iso", "--no-pager", "-q"], timeout=90).splitlines():
                t = template(line)
                if t:
                    journal[t] += 1
                    last = t
        out.append({"name": f, "sha256": sha(p), "keys": keys, "state": {k: v for k, v in state.items() if v},
                    "journal_7d": top(journal, 12), "journal_last": last})
    return out


def opt_layout():
    data = []
    for f in sorted(os.listdir(DATA)) if os.path.isdir(DATA) else []:
        p = os.path.join(DATA, f)
        st = os.lstat(p)
        size = run(["du", "-sb", p]).split()[0] if stat.S_ISDIR(st.st_mode) else st.st_size
        data.append({"name": scrub(f), "type": "dir" if stat.S_ISDIR(st.st_mode) else "file", "mode": oct(st.st_mode & 0o777),
                     "owner": f"{st.st_uid}:{st.st_gid}", "bytes": int(size) if str(size).isdigit() else None})
    secrets = []
    for f in sorted(os.listdir(SECRETS)) if os.path.isdir(SECRETS) else []:
        st = os.lstat(os.path.join(SECRETS, f))   # name and mode only: the content is never read
        secrets.append({"name": f, "mode": oct(st.st_mode & 0o777), "owner": f"{st.st_uid}:{st.st_gid}"})
    st = os.lstat(SECRETS) if os.path.isdir(SECRETS) else None
    return {"data": data, "secrets": secrets, "secrets_dir_mode": oct(st.st_mode & 0o777) if st else None}


def deployed_tree():
    out = {}
    for root, dirs, files in os.walk(DEPLOY):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".claude", "graphify-out")]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), DEPLOY)
            if rel.startswith("secrets/") and ".dec" in f:
                continue
            out[rel] = sha(os.path.join(root, f))
    return out


def squid(conts, nets):
    """Allowed/denied hosts per zone. A client IP is credited to the container holding it now only for lines logged after
    that container started: compose recreates containers on deploy and Docker hands their IPs out again."""
    ip_name = {ip: n for net in nets for ip, n in net["ips"].items()}
    since = {}
    for c in conts:
        try:
            since[c["name"]] = datetime.strptime(str(c["state"]["started_at"])[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc).timestamp()
        except (KeyError, TypeError, ValueError):
            pass
    when = lambda t: datetime.fromtimestamp(float(t), WIB).isoformat(timespec="minutes") if t else None  # noqa: E731

    def client(ip, ts):
        name = ip_name.get(ip)
        if name is None:
            return "gone (e.g. an ingest-gmail run)"
        return name if float(ts) >= since.get(name, 0) else "earlier holder of a reused IP"
    out = {}
    for c in conts:
        if not (c["service"] or "").startswith("squid-"):
            continue
        conf = run(["docker", "exec", c["name"], "cat", "/etc/squid/squid.conf"])
        allow = sorted({d for line in conf.splitlines() if re.match(r"\s*acl\s+\S+\s+dstdomain\s", line) for d in line.split()[3:]})
        directives = [scrub(x.strip()) for x in conf.splitlines() if x.strip() and not x.strip().startswith("#")]
        allowed, denied, clients, first, last = Counter(), Counter(), Counter(), None, None
        for line in run(["docker", "exec", c["name"], "cat", "/var/log/squid/access.log"], timeout=120).splitlines():
            p = line.split()
            if len(p) < 7:
                continue
            host = re.sub(r":\d+$", "", re.sub(r"^\w+://", "", p[6]).split("/")[0])
            verdict = "denied" if "DENIED" in p[3] or p[3].endswith(("/403", "/407")) else "allowed"
            (denied if verdict == "denied" else allowed)[host] += 1
            clients[f"{client(p[2], p[0])} {verdict} {host}"] += 1
            first = first or p[0]
            last = p[0]
        out[c["service"]] = {"conf_sha256": hashlib.sha256(conf.encode()).hexdigest(), "allow_domains": allow, "directives": directives,
                             "allowed": top(allowed, 30), "denied": top(denied, 30), "by_client": top(clients, 40),
                             "log_first": when(first), "log_last": when(last)}
    return out


def docker_logs(conts):
    out = {}
    for c in conts:
        if c["service"] not in ("vault-tools", "control"):
            continue   # vault's stdout carries the owner's messages; its log files are templated by probe_hermes
        p = subprocess.run(["docker", "logs", "--since", "168h", c["name"]], capture_output=True, text=True, errors="replace", timeout=120)
        cnt = Counter(template(x) for x in (p.stdout + p.stderr).splitlines() if x.strip())
        out[c["service"]] = {"lines_7d": sum(cnt.values()), "templates": top(cnt, 25)}
    return out


def images():
    rows = [json.loads(x) for x in run(["docker", "images", "--format", "{{json .}}"]).splitlines() if x.startswith("{")]
    keep = ("personal-agent", "nousresearch/hermes-agent", "ubuntu/squid")
    return sorted([{"repo": r["Repository"], "tag": r["Tag"], "id": r["ID"], "created": r["CreatedAt"], "size": r["Size"]}
                   for r in rows if r["Repository"].startswith(keep)], key=lambda r: (r["repo"], r["created"]))


conts = containers()
nets = networks()
print(json.dumps({"collected_at": datetime.now(WIB).isoformat(timespec="seconds"),
                  "os": os_info(), "usage": usage(), "listening": listening(), "security": security(), "containers": conts,
                  "networks": nets, "volumes": volumes(conts), "units": units(), "opt": opt_layout(),
                  "deployed_tree": deployed_tree(), "squid": squid(conts, nets), "docker_logs": docker_logs(conts), "images": images()},
                 sort_keys=True))
