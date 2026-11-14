#!/usr/bin/env python3
"""Reads the reports of probe.py and prints what the return from kimiclaw would bring home: counts, hashes compared,
short codes. Nothing in a report is a value of the data except short codes, and those are printed only when probe.py
marked them showable; payee-like values are shortened here once more. Lists are wrapped so that nothing is cut by the
width of ops/privacy/mask.py, which the output is piped through.

Usage: compare.py summary report.json            one host (Tahap A2)
       compare.py diff orig.json kimi.json       what kimi has that orig has not (Tahap A4): the gate of the plan, and
                                                 what needs the owner's eye before the OK for Tahap B
"""
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVENTS_KEY = hashlib.sha256(repr("_events.jsonl").encode()).hexdigest()[:24]   # probe.py's hx() of that name
KIMI_PATHS = ("/opt/vault-tools", "/opt/ingest-gmail", "/root/")
SCANNED = {".", "telegram"}   # the folders card_lines.find_file searches by hash: /ingest and /ingest/telegram


def short(v):
    return re.sub(r"^(les|sekolah)[-_ ].*", r"\1-*", v) if isinstance(v, str) else v


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def wrap(label, items, per=6):
    items = list(items)
    print(f"{label} ({len(items)}):" if items else f"{label}: tidak ada")
    for i in range(0, len(items), per):
        print("    " + ", ".join(str(x) for x in items[i:i + per]))


def code_literals():
    """Every quoted lower-case word in vault-tools' code: a threshold key the old code reads is one of them."""
    out = set()
    for p in (ROOT / "services/vault-tools/vault_tools").glob("*.py"):
        out.update(re.findall(r"""["']([a-z][a-z0-9_]{2,40})["']""", p.read_text(encoding="utf-8")))
    return out


def host_line(r):
    h = r["host"]
    return (f"os {h['os']}, python {h['python']}, sqlite {h['sqlite']}, serialize {'ada' if h['serialize'] else 'TIDAK'}, "
            f"disk bebas {h['disk_free_gb']} GB (terpakai {h['disk_used_pct']}%)")


def db_head(name, d):
    if "error" in d:
        return f"{name}: GAGAL dibaca ({d['error']})"
    if not d.get("exists"):
        return f"{name}: tidak ada"
    side = ", ".join(f"{k} {v['size']} B" for k, v in sorted(d["side"].items())) or "tanpa berkas samping"
    total = sum(t["count"] for t in d["tables"].values())
    return (f"{name}: integrity {','.join(d['integrity'])}, versi {d['user_version']}, skema {d['schema_hash'][:12]}, "
            f"{len(d['tables'])} tabel, {total} baris, uid {d['uid']} mode {d['mode']}, WAL-flag {d['wal_flag']}, {side}")


def summary(path):
    r = load(path)
    print(host_line(r))
    for name, d in r["dbs"].items():
        print(db_head(name, d))
        if d.get("tables"):
            wrap("  baris per tabel", (f"{t} {v['count']}" for t, v in sorted(d["tables"].items())), per=8)
            hits = {f"{t}.{k}": n for t, v in d["tables"].items() for k, n in v["needles"].items()}
            wrap("  teks berisi path", (f"{k} {n}" for k, n in sorted(hits.items())), per=3)
            dups = {t: v["dup_keys"] for t, v in d["tables"].items() if v["dup_keys"]}
            if dups:
                print(f"  kunci ganda: {dups}")
        if d.get("doc_dirs") is not None:
            print(f"  folder di doc_files: {d['doc_dirs']}")
    ing = r.get("ingest")
    if ing:
        ev = ing["events"]
        print(f"folder ingest: {len(ing['files'])} berkas, bukan berkas biasa {ing['others']}, "
              f"folder uid {ing['dir']['uid']} mode {ing['dir']['mode']}")
        wrap("  per folder dan jenis", (f"{k} {v}" for k, v in sorted(ing["tops"].items())), per=4)
        if ev:
            print(f"  _events.jsonl: {ev['lines']} baris, diakhiri baris baru {ev['ends_newline']}, jenis {ev['types']}")
            print(f"  set kunci: {ev['keysets']}")
        owners = collections.Counter(f"{f['uid']}:{f['gid']} {f['mode']}" for f in ing["files"].values())
        print(f"  pemilik dan mode berkas: {dict(owners)}")
    print("unit:")
    for name, u in sorted(r["units"].items()):
        s = u.get("show", {})
        extra = ""
        if name.endswith(".timer"):
            extra = f", terakhir {s.get('LastTriggerUSec') or '-'}, cap {'ada' if u.get('stamp') else 'tidak'}"
        if name.endswith(".service") and s.get("Result"):
            extra = f", hasil {s.get('Result')} status {s.get('ExecMainStatus')}, user {s.get('User') or 'root'}"
        print(f"  {name}: {u['file']} / {u['active']}{extra}")
    print(f"proses yang membuka database: {r['holders'] or 'tidak ada'}")
    if r.get("secret_names") is not None:
        wrap("nama rahasia", (f"{s['name']}{'' if s['size_gt0'] else ' (KOSONG)'}" for s in r["secret_names"]), per=4)
    x = r.get("extras")
    if x:
        print(f"container jalan {x['containers_running']}, semua {x['containers_all']}; applier: disetujui "
              f"{x['applier']['approved']}, menunggu {x['applier']['pending']}")
        for n, s in x["secrets"].items():
            print(f"  rahasia {n}: " + ("tidak ada" if s is None else
                                       f"isi {'ada' if s['size_gt0'] else 'KOSONG'}, mode {s['mode']}, mtime {s['mtime']}"))
        for n in ("vault.env", "front.env"):
            s = x.get(n)
            print(f"  {n}: " + ("tidak ada" if s is None else f"mode {s['mode']}, mtime {s['mtime']}"))
    for k in ("listing", "command_files", "cron"):
        if r.get(k) is not None:
            items = r[k].items() if isinstance(r[k], dict) else enumerate(r[k])
            print(f"{k}:")
            for key, val in items:
                print(f"    {key}: {json.dumps(val, ensure_ascii=False)[:600]}")
    if "root_crontab_lines" in r:
        print(f"baris crontab root: {r['root_crontab_lines']}")


def repo_code():
    out = {}
    for base in ("services/vault-tools", "services/ingest-gmail"):
        for p in (ROOT / base).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and "tests" not in p.parts:
                out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()[:32]
    return out


def code_compare(kimi_code):
    repo = repo_code()
    used, rows = set(), []
    for root, files in (kimi_code or {}).items():
        if files is None:
            rows.append((root, "-", "folder tidak ada"))
            continue
        for rel, f in sorted(files.items()):
            parts = rel.split("/")
            match = None
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                cands = [p for p in repo if p == suffix or p.endswith("/" + suffix)]
                if len(cands) == 1:
                    match = cands[0]
                    break
            if match is None:
                rows.append((root, rel, "baru (tidak ada di repo)"))
            else:
                used.add(match)
                rows.append((root, rel, "sama dengan repo" if repo[match] == f["sha"] else f"BEDA dari {match}"))
    missing = sorted(p for p in repo if p not in used and p.endswith(".py"))
    return rows, missing


def diff(orig_path, kimi_path):
    o, k = load(orig_path), load(kimi_path)
    gate, attn = [], []
    literals = code_literals()
    print("kimi: " + host_line(k))
    print("orig: " + host_line(o))
    for name in ("ledger", "ingest"):
        od, kd = o["dbs"].get(name, {}), k["dbs"].get(name, {})
        print(f"== {name}")
        print("  orig " + db_head(name, od))
        print("  kimi " + db_head(name, kd))
        if not (od.get("tables") and kd.get("tables")):
            gate.append(f"{name}: tidak terbaca di salah satu host")
            continue
        if od["integrity"] != ["ok"] or kd["integrity"] != ["ok"]:
            gate.append(f"{name}: integrity tidak ok")
        same_schema = od["schema_hash"] == kd["schema_hash"] and od["user_version"] == kd["user_version"]
        print(f"  skema sama: {same_schema}")
        if not same_schema:
            gate.append(f"{name}: skema beda")
            oo, ko = {tuple(x) for x in od["objects"]}, {tuple(x) for x in kd["objects"]}
            wrap("  objek hanya di kimi", sorted(ko - oo), per=3)
            wrap("  objek hanya di orig", sorted(oo - ko), per=3)
        for t in sorted(set(od["tables"]) | set(kd["tables"])):
            ot, kt = od["tables"].get(t), kd["tables"].get(t)
            if ot is None or kt is None:
                print(f"  {t}: hanya di {'kimi' if ot is None else 'orig'}")
                continue
            okeys, kkeys = set(ot["rows"]), set(kt["rows"])
            added, removed = kkeys - okeys, okeys - kkeys
            changed = {x for x in okeys & kkeys if ot["rows"][x] != kt["rows"][x]}
            if kt["count"] < ot["count"]:
                gate.append(f"{name}.{t}: berkurang {ot['count']} -> {kt['count']}")
            if not (added or removed or changed):
                continue
            print(f"  {t}: orig {ot['count']}, kimi {kt['count']}: tambah {len(added)}, ubah {len(changed)}, "
                  f"hilang {len(removed)}")
            if kt["tags"]:
                for label, keys in (("tambah", added), ("ubah", changed)):
                    if keys:
                        print(f"      {label} per jenis: {dict(collections.Counter(kt['tags'].get(x, '?') for x in keys))}")
            if removed:
                per = dict(collections.Counter(ot["tags"].get(x, "?") for x in removed)) if ot["tags"] else ""
                attn.append(f"{name}.{t}: {len(removed)} baris dari 9 Nov tidak ada lagi di kimi {per}".rstrip())
            if t == "payee_secrets":
                attn.append(f"payee_secrets berubah di kimi (tambah {len(added)}, ubah {len(changed)}, hilang "
                            f"{len(removed)}): nomor yang ditulis di sana harus terbuka dengan kunci VPS lama; "
                            f"buktinya mirror-check di Tahap C1 dan /rincian di B7")
        for t, kt in sorted(kd["tables"].items()):
            ot = od["tables"].get(t)
            if ot is None:
                continue
            for c, kv in sorted(kt["enum"].items()):
                ov = ot["enum"].get(c, {})
                new = {h: v for h, v in kv.items() if h not in ov}
                if not new:
                    continue
                shown = sorted(short(v["v"]) for v in new.values() if v["v"] is not None)
                hidden = sum(1 for v in new.values() if v["v"] is None)
                print(f"  nilai baru {t}.{c}: {len(new)} ({sum(v['n'] for v in new.values())} baris)"
                      + (f", {hidden} tidak ditampilkan" if hidden else ""))
                if shown:
                    wrap("      yang tampil", shown, per=6)
                if t == "thresholds" and c == "key":
                    unread = [v for v in shown if v not in literals]
                    if unread or hidden:
                        attn.append(f"thresholds: {len(unread) + hidden} kunci baru dari kimi tidak dibaca kode lama "
                                    f"({', '.join(unread) or '-'}; {hidden} tidak ditampilkan): datanya ikut pulang, "
                                    f"fitur Kimi di baliknya tidak")
        kh = {f"{t}.{c}": n for t, v in kd["tables"].items() for c, n in v["needles"].items()}
        oh = {f"{t}.{c}": n for t, v in od["tables"].items() for c, n in v["needles"].items()}
        grew = {x: (oh.get(x, 0), n) for x, n in kh.items() if n > oh.get(x, 0)}
        wrap("  teks berisi path yang bertambah (orig, kimi)", (f"{x} {v}" for x, v in sorted(grew.items())), per=2)
        kimi_hits = {x: v for x, v in grew.items() if any(p in x for p in KIMI_PATHS)}
        if kimi_hits:
            gate.append(f"{name}: {sum(v[1] - v[0] for v in kimi_hits.values())} teks berisi path kimiclaw "
                        f"({', '.join(sorted(kimi_hits))}); find_file memulihkan path berkas statement lewat hash di "
                        f"/ingest dan /ingest/telegram, jadi perlu keputusanmu: dibiarkan pulih sendiri atau diganti")
        if kd.get("doc_dirs") is not None:
            print(f"  folder di doc_files: orig {od.get('doc_dirs')}")
            print(f"                       kimi {kd.get('doc_dirs')}")
            far = {d: n for d, n in kd["doc_dirs"].items()
                   if d not in ("/ingest", "/ingest/telegram", "/opt/vault-tools/ingest", "/opt/vault-tools/ingest/telegram")}
            if far:
                attn.append(f"doc_files: berkas di folder yang tidak dicari find_file: {far}")
    oi, ki = o.get("ingest"), k.get("ingest")
    print("== folder ingest")
    if oi and ki:
        of, kf = oi["files"], ki["files"]
        new = set(kf) - set(of)
        same = {x for x in set(kf) & set(of) if kf[x]["sha"] == of[x]["sha"]}
        conflict = {x for x in set(kf) & set(of) if kf[x]["sha"] != of[x]["sha"]}
        only_orig = set(of) - set(kf)
        print(f"  orig {len(of)}, kimi {len(kf)}: baru {len(new)}, sama {len(same)}, nama sama isi beda {len(conflict)}, "
              f"hanya di orig {len(only_orig)}")
        per_folder = collections.Counter(kf[x]["top"] + " " + kf[x]["ext"] for x in new)
        wrap("  yang baru per folder", (f"{f} {n}" for f, n in sorted(per_folder.items())), per=4)
        far = {f: n for f, n in per_folder.items() if f.split(" ")[0] not in SCANNED}
        if far:
            attn.append(f"ingest: berkas baru di folder yang tidak dicari find_file: {far}")
        if only_orig:
            attn.append(f"ingest: {len(only_orig)} berkas hanya ada di VPS lama (tetap di sana)")
        bad = [x for x in conflict if x != EVENTS_KEY]
        if bad:
            gate.append(f"ingest: {len(bad)} berkas bernama sama dengan isi beda")
        oe, ke = oi["events"], ki["events"]
        if oe and ke:
            prefix = ke["line_hashes"][:len(oe["line_hashes"])] == oe["line_hashes"]
            print(f"  _events.jsonl: orig {oe['lines']} baris, kimi {ke['lines']} baris, orig awalan dari kimi: {prefix}")
            print(f"  jenis event kimi {ke['types']}")
            print(f"  set kunci kimi {ke['keysets']}")
            if not prefix:
                gate.append("_events.jsonl: isi orig bukan awalan isi kimi")
        else:
            print(f"  _events.jsonl: orig {'ada' if oe else 'tidak ada'}, kimi {'ada' if ke else 'tidak ada'}")
    else:
        print(f"  orig {'ada' if oi else 'tidak ada'}, kimi {'ada' if ki else 'tidak ada'}")
        gate.append("ingest: folder tidak terbaca")
    print("== kimi: unit, proses, rahasia, menu, cron")
    for name, u in sorted(k["units"].items()):
        s = u.get("show", {})
        extra = (f", user {s.get('User') or 'root'}" if name.endswith(".service")
                 else f", berikutnya {s.get('NextElapseUSecRealtime') or '-'}")
        print(f"  {name}: {u['file']} / {u['active']}{extra}")
    print(f"  proses yang membuka database: {k['holders'] or 'tidak ada'}")
    wrap("  nama rahasia", (s["name"] for s in (k.get("secret_names") or [])), per=4)
    print("  berkas yang mendaftarkan menu:")
    for c in k.get("command_files") or []:
        print(f"    {c}")
    cron = k.get("cron")
    print(f"  job cron OpenClaw: {len(cron) if cron is not None else 'folder tidak ada'}")
    for j in (cron or []):
        if j["hits"]:
            print(f"    {j}")
    print(f"  baris crontab root: {k.get('root_crontab_lines')}")
    for root, rows in (k.get("listing") or {}).items():
        if rows is None:
            print(f"  {root}: tidak ada")
            continue
        wrap(f"  {root}: {len(rows)} berkas; database", (x["name"] for x in rows if ".db" in x["name"]), per=4)
    rows, missing = code_compare(k.get("code"))
    print("== kode di kimi dibanding repo")
    for root, rel, verdict in rows:
        if verdict != "sama dengan repo":
            print(f"  {root}/{rel}: {verdict}")
    print(f"  sama dengan repo: {sum(1 for r in rows if r[2] == 'sama dengan repo')} berkas; "
          f"berkas .py repo yang tidak ada di kimi: {len(missing)}")
    print("== gerbang data (rencana Tahap A)")
    print("  lolos" if not gate else "  TIDAK lolos:")
    for g in gate:
        print(f"  - {g}")
    print("== perlu perhatianmu")
    print("  tidak ada" if not attn else "", end="\n" if not attn else "")
    for a in attn:
        print(f"  - {a}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "summary":
        summary(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
