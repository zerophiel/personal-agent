#!/usr/bin/env python3
"""Reads the reports of probe.py and prints what the return from kimiclaw would bring home: counts, hashes compared,
short codes. Nothing in a report is a value of the data except short codes, and those are printed only when probe.py
marked them showable; payee-like values are shortened here once more. Lists and long lines are wrapped so that nothing
is cut by the width of ops/privacy/mask.py, which the output is piped through.

Usage: compare.py summary report.json            one host (Tahap A2)
       compare.py diff orig.json kimi.json       what kimi has that orig has not (Tahap A4): the plan's data gate, the
                                                 plan conditions that have a known handling and wait for the owner's
                                                 decision, and what needs the owner's eye before the OK for Tahap B
"""
import collections
import hashlib
import importlib.util
import json
import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
_spec = importlib.util.spec_from_file_location("return_probe", HERE / "probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

KIMI_INGEST = probe.LAYOUTS["kimi"]["ingest_dir"].rstrip("/")
# card_lines.find_file, the only reader of doc_files.path, looks for a missing file by hash in these two folders.
HEALING_DIRS = {"/ingest", "/ingest/telegram"}
KIMI_DIRS = {KIMI_INGEST, KIMI_INGEST + "/telegram"}   # their counterparts on kimi; stage.py brings these files into them
SCANNED = {".", "telegram"}                            # the same two, as the ingest report names a file's folder
FIND_EXT = (".pdf", ".csv", ".txt")                    # and only files with these extensions, directly in them
# Codes the old code switches on. Most are CHECK-bound, so equal schemas already rule out a new one; lines_status and
# processed.status are not. A value that the code of this repo never writes is a stop.
GATE_CODES = {("transactions", "status"), ("transactions", "source"), ("card_lines", "kind"),
              ("statements", "lines_status"), ("accounts", "kind"), ("cards", "pay_method"), ("payee_secrets", "kind"),
              ("debt_payments", "how"), ("subscriptions", "status"), ("feature_requests", "status"),
              ("one_off_bills", "status"), ("one_off_bills", "method"), ("change_log", "action"),
              ("processed", "status")}
# Codes the old code only reads by name or shows: a new one is data that comes home without the feature behind it.
SOFT_CODES = {("thresholds", "key"), ("change_log", "tbl")}
# Columns where the code itself leaves NULL and reads it: a statement whose lines were not read yet (card_lines.py).
NULL_KNOWN = {("statements", "lines_status")}


def hx(v):
    """probe.py's hash of a value (the same function runs on the hosts)"""
    b = v if isinstance(v, bytes) else repr(v).encode("utf-8", "surrogatepass")
    return hashlib.sha256(b).hexdigest()[:24]


EVENTS_KEY = hx("_events.jsonl")
NULL_KEY = hx(None)   # probe.py never shows a NULL; its hash is known all the same


def code_words():
    """hx() of every quoted word in the services' code, tests left out: the codes the code of this repo can write. A word
    quoted anywhere counts, so this is a loose check; for the CHECK-bound columns the equal schemas are the strict one."""
    words = set()
    for p in (ROOT / "services").rglob("*.py"):
        if "tests" not in p.parts and "__pycache__" not in p.parts:
            words.update(re.findall(r"""["']([a-z][a-z0-9_.:-]{1,60})["']""",
                                    p.read_text(encoding="utf-8", errors="replace")))
    return {hx(w) for w in words}


def short(v):
    return re.sub(r"^(les|sekolah)[-_ ].*", r"\1-*", v) if isinstance(v, str) else v


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def wrap(label, items, per=6):
    items = list(items)
    pad = " " * (len(label) - len(label.lstrip()) + 4)
    print(f"{label} ({len(items)}):" if items else f"{label}: tidak ada")
    for i in range(0, len(items), per):
        print(pad + ", ".join(str(x) for x in items[i:i + per]))


def para(text, indent="  - ", more="    "):
    print(textwrap.fill(text, width=150, initial_indent=indent, subsequent_indent=more))


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
                para(f"{key}: {json.dumps(val, ensure_ascii=False)}", "    ", "      ")
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


def tables_diff(name, od, kd, known, gate, attn):
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
        if t == "payee_secrets":
            if added or removed or changed:
                attn.append(f"payee_secrets berubah di kimi (tambah {len(added)}, ubah {len(changed)}, hilang "
                            f"{len(removed)}): nomor yang ditulis di sana harus terbuka dengan kunci VPS lama; buktinya "
                            f"mirror-check di Tahap C1 dan /rincian di B7")
            else:
                print("  payee_secrets: tidak berubah di kimi, jadi tidak ada nomor yang ditulis dengan kunci lain")
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
        if t == "statements":
            lost = sum(1 for x in added | changed
                       if kt["tags"].get(x) == "tanpa-berkas" and ot["tags"].get(x) != "tanpa-berkas")
            if lost:
                attn.append(f"statements: {lost} statement jadi 'tanpa-berkas' di kimi (berkasnya tidak ketemu di sana); "
                            f"kalau berkasnya ada di VPS lama atau ikut pulang, statement itu dibaca ulang setelah pindah")
            unread = sum(1 for x in added if kt["tags"].get(x) == "-")
            if unread:
                attn.append(f"statements: {unread} statement baru di kimi barisnya belum dibaca (lines_status kosong); "
                            f"kode lama menampilkannya sebagai 'baris belum dibaca'")
    for t, kt in sorted(kd["tables"].items()):
        ot = od["tables"].get(t)
        if ot is None:
            continue
        for c, kv in sorted(kt["enum"].items()):
            ov = ot["enum"].get(c, {})
            new = {h: v for h, v in kv.items() if h not in ov}
            if not new:
                continue
            shown = sorted((short(v["v"]) if h != NULL_KEY else "NULL" for h, v in new.items()
                            if v["v"] is not None or h == NULL_KEY), key=str)
            hidden = sum(1 for h, v in new.items() if v["v"] is None and h != NULL_KEY)
            print(f"  nilai baru {t}.{c}: {len(new)} ({sum(v['n'] for v in new.values())} baris)"
                  + (f", {hidden} tidak ditampilkan" if hidden else ""))
            if shown:
                wrap("      yang tampil", shown, per=6)
            unknown = {h: v for h, v in new.items()
                       if h not in known and not (h == NULL_KEY and (t, c) in NULL_KNOWN)}
            if not unknown or (t, c) not in GATE_CODES | SOFT_CODES:
                continue
            u_shown = sorted((short(v["v"]) if h != NULL_KEY else "NULL" for h, v in unknown.items()
                              if v["v"] is not None or h == NULL_KEY), key=str)
            u_hidden = sum(1 for h, v in unknown.items() if v["v"] is None and h != NULL_KEY)
            what = (", ".join(u_shown) or "-") + (f"; {u_hidden} tidak ditampilkan" if u_hidden else "")
            if (t, c) in GATE_CODES:
                gate.append(f"{name}: kode baru di {t}.{c} yang tidak pernah ditulis kode repo: {what}")
            else:
                attn.append(f"{t}.{c}: {len(unknown)} nilai baru yang tidak dikenal kode repo ({what}): datanya ikut "
                            f"pulang, fitur Kimi di baliknya tidak")


def paths_diff(name, od, kd, gate, decide, odd):
    """path needles that grew; for the ledger, the folders doc_files points to. Returns how many doc_files paths point
    into kimi's ingest folder (0 when none)."""
    kh = {f"{t}.{c}": n for t, v in kd["tables"].items() for c, n in v["needles"].items()}
    oh = {f"{t}.{c}": n for t, v in od["tables"].items() for c, n in v["needles"].items()}
    grew = {x: (oh.get(x, 0), n) for x, n in kh.items() if n > oh.get(x, 0)}
    wrap("  teks berisi path yang bertambah (orig, kimi)", (f"{x} {v}" for x, v in sorted(grew.items())), per=2)
    text = sorted(x for x in grew if not x.startswith("doc_files.path|"))
    if text:
        gate.append(f"{name}: path bertambah di kolom teks {', '.join(text)}. Perlu dicek di kode, kolom demi kolom, "
                    f"apakah kolom itu dibuka sebagai berkas; yang sudah dicek baru doc_files.path (lewat find_file).")
    if kd.get("doc_dirs") is None:
        return 0
    print(f"  folder di doc_files: orig {od.get('doc_dirs')}")
    print(f"                       kimi {kd.get('doc_dirs')}")
    on_kimi = {d: n for d, n in kd["doc_dirs"].items() if d in KIMI_DIRS}
    far = {d: n for d, n in kd["doc_dirs"].items()
           if d not in HEALING_DIRS | KIMI_DIRS | set(od.get("doc_dirs") or {})}
    if on_kimi:
        decide.append(f"doc_files: {sum(on_kimi.values())} path menunjuk ke folder ingest kimiclaw {on_kimi}, padahal "
                      f"rencana meminta tidak ada path kimiclaw. Penanganannya ada di kode: find_file, satu-satunya "
                      f"pembaca doc_files.path, tidak menemukan path itu di VPS lama, lalu mencari berkasnya lewat hash, "
                      f"tetapi hanya berkas .pdf, .csv dan .txt yang langsung berada di /ingest dan /ingest/telegram (ke "
                      f"sanalah stage.py membawanya pulang), dan menulis path yang benar. Pilihan: dibiarkan pulih sendiri, "
                      f"atau diganti di salinan staging sebelum dipasang."
                      + (f" Catatan: ada berkas baru berjenis lain di folder itu, {dict(odd)}; kalau doc_files menunjuk "
                         f"ke salah satunya, path-nya tidak pulih sendiri." if odd else ""))
    if far:
        gate.append(f"doc_files: {sum(far.values())} berkas di folder yang tidak ikut pulang dan tidak dicari find_file: "
                    f"{far}")
    return sum(on_kimi.values())


def diff(orig_path, kimi_path):
    o, k = load(orig_path), load(kimi_path)
    gate, decide, attn = [], [], []
    known = code_words()
    oi, ki = o.get("ingest"), k.get("ingest")
    odd = collections.Counter()   # new kimi files in the folders find_file scans, with an extension it does not read
    if oi and ki:
        for x, f in ki["files"].items():
            if x not in oi["files"] and f["top"] in SCANNED and f["ext"] not in FIND_EXT and x != EVENTS_KEY:
                odd[f"{f['top']} {f['ext']}"] += 1
    healing = 0
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
        tables_diff(name, od, kd, known, gate, attn)
        healing += paths_diff(name, od, kd, gate, decide, odd)
    print("== folder ingest")
    if oi and ki:
        of, kf = oi["files"], ki["files"]
        new = set(kf) - set(of)
        same = {x for x in set(kf) & set(of) if kf[x]["sha"] == of[x]["sha"]}
        conflict = {x for x in set(kf) & set(of) if kf[x]["sha"] != of[x]["sha"]}
        only_orig = set(of) - set(kf)
        bad = [x for x in conflict if x != EVENTS_KEY]
        print(f"  orig {len(of)}, kimi {len(kf)}: baru {len(new)}, sama {len(same)}, nama sama isi beda {len(bad)} "
              f"(_events.jsonl tidak dihitung), hanya di orig {len(only_orig)}")
        per_folder = collections.Counter(kf[x]["top"] + " " + kf[x]["ext"] for x in new)
        wrap("  yang baru per folder", (f"{f} {n}" for f, n in sorted(per_folder.items())), per=4)
        far = {f: n for f, n in per_folder.items() if f.split(" ")[0] not in SCANNED}
        if far:
            attn.append(f"ingest: {sum(far.values())} berkas baru di folder yang tidak dicari find_file ({far}): ikut "
                        f"pulang, tetapi bot tidak menemukannya lewat hash")
        if odd and not healing:
            attn.append(f"ingest: berkas baru berjenis yang tidak dibaca find_file {dict(odd)}: ikut pulang; tidak ada "
                        f"path doc_files kimiclaw yang bergantung padanya")
        if only_orig:
            attn.append(f"ingest: {len(only_orig)} berkas hanya ada di VPS lama; tetap di sana")
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
    names = [s["name"] for s in (k.get("secret_names") or [])]
    wrap("  nama rahasia", names, per=4)
    print(f"  vault_tools_key di kimi: {'ada' if 'vault_tools_key' in names else 'tidak ada'}")
    cmds = k.get("command_files") or []
    print("  berkas yang mendaftarkan menu:" + ("" if cmds else " tidak ada"))
    for c in cmds:
        para(json.dumps(c, ensure_ascii=False), "    ", "      ")
    cron = k.get("cron")
    print(f"  job cron OpenClaw: {len(cron) if cron is not None else 'folder tidak ada'}")
    for j in (cron or []):
        if j["hits"]:
            para(json.dumps(j, ensure_ascii=False), "    ", "      ")
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
    verdict = "TIDAK lolos" if gate else ("belum lolos: ada syarat rencana yang tidak terpenuhi, penanganannya menunggu "
                                          "keputusanmu (bagian berikut)" if decide else "lolos")
    print("== gerbang data (rencana Tahap A): " + verdict)
    for g in gate:
        para(g)
    print("== syarat rencana yang punya penanganan, menunggu keputusanmu:" + ("" if decide else " tidak ada"))
    for d in decide:
        para(d)
    print("== perlu perhatianmu:" + ("" if attn else " tidak ada"))
    for a in attn:
        para(a)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "summary":
        summary(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
