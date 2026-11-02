# Progress and resume point (finance / vault)

Last updated: 2026-11-02. Branch `worktree-m1-skeleton`, draft PR #1. 663 tests pass (480 in vault-tools).
No secrets or personal amounts are recorded here; the numbers live in the ledger on the VPS.

## Done
- M1 platform and M2 vault deployed; 40 MCP tools; Hermes vault bot uses them (`tools.tool_search.enabled: "off"`).
- Mutations Jan-Oct recorded and verified complete for BCA, Mandiri, Jago (28 files). Categorization ~85-96% for Jan-Aug.
- Categories: `perantara:` (pass-through money), `berhenti:` (ended costs: driver, house installment, Allianz commission), `sekali:` (one-offs: gold sale, Avrist surrender), `bunga`.
- Card statements recorded for all 7 cards (BCA/Jenius/CIMB/Mandiri Jan-Oct, HSBC Feb-Oct, DBS 3, Mega 2). Reconciliation tolerates Rp 3 (cents).
- Card installments (x/y): 10 active, tracked per scanned statement; they count in the roadmap and shrink card capacity. Subscriptions table (active/ended/unsure).
- Owner answers applied: pot for the friend's debt stays 9M/month; salary 42M net, no other income; house/gold proceeds are NOT the owner's (spouse handles them); car installment 5.706.000 incl. admin; Apple One, Spotify, Microsoft, gym (child), Telkomsel are active recurring costs.
- `living_reserve` = Rp 7.546.005 (owner's choice via the bot on 2026-10-28 18:40: September's living cost; first approved
  7.500.000): cash daily living only; median Jan-Sep cash living ~7.4M with the Sep hospital stay marked `sekali:medis`. Card spending is controlled separately by the budgets below.
- Oct BCA mutation CSV recorded (39 rows, reconciled). Jago has no Oct statement (owner barely uses it); Mandiri through 26 Oct.
- Owner-explained names are stored as `category_keywords` in the ledger (teachers -> `wajib:les`), never in the repo.

## Key finding
After fixed costs (11.1M), car (5.7M) and the pot (9M), about 16.2M is left from 42M. Cash living is ~6.7M and card installments ~6.2M, so little room remains for other card spending; the observed card run-rate (median ~20.9M new charges a month, installments included) exceeds it. The balance keeps rolling onto cards unless card spending drops or the pot changes.

## Card spending budgets (owner approved 2026-10-28; update monthly as installments end)
November: kesehatan 500k, makan 200k, game-digital 250k, belanja-online 300k, lain-lain 200k (total 1.45M = the room left after fixed costs, car, pot 9M, cash living, recurring and installments). Room grows: Dec ~2.0M, Jan ~2.3M, Feb-Mar ~2.5M, Apr-Jun ~2.8M, Jul ~4.4M. Also set: listrik 2.3M, internet 540k, transport 1M.
Biggest avoidable costs: game/digital top-ups (PlayStation, Steam, Apple non-One, AWS) and Rp 1.5-2.1M a month of late/overlimit fees and interest. Autodebit or minimum on time on all 7 cards.
Fixed this session: the current bill is the latest by statement date; the same card+statement date is one bill (duplicates from email + Telegram).

## Payday 30 Oct 2026: scenario A (owner approved 2026-10-28)
Owner paid BCA 1.538.834 on 28 Oct from Mandiri (recorded); the living cash the owner still holds counts toward this payday's living money (since 2026-10-30 stored as the owner's own figure `living_leftover`, see "Leftover living cash as a fact" below; the derived `living_reserve_override` is gone). Effect at the time: Jenius paid in full (6.361.689 + minimum on 10 Nov), HSBC +1.179.205, other cards minimum; card interest next month ~173k instead of ~309k; card balance ~10.6M, cleared ~Jul 2027 (was ~Oct 2027). SPayLater autodebit day 1 (270k x 5, Nov-Mar), car autodebit day 2; salary must land in Mandiri on 30 Oct. The plan's living transfer for this cycle is only the part taken from the salary; real daily cash is the full `living_reserve`.
Roadmap now subtracts confirmed subscriptions and grows the card-clearing capacity as installments, the pot and the car end.

## Telegram bot (vault) 2026-10-28
- Owner "/" menu (13 commands) is pushed by the cardguard plugin and self-heals: every 2 min it compares `getMyCommands` with its list and restores it when Hermes overwrote it (Hermes rewrites its stock menu on every restart/reconnect).
- Report commands (/rencana /tagihan /cicilan /anggaran /peta /kondisi /data /bantuan) are rendered by `vault_tools/reports.py` as Telegram HTML (bold headings, bullets, spacing, status emoji, friendly names, no ISO dates) and sent by the plugin in paragraph chunks with a plain-text fallback; no model involved.
- SOUL has answer-style rules (conclusion first, short, no raw tool dumps, no tables) and check-first rules (`ringkasan_data` before asking or recording; one card one alias; `num-xxxx` tokens map to cards by last 4 digits).
- `approvals.destructive_slash_confirm: false` in config.yaml (the bot cannot save settings: config is read-only).
- The vault bot token was rotated on 2026-10-28 after an accidental print in a tool error; scripts must never print URLs that carry the token.
- After any change to tools, SOUL, plugin or config the owner needs one `/new` and the vault container must be restarted (compose `restart`, or `up -d --force-recreate` when the env file changed).

## Bot calibration from the owner's real chat (2026-10-28)
Findings and fixes: the bot invented its own totals ("defisit 23 juta") -> `simulasi_skenario` (code-computed what-if: pot deferral, extra money now, savings, new card spending) and three labelled numbers in SOUL; it said "no simulation tool" three times -> simulator; it refused changes silently -> `catat_usulan` + `/usulan` (the bot cannot modify its own tools by design: prompt-injection risk; a human builds approved requests); it answered bare "1"/"ya" with the previous answer again -> SOUL rule; it said "alat" and mixed Anda/kamu -> "kamu", no tool jargon; it scanned documents in chat -> read guard (3 re-reads per 30 min). Owner preferences now in SOUL: health costs are covered by the employer, children's school/lessons untouchable, Claude Max kept on purpose, card use nearly stopped for 2 months.
Facts from the chat now in the ledger: Coway schedule (400k to Jan 2027, 270k to Jun 2027, two 270k to Aug 2028, recorded flat at 1.21M), Anthropic Max 1.95M/month active, Netflix 186k kept, Google One ~309k, Catchplay/GoPro/AWS/Steam/PlayStation ended. Active subscriptions 6.25M/month. SUPERSEDED: the "-3.1M/month" capacity and the rising card balance (~44.8M) were a double count (the open statements already held that month's instalments and subscriptions); see Recalibration v2.

## Pot = goal with a deadline (2026-10-28)
The friend's debt is a single transfer of Rp 135M on 31 Jan 2028; the pot deposits are flexible. `sinking_funds.low_amount/low_until` hold an optional low phase; `tools.pot_schedule` spreads the rest evenly afterwards so the target is still met; plan, roadmap (capacity steps) and simulator (`setoran_pot_awal`, `setoran_pot_awal_bulan`) all use it; bot tool `atur_jadwal_pot` saves it after the owner agrees. Real-data comparison (16 cycles, no new card spending, Coway flat 1.21M): even 9M -> card balance ~40M in Jan 2028, interest ~12.6M; 5M until Jun 2027 then ~15M -> ~32.8M, ~5.3M interest (best of those tried); 3M or 0M early clears the cards by ~May 2027 but the catch-up (18-22.5M/month) pushes balances back up. SUPERSEDED by Recalibration v2 (these numbers carried the double count).

## Notion
Snapshot pages created 2026-10-28 (private): `Agent` > `Finance` (Rencana gajian, Tagihan kartu, Cicilan kartu dan langganan, Peta jalan bebas utang, Anggaran dan batas) and `Agent` > `General` (empty). Written from the ledger summaries by Claude Code through the Notion connector; no card/account numbers.
AUTOMATED since 2026-10-28: `vault_tools/notion_sync.py` (no LLM) rewrites the five Finance sub-pages from the ledger every day at 06:30 WIB (`pa-notion.timer` -> `docker exec ... python -m vault_tools.notion_sync`). Token in the `notion_token` docker secret (vault-tools), page id in `/opt/personal-agent-data/vault-tools/notion.json`, egress via squid-vault (api.notion.com). New blocks are appended first, then the old ones are archived; child pages are never deleted. Run by hand: `ssh ... sudo docker exec personal-agent-vault-tools-1 python -m vault_tools.notion_sync`.
Card payment targets: Mandiri via app menu; BCA, HSBC, CIMB, Mega, DBS transfer to the card number; Jenius transfer to the owner's Jenius account. The owner registers numbers in the vault bot (card number as a plain message, `/rekening` for the Jenius account); `link_card_payees` then fills `cards.pay_to_alias` by last 4 digits. A leftover test payee `num-1111` exists from the early spike (not deleted automatically).
Card budgets are `kartu:<category>` (count only rows paid by a card, via `record_expense card_alias`); cash budgets (listrik, internet, transport) count account payments.

## Recalibration v2 (2026-10-28; owner: accuracy first, effort high approved)
- Simulator is statement-based (cycle 1 pays the open statements; later cycles = carry + interest + that statement month's
  instalments and subscriptions + card spending beyond the living money). Roadmap, `sinking_status` and the payday plan use it.
- Payday window: asked within 7 days after payday (the owner pays everything on the 1st) the plan is for the salary just
  received (`current_payday`). The living reserve now protects the pot and the emergency fund too (a pot can never squeeze it).
- Pot pattern `sisa` (cards first, pot takes the rest), set on `hutang-teman` (owner asked for small-first, growing deposits and
  never being squeezed). Real data: cards clean after the Dec 2026 bill, card interest ~23k total (even 9M: ~7.2M interest,
  cards at ~33M). Projection on 31 Jan 2028: 121.437.703, short 13.562.297; counting the 31 Jan 2028 salary (Monday, the due
  date itself; `due_payday`, NOT set: owner's decision): 133.539.315, short 1.460.685. Card spending beyond the living money
  is the big risk (+1M/month -> short 27.6M).
- Emergency fund: `emergency_target` 3M, `emergency_monthly` 500k, `emergency_saved` set only via `dana_darurat(saldo)`.
- New tools: `periksa_data` (+ `/periksa`; also feeds "Data:" warnings into the payday plan), `saldo_pot`, `dana_darurat`,
  `sisa_uang_harian` (this payday only), `atur_jadwal_pot(pola, pakai_gaji_hari_tenggat)`, `upsert_subscription(berakhir, wajib)`,
  `simulasi_skenario(pola_pot, gaji_hari_tenggat)`.
- Data: Coway split per contract with end months (coway-cs 400k to 2027-01, unit-1 270k to 2027-06, unit-2 540k to 2028-08);
  `rockstar-gym` marked `essential` (Gracia's gym). Card lines: 63/63 statements `cocok` after the re-read; instalments matched by
  exact amount (IPREG 152.097, MID*Tokopedia 378.922), M-BCA credits are payments, purchases credited back are netted (Aug 2026:
  22.26M).
- Bot: `reasoning_effort: high`, vision and compression on claude-sonnet-5-5 (titles stay Haiku). Evidence: 197 replies / 256 tool
  calls on 27-28 Oct, 1 tool error (vision on a PDF), 2 "answer first, check later" slips; all 63 model-recorded statement totals
  reconcile with the code-read lines. Spend: Telegram 3.4-6 USD/day on the two setup days; calibration one-shots cost more than that.
  Hermes shows `cost_status: unknown` for Sonnet 5.5: the USD 45 vault limit must be checked in the Console.
- Owner rules (SOUL): children's needs never proposed as cuts; games are the owner's own spending; apps asked per app.
- Calibration is manual on request: `docs/calibration.md` + `ops/calibration/` (no scheduler, by the owner's choice).
- Verified live: payday-list one-shot (numbers exact, asked for leftover living cash, ran the audit, recorded nothing) and a
  receipt-image one-shot (Sonnet vision read Rp 125.000 correctly).

## Accuracy layers (2026-10-28, owner: "akurasi 99,99%, tidak boleh salah hitung")
- Self-checks (`vault_tools/invariants.py`) run inside every payday plan and simulation: transfers + cash kept = salary, whole
  positive rupiah, nothing above a bill, paid + unfunded = bill, living money never used for saving-type items, card books balance,
  pots within target. A violation raises CalculationError: the numbers are refused, never shown.
- Property tests: 200 random ledgers in the suite; a one-off stress run of 3000 found 0 violations. The property test found one real
  bug first: an overdue card's balance above the minimum outranked the living money (fixed: only the minimum is urgent).
- Number guard (cardguard plugin hooks `pre_llm_call`, `post_tool_call`, `transform_llm_output`): every 'Rp ...' in the bot's answer
  must match a tool result or the owner's own words in that session, else a visible 'Cek angka' warning is appended. Live test:
  tool numbers pass with no warning; asked for a sum, the bot refused to calculate (SOUL).
- Duplicate expenses: same date + amount + source account/card is a duplicate whatever the merchant text (a re-sent Flazz
  screenshot was stored twice after /new; corrected in the ledger, nothing deleted). Transfers to own accounts are not spending.
- Owner decided on 2026-10-28 (via the bot) to count the 31 Jan 2028 salary: `due_payday=1`; projection 133.539.315, short 1.460.685.

## Leftover living cash as a fact; subscription notes kept (2026-10-30)
- Bug: `sisa_uang_harian` stored a derived top-up (`living_reserve_override` = living money - leftover). When the owner later
  changed `living_reserve` (7.500.000 -> 7.546.005) the 30 Oct plan #53 said "move 4.940.162", a figure the owner never had;
  following it would have left Mandiri 46.005 short of the auto-debits (SPayLater 1 Nov + car 2 Nov + 100.000 the bank holds).
- Fix: the owner's figure is stored (`living_leftover`, `_payday`, `_at`; blocked in `set_threshold`); the salary part
  (`living_reserve` - leftover) is computed when the plan is made; invariant: salary part + leftover = living money, amount to
  move = the owner's figure. A leftover above a month of living money is refused (the salary was counted in);
  `jumlah_lain` adds the daily account, summed by code. The living reminder and `/rincian` say how much each auto-debit account
  must keep. SOUL: the living money is read from `ringkasan_data` (UANG HARIAN SEBULAN), never a remembered number; on the 1st
  the leftover just before the salary is always confirmed again.
- Bug: right after a context compaction (three in 6 minutes, 28 Oct 18:51-18:57) the bot rewrote subscription notes it no
  longer remembered; `upsert` replaced note/end even when not given and cut notes at 120 characters. Fix: an empty field keeps
  what is stored, "" clears, notes up to 300 characters (longer is refused, not cut); SOUL: stored notes come from the owner.
- Data (backup `ledger.db.bak-pre-leftover-fix`): leftover 4.894.157 (Mandiri, usable, reported 28 Oct) for payday
  2026-10-30, override keys removed; notes of apple-one, microsoft, domain-squarespace, squarespace-workspace and coway-cs
  restored from the bot's own 18:51 output, the "rencana pindah ke Jenius" marker kept. Plan #54: 2.651.848 from the salary to
  the daily account, move 4.894.157, transfers 39.348.152 + cash 2.651.848 = 42.000.000; Mandiri ends at exactly 6.076.000;
  unfunded DBS 696.020 (+46.005) and CIMB 1.631.853; pot projection 132.732.499, short 2.267.501 (sisa pattern, due-date
  salary counted).

## The bot's three /usulan, built (2026-10-30, schema v12)
- #3 correct what the owner recorded: `daftar_belanja` (ids, source, merged/twin flags), `ubah_belanja`, `hapus_belanja`. Only
  `receipt`/`manual` rows not merged; the stored amount must be named back (`jumlah_tercatat`, guards a wrong id); an edit
  re-keys `dedupe_key` by id so a later record of the old values cannot hit the unique index; the whole row before/after goes to
  `change_log` with the owner's reason (subscription upserts are logged there too). Bank mutations and statement lines are fixed
  by uploading again. A merged row can point at an earlier owner record (the 28 Oct Flazz screenshot sent twice), not only a
  mutation. PHO STREET #2440 (Jenius -> Jago daily) was then fixed by the owner through the bot (change_log #1).
- #2 `belanja_kartu(kartu=, bulan=)`: every line of one card's latest (or given) statement with its line status, long numbers
  masked, plus that card's per-cycle summary. One-shot check on CIMB answered from the tool exactly (total 1.717.741, minimum
  85.888, due 5 Nov; subscriptions 1.676.161 of which GoPro 1.186.072; no writes).
- #1 `saldo_rekening`: the balance shown in the bank app (gross) is stored in `balance_reports` and checked by code against the
  auto-debits from that account until the next salary plus what the bank holds back; a debit due that day gives both figures
  (live: Mandiri 6.076.000 = CUKUP lebih 0; on 1 Nov 6.076.000 not yet debited / 5.806.000 after SPayLater). The payday plan
  repeats the verdict for a balance reported since this payday; `ringkasan_data` shows the last report with its WIB time.
  SOUL payday step 5: ask it AFTER the transfers; it is not the pre-salary leftover of step 1.
- `/usulan` shows `feature_requests.resolution`; #1-#3 marked `selesai` with what to say to the bot. Pot shortfall choices no
  longer offer the due-day salary once it is counted. Backup `ledger.db.bak-pre-usulan`; plan for 30 Oct unchanged to the rupiah.

## Own records merge only into a debit of their own bank (2026-10-30, owner: "ya betulkan")
- Found while checking the PHO STREET fix: `merge_receipt_into_mutation` merged the nearest own record of the same amount
  within 2 days into a debit of ANY account, card purchases included, and the debit took the record's category (a
  `transfer_internal` record could drop a real expense out of the living cost). Live: 3 own records, 1 merge, none wrong.
- Now `health.merge_receipts`: the same bank, not the same account, because the Jago statement (`jago-utama`) is one file
  for every pocket (Danu Pocket, Main Pocket, Internet, IPL...), so `jago-harian` purchases show up there; bank names are
  compared case-insensitively ('Jago'/'jago'). A record without a source still matches any bank; a card purchase never; a
  purchase never merges with a move between own accounts (the Jago file is full of round pocket moves) nor the other way
  round. Matched once the whole file is stored, closest dates first, exact account before same bank before no source, one
  record per debit. `ubah_belanja` matches the corrected record again (a wrong bank fixed later is not left counted twice);
  its change_log row then shows `merged_into`.
- 368 tests (8 new, 7 of them fail on the old code). Dry run on a ledger copy: BCA -100.000 on 28 Oct leaves Flazz #2438
  alone; Jago -156.541 on 29 Oct (jago-utama) absorbs PHO STREET #2440; Mandiri -100.000 on 28 Oct absorbs #2438; the fresh
  30 Oct plan is identical (cash 2.651.848, leftover 4.894.157, invariants clean; only the pot warning text that Deploy B
  already changed differs from #54). Backup `ledger.db.bak-pre-merge-fix`; vault-tools rebuilt, vault restarted; no tool,
  SOUL or schema change, so no `/new`; from the vault, MCP `tools/list` returns the 53 tools of `MCP_TOOL_NAMES`.

## Records made after their statement, and re-sent screenshots (2026-10-30, owner: "ya betulkan juga")
- `record_expense` now matches the new record at once (`merge_receipts(receipt_id=...)`), but only against a bank whose
  stored statements (`mutation_files` period) already reach the record's day: before that its own row is not in yet and the
  2-day window would hand it to another payment of the same size, so it waits for that upload. `ubah_belanja` re-matches
  under the same gate. The bot gets the merge in `alerts` (relayed as is): the row and the category that counts, plus
  `merged_into`.
- The duplicate check includes merged records (`existing_id` = the oldest; the message says what it was merged with).
  Before, the screenshot of a merged purchase sent again was stored a second time (a corrected record's key is id-based)
  or hit `UNIQUE constraint failed: transactions.dedupe_key`; `allow_duplicate` after a merged or deleted twin hit it too.
  The key now takes the next free number.
- A merge no longer overwrites the status of a row that already has a category (a rule's `verified` row turned `unverified`).
- 374 tests (6 new, 5 red on the old code; the sixth guards the gate). Dry run on a ledger copy: #2440 merged on a synthetic
  Jago row, its screenshot re-sent -> `possible_duplicate` #2440 and no new row; `allow_duplicate` -> stored, unmerged; a
  Mandiri 800.000 record of 27 Oct left alone although a 26 Oct row of that size exists (Mandiri reaches 26 Oct); a record
  for BCA's 25 Oct FLAZZ 200.000 merged at once (October total +0, the row stays `transport`/`verified`); plan identical.
  Backup `ledger.db.bak-pre-record-merge`; vault-tools rebuilt, vault restarted; MCP `tools/list` 53 tools with the
  `record_expense` description unchanged; ledger counts unchanged; no `/new`.

## Merged records corrected, deleted or let go; cash never merges (2026-10-30, owner: "ya betulkan dua-duanya")
- `ubah_belanja` and `hapus_belanja` accept a record merged into a bank row (before: refused, so a wrong match stayed until
  a human fixed the row). A corrected record goes back into the row it came from while it is still that money (same amount,
  bank and kind; no coverage gate, since an upload merges without one), else it is matched afresh under the gate. A
  category the owner names there becomes the counted row's too, so the bot does not ask twice.
- `lepas=true` (the owner: the record is not that row): it counts on its own and never merges into that row again, by the
  row's dedupe key, so recording the statement again does not hand it back. A screenshot sent twice (a record merged into
  a record) is deleted or let go, not edited.
- A row that took a record's category gets it back when the record leaves, unless it was changed since. `change_log` holds
  these as `ubah` rows told apart by a key in `after_json` (`catatan` given, `kembali` given back, `bukan` refused): the
  action column is CHECKed to baru/ubah/hapus. A replaced upload marks each removed row that held a record, because the
  last ids are used again (`INTEGER PRIMARY KEY` without AUTOINCREMENT).
- A record with no account and no card is cash and never merges (before: it could take any bank's debit of that size).
  `record_expense` requires exactly one of `account_alias`, `card_alias`, `tunai=true`; the bot asks when unsure (SOUL).
  `daftar_belanja` names the bank row a merged record is in, and says "tunai" for cash.
- 383 tests (9 new; every new and changed one fails on the old code, the id-reuse one also without the replace mark). Dry
  run on in-memory copies of the live ledger: no receipts without a source and no `manual` rows; twin #2439: edit refused
  with guidance, delete allowed (#2438 still counts, October total +0), `lepas` makes it count (+100.000, transport budget
  warning); #2440 merges into a synthetic Jago row, an owner category moves to that row, `lepas` gives the row its
  category back and a later edit keeps it out; a cash record on a free BCA debit of the same size and day stays separate
  while a BCA record merges; plan identical (2.651.848 / 4.894.157, invariants clean). Backup `ledger.db.bak-pre-unmerge`;
  vault-tools rebuilt, vault restarted; MCP `tools/list` 53 tools, `ubah_belanja` with `lepas`/`tunai`, `record_expense`
  with `tunai`; counts unchanged; logs clean. Tool fields and SOUL changed, so the owner sends `/new` once.
- Same day, 45dfc1e: ids are used again on the record side too, so a `bukan` mark or a category given by a record deleted
  since no longer applies to the new record that gets its id (a record let go and then deleted kept the next one out of
  that row, counted twice). 384 tests; the new one fails without either half. Dry run on live copies clean; backup
  `ledger.db.bak-pre-unmerge-2`; redeployed with the same checks; no further `/new`.

## A payday's plan comes from the ledger before that payday; payments are progress (2026-10-30, owner: "PERBAIKI SEKARANG JUGA")
- After the owner paid everything on the 30 Oct payday, plans #57-#61 treated the paid salary as still free (pot deposit
  19-20.7M for November), `/rincian` and the simulation counted the paid cards again, `tunda_pot` did nothing to a `sisa`
  pot, a card whose minimum was paid was still "due", and the bot asked the same questions again after three compactions.
- Schema v13: `card_payments`, `debt_payments`, `plan_progress`, `fund_reports` date every payment and reported balance;
  v12 data is backfilled once (`paid_at` trimmed to its date; the open bill and the current emergency balance dated on the
  deploy day).
- A payday's plan, `/rincian`, `/rencana`, the simulation and the pot projection use the ledger as it stood BEFORE that
  payday; what was paid since is progress (done, paid outside the plan, still open), never free money. Reminders and card
  status use the current state. Plans are stored only when the JSON changes.
- New tools: `cicilan_dibayar` (an instalment paid by hand ahead of its auto-debit: tenor and outstanding go down, the
  auto-debit leaves the reminder), `transfer_selesai`, `status_gajian` (progress plus facts already reported).
- A card whose minimum is paid is never "due" (reminders, audit, `/tagihan`, overview, SOUL). `card_advice` no longer
  offers cutting the living money. `record_card_payment` refuses the same amount twice on one day unless `ulang=true`.
- `tunda_pot`/`pot_awal` also hold back a `sisa` pot; the simulation's first cycle pays every minimum first, like the plan.
- `dana_darurat(saldo)` read on or after a payday says whether that payday's deposit arrived, against the last report
  before it (16:29: 600.048 and 600.000, both read after the deposit, made the bot ask for another 500.000). The latest
  fund report is picked by date, not by id (a report can be backdated).
- SOUL: `status_gajian` first (up to 7 days after a payday, and after every compaction), one question per message, never
  re-ask what is recorded; open items are knowledge, not questions. Hermes compaction at 100K tokens (was 60K) with the
  owner's last 3 messages verbatim; `protect_first_n` stays at Hermes's default (it stops protecting the session opening
  after the first compaction by itself); idle compaction back to Hermes's default (off): set to 1800 s since 27 Oct, it
  would summarise the owner's answers while they step away to make the payday transfers (it never fired 27-30 Oct).
- 401 vault-tools tests (16 new in `test_payday_progress.py`; the first 15 fail on the old code), 479 across all suites.
  Dry runs on in-memory copies of the live ledger (old vs new code). Backup `ledger.db.bak-pre-payday-progress` (v12,
  61 plans, 1.915 transactions); vault-tools rebuilt (v13: 7 card payments, 2 fund reports, dates 2026-10-30); data fix;
  vault restarted; MCP 56 tools, `status_gajian` through the Hermes container; logs clean. Owner sends `/new`.
- Data recorded from the owner's 30 Oct chat: MTF 2 Nov (5.706.000) and SPayLater 1 Nov (270.000) paid by hand on 30 Oct
  (tenor 18 / 4, outstanding 102.613.000 / 1.080.000); transfers done: IPL, les English, les Gracia, both school VAs,
  dana darurat 500.000, uang harian 2.827.889 (the owner sent 2.830.398); les Mandarin 800.000 left in Mandiri (not billed
  yet); emergency fund 100.000 before the payday (report dated 29 Oct) and 600.000 after; office parking Nusapala 150.000
  from Mandiri on 30 Oct 16:53 (#2442, transport: paid monthly since August, a living cost, no fixed expense). /usulan #5,
  #7, #8, #9, #10 `selesai`; #4, #6 `dikerjakan`.
- Plan #62: no auto-debit until 30 Nov; DBS rest 872.061 carried (minimum met, ±15.261 interest); pot hutang-teman
  134.200.046 of 135.000.000 by 31 Jan 2028, short 799.954 (16 paydays: 0, 4.454.039, 5.818.351, 6.108.204, 6.794.623,
  7.164.623, 3 x 7.564.623, 9.433.427, 3 x 11.855.363, 3 x 12.055.607). Before the data fix it showed short 299.954: the
  500.000 deposit was counted twice.

## Daily money is the top-up plus the leftover (2026-10-31, owner: "x + y adalah 7.5 juta, jadi bukan x doang yg dipakai menghitungnya")
- On 31 Oct 22:26 the bot recorded ANKER 249.000 and its system warning said 22% of the daily money was used after 6% of
  the time, Rp 2.186.814 left for 29 days. The spending pace measured against `cash_to_hold`, the 2.827.889 the plan took
  from the salary; the owner's month was that top-up plus the 4.718.116 leftover already held: 7.546.005
  (`living_reserve`). The same salary-only base showed in the plan summary ("jatah harian 91.222") and the `/rencana` footer.
- `payday.living_money(snap)` = `cash_to_hold + living_leftover` of the stored plan, and `living_per_day` over the payday
  window, feed the spending pace (purchase alerts, `health_check`, `/anggaran`), the plan summary, the `/rencana` footer and
  the Notion plan note. The stored `daily_allowance` stays the salary part, so stored plans are not rewritten and
  regenerating plan #62 adds no row. Every month with a reported leftover counts the same way: top-up + leftover =
  `living_reserve`.
- Cash spent from the payday until the first leftover reading on or after it is already out of that figure:
  `set_leftover_living_cash` keeps it (`living_leftover_spent`, protected like the other `living_leftover*` keys) and the
  pace does not count it again. A later figure for the same payday corrects that reading (the bot does not ask twice), so
  the count made then stands; an estimate made before the payday is counted again at the payday reading. Card purchases
  were never in the leftover and still count. On 30 Oct, Warkop Dani 17.000 (#2441, recorded 15:23) came before the 15:27
  reading of 4.718.116.
- Dry run of the new code on an in-memory copy of the live ledger (31 Oct, after ANKER): 624.075 of 7.546.005 used (8%,
  6% of the time), ok, no warning; 6.921.930 left for 29 days (238.687/day); 243.419/day over the window; 62 plans before
  and after regenerating. 407 vault-tools tests (6 new in `test_health.py`), 495 across all suites.
- Deployed 2026-11-01 00:34-00:37 WIB on the owner's "lanjut deploy", the steps of
  `ops/datafix/2026-10-31-pace-fix/deploy.sh` run one by one: bot idle; backup `ledger.db.bak-pre-pace-fix` (integrity ok,
  1.919 transactions, 62 plans); `living_leftover_spent` = 17.000 for payday 20261030 set on the code still deployed (with
  the key missing, the next `sisa_uang_harian` on the new code would take every purchase since the payday as already out
  of the leftover); rsync; vault-tools rebuilt (image 03dbe36a1c9f, healthy); vault restarted when idle; Hermes listed the
  MCP tools again at 00:36:38 (56 vault_tools tools). Live read-only check on 1 Nov: 624.075 of 7.546.005 used (8%, 9% of
  the time), ok, no alert; 6.921.930 left until the 30 Nov payday; 62 plans. Runtime map 00:37: the 157 deployed files
  are identical to the repo. The owner sends `/new` once (the session still holds the 22% warning).

## The daily account's balance corrects the month; no per-day figure (2026-11-01, owner: "saldo poket harian 7051352 buat bot bisa rekoreksi"; "240 sekian perhari kayaknya ga perlu kamu state")
- The daily pocket drifts from the records: the wife's transfers for errands are often bigger than the errands (650.000
  for 600.000 of petrol). On 1 Nov the owner read 7.051.352 where the records said 6.921.930.
- `saldo_rekening` on `jago-harian` (`health.LIVING_ACCOUNT`) anchors the month: `living_balance_report` (the
  balance_reports row) and `living_balance_mark` (the last transaction id at that moment), both system keys. What is left
  = the balance minus card purchases since the payday (daily money, not out of the account yet) minus what was spent
  after the reading (dated later, or dated that day and recorded after it, unless the row is a bank row that took in a
  receipt recorded before the reading). What left any account before the reading day is in the balance or was daily
  money held elsewhere, whenever its row comes in: the 30 Oct parking 150.000 was paid from the Mandiri leftover, bank rows
  come in weeks later, and Jago files every pocket under `jago-utama`. The pace shows the difference with the records as
  a correction (more money: added to the month; less: counted as spent). A newer reading replaces the last; a reading
  from another payday window is ignored; a reading before the payday's top-up is marked done is kept but not used.
- `sisa_uang_harian` is refused once the payday's top-up (`uang-harian`) is in `plan_progress`: the balance then holds the
  top-up too, and taken as the leftover it would make the month 2.827.889 + 7.051.352 instead of 7.546.005.
- No per-day figure anywhere (`/rencana` footer, `/anggaran`, the plan summary, alerts) and no "padahal baru N% waktu
  berlalu" warning: the daily money also pays electricity, phone and water, so it is not spent evenly; a 2.300.000
  electricity bill early in the month would always look like overspending. The 80% and over-100% alerts stay.
  `living_per_day` is gone; the stored `daily_allowance` is never shown.
- `ringkasan_data` carries UANG HARIAN BULAN INI (spent, of, %, left until the payday, and the reading it follows), so
  the bot answers "sisa uang harian berapa" from the code. SOUL: the current daily-account balance goes to
  `saldo_rekening`, never to `sisa_uang_harian`; never state the daily money per day.
- Commits e5d494c, 60ae046, the deploy scripts in `ops/datafix/2026-11-01-pocket-balance/`. 414 vault-tools tests (7 new
  in `test_health.py`), 502 across all suites. Dry run on a copy of the live ledger: as below, 62 plans before and after.
- Deployed 2026-11-01 01:22-01:24 WIB under the owner's delegation (until 1 Nov 09:00 WIB: "langsung memperbaiki bot tanpa
  butuh persetujuan saya"), the steps of `deploy.sh` run one by one: bot idle; rsync; vault-tools rebuilt (healthy); backup
  `ledger.db.bak-pre-pocket-balance` (integrity ok, 1.919 transactions, 62 plans); the reading stored with
  `record_account_balance` on the new code (report 5, mark 2445); vault restarted when idle; Hermes listed the tools again
  at 01:24:08 and Telegram connected at 01:24:20. Live read-only check: 7.051.352 left until the 30 Nov payday (records
  6.921.930, +129.422), 624.075 of 7.675.427 used (8%), ok, no alert; VERIFIED. The owner sends `/new` once.

## Numbers the bot worked out itself now come from the code (2026-11-01 recalibration, owner: "check ulang bot apakah sudah sesuai, apakah ada yg salah hitung")
- The code's figures reconcile: the 63 statements re-read `cocok`; `periksa_data` 0 problems and 3 INFO (google-one
  309.000 recorded vs 2.691.822 charged, apple-one 319.000 vs 810.000, coway 1.210.000 vs 2.190.000 in cycle 2026-10;
  open question 4); plan #62 by hand (DBS rest 872.061 carried at 15.261 a month, CIMB 85.888 + 1.631.853 = 1.717.741
  closed outside the plan, pot hutang-teman 799.954 short, only les-mandarin-manuel 800.000 still open); the month's
  624.075 is rows #2441-#2445 less the 17.000 spent before the leftover reading.
- Each of the four replies the number guard flagged ("⚠️ Cek angka") had a number the model made or restated itself:
  - 30 Oct 15:27, "Rp 2.504.914 belum terdanai di dua kartu": its own sum of a card rest carried with interest (DBS
    872.061) and one already closed outside the plan (CIMB 1.631.853), and 1.000 off (the sum is 2.503.914).
    `status_gajian` and the plan summary now end the unfunded list with a JUMLAH line (two or more items): what has no
    money, what is carried with interest, how many are closed.
  - 30 Oct 16:08, Rp 193.913: the model's own 293.913 - 100.000 (the Mandiri balance less what the bank holds).
    `saldo_rekening` now says "Yang bisa dipakai", and the broken "Tidak ada autodebet ...; ditambah saldo minimum"
    sentence is gone. In the payday days it names the salary transfers not marked done and what is left (or KURANG) if
    they are paid from that account, both figures when an auto-debit is due that day; transfers paid into the account
    itself (a payee with its bank and last digits: dana-darurat is jago-darurat) are left out; without a stored plan for
    the payday, the old general caveat.
  - 31 Oct 20:20 (twice), Rp 174.075, the YONNY receipt: `record_expense` returned no amount, so the bot confirmed with
    its own reading of the photo. It now returns `recorded` ("#id merchant Rp amount, date, source, kategori ...") and
    SOUL says to confirm with that. The guard also missed the amount in the gateway's photo description, which writes
    amounts the English way (174,075): those are now remembered as seen.
- SOUL: never add up or subtract; the JUMLAH line and `saldo_rekening` carry the figures; a figure no tool gave is said
  to be missing, not worked out.
- Commits a473d4d, a7e0947, the deploy scripts in `ops/datafix/2026-11-01-recal/`. 417 vault-tools tests, 506 across all
  suites. Dry run on a copy of the live ledger: 62 plans before and after.
- Deployed 2026-11-01 01:51-01:53 WIB under the owner's delegation, the steps of `deploy.sh` one by one: bot idle; backup
  `ledger.db.bak-pre-recal` (integrity ok, schema 13, 1.919 transactions, 62 plans, 5 balance reports); rsync; vault-tools
  rebuilt (healthy); vault restarted when idle; SOUL.md and the cardguard plugin in the container hash the same as the
  repo; Telegram connected (polling) at 01:53:28 and Hermes listed the tools again. Live read-only check on an in-memory
  copy: VERIFIED (JUMLAH with DBS 872.061 carried and 1 item closed; Mandiri 293.913 gives 193.913 usable and KURANG
  606.087 if les Mandarin 800.000 is paid from it; `recorded` from the stored row). The daily money is unchanged:
  7.051.352 left, 624.075 of 7.675.427 (8%).

## Control bot and front agent (M3, 2026-11-01, owner: "danoe control bot dan danoe front agent itu fungsinya buat apa ya? ... Kalau belum implementasikan juga setelah ini ya"; built under the delegation until 09:00 WIB)
- What they are for: `@danoecontrol_bot` is the owner's approval desk and has no LLM. An agent never changes itself;
  it asks, and the owner taps Setujui or Tolak once. `@danoefront_agent` is the general assistant on the open web
  (questions, search with sources, drafts); finance stays with `@danoevault_agent`.
- Control v2, live since 02:08 WIB (redeployed 02:15 with the link-safe inbox read; commits 0e4e730, 9b7a355): it reads
  `proposals-inbox`, re-validates every file (the seven fields, zone, change type, the files each type may write, length
  caps), posts a plain-text card with one-time buttons, and records the tap in `control-state` (`control.db`,
  `decided/`, `approved/`). `/status`, `/usulan`, `/ping`. Nothing was applied then: the applier was not built
  (installed since 23:23 WIB, section "M3 installed" below).
- Test proposal #1 ("UJI pemasangan control", 02:09 WIB) is posted and waits for the owner's Tolak tap; afterwards
  `decided/1.json` must exist and the buttons are gone. It was accepted under the first rules (a config change without
  files); the current rules would refuse it. (The owner tapped Setujui; the applier skipped it at its install.)
- change-proposals (b0fa065): front's one MCP tool `submit`, which writes a proposal into the inbox and nothing else (five
  waiting, ten per 24 hours). Its token is generated on the VPS and the image is built and smoke-tested offline; it runs
  only with front.
- Front (1ed7105): Hermes on Haiku 5.5 with web search, `clarify`, `vision_analyze`, memory (each write waits for the
  owner's OK) and `submit`; terminal, code, files, browser, skills, delegation and cron are off. Web search needs no key
  (free tiers of Exa, Parallel, Keenable or Firecrawl through squid-front, so search text leaves the VPS). Checked on
  the VPS with dummy credentials and no network: `hermes doctor` reports no deprecated or stale key (only the missing
  API key), and `gateway run` with front's caps, process and memory limits stays up as uid 10000 (26 processes,
  240 MiB) and stops cleanly. Also off: x_search (it turns itself on when xAI credentials exist) and the background
  memory review every 10 turns (`nudge_interval: 0`); photos go to the model as images (`image_input_mode: native`).
- Groups (getMe, 02:40 WIB): `@danoevault_agent` and `@danoecontrol_bot` can still be added to a group (BotFather
  "Allow Groups" was never turned off). The vault was never in one (all 66 sessions are DMs) and control drops
  non-private chats in code. Both Hermes configs now set `allowed_chats: "none"`, which drops every group and leaves
  DMs alone (a throwaway container with v0.22.5: private kept, group and supergroup dropped; the live config before
  the change let both through). The vault restarted with it at 02:46 WIB while idle: Telegram polling again after
  37 s, config and SOUL hashes equal to the repo's. The owner turns Allow Groups off for both bots.
- Front needed `telegram_front_token` and `anthropic_front_key` from the owner (set 09:08 and 09:09 WIB). The key comes
  from a separate Anthropic workspace with its own USD 40 limit; with the vault's key front would spend the finance
  bot's budget, so the render script refuses that key. Front runs since 11:34 WIB (section "Front live" below).
- Deferred, with reasons:
  - (built 2026-11-01 without a deploy key or git on the VPS, section "The applier" below; installed 23:23 WIB) The
    applier (writes, commits, deploys and health-checks an approved change): needs a deploy key from the owner, a git
    checkout on the VPS (today an rsync target), a running front and the owner's review at the M3 gate. Contract in
    `docs/SECURITY.md`.
  - (built 2026-11-01, section "Front live" below) A card-number guard for front: vault's cardguard stores numbers in
    vault-tools, which front cannot reach, so front's `cardblock` drops the message instead.
  - Browser, a terminal sandbox, skills and a Sonnet route for hard questions: later, each as a proposal.
- Tests: 530 across all suites; new `tests/test_zones.py` (one network per service, only control mounts the decisions,
  front's mounts and toolsets, groups dropped and no Opus or Fable in any zone).

## Admin fees, bills paid once, undoing an instalment (Deploy 2, 2026-11-01, owner: "lanjut sampai selesai"; "Tunggakan coway 540 sudah lunas dari tanggal 30")
- Admin fees (/usulan #4, the owner's estimates): Rp 7.500 per card payment (a transfer to a card number), Rp 6.500 per other
  transfer; the Mandiri card (bank-app menu) and the auto-debits cost nothing. The plan pays each fee with its payment, once
  per destination, only when something is paid, keeps the living money's fee with the reserve and lists the fees apart:
  transfers + fees + cash = salary (`docs/payday.md`). They count from the 30 Nov payday (`biaya_admin_mulai` 20261130):
  plan #62 (30 Oct), already carried out, keeps its numbers, so the les Mandarin transfer still open this cycle carries a
  fee of about 6.500 that no plan holds. status_gajian, `saldo_rekening`, /rincian, the report and Notion show the code's
  total. The simulation: the plan's fees in cycle 1, then `fee_estimate`, 102.500 a cycle on the live ledger (six fixed
  costs, the pot, the emergency fund and the living money at 6.500; five card payments at 7.500 and Jenius at 6.500).
  Conservative: every card with a bill now counts every month, the emergency fund after its target too.
- The fees moved the projection, not the allocation: plan #63 (30 Oct, the same transfers and cash as #62) says pot
  hutang-teman 132.662.546 of 135.000.000 by 2028-01-31, 2.337.454 short (799.954 before the fees). A 30 Nov preview from
  today's data has 66.000 of fees (the November card bills are not in yet).
- Bills paid once (/usulan #6): `tagihan_sekali` (catat, daftar, lunas, buka, batal), in the plans after the day it was
  recorded (`docs/payday.md`). `transfer_selesai` marks one paid. A bill already paid when mentioned is an expense.
- `cicilan_dibayar batal=true` undoes an instalment recorded by mistake: the debt gets back exactly what that record took
  (from the change log; for a record from before the log, its amount), tenor + 1, and an auto-debit is counted again.
- The vault service has `stop_grace_period: 60s`: Docker's default 10 s killed Hermes mid-drain ("exited UNCLEANLY").
- Data fix (`ops/datafix/2026-11-01-deploy2/`): the three fee keys, `biaya_admin_mulai` first; the Coway arrears of 540.000,
  paid 30 Oct from the Mandiri balance (the owner to the bot, 30 Oct 15:54 and 16:00, and in the Claude Code session on
  1 Nov), recorded as expense #2447 (receipt, mandiri-utama, `sekali:coway-tunggakan` like the 13 Oct rows): it merges into
  its Mandiri row when the October e-statement is stored, if the bank shows one debit of 540.000; usulan #4 and #6
  `selesai`; the plan made again only after a copy showed the allocation unchanged.
- Schema 14 (`one_off_bills`). Commits e0bc2e4, d1c7c46. 573 tests across all suites (460 vault-tools); the 200 random
  ledgers have fees and bills paid once. Dry run on a copy of the live ledger with the new code: the same report as live.
- Deployed 2026-11-01 10:25-10:27 WIB with `deploy.sh`: bot idle; backup `ledger.db.bak-pre-deploy2` (integrity ok,
  schema 13, 1.920 transactions, 62 plans); rsync; compose ok; vault-tools rebuilt (healthy); data fix; vault recreated
  (stop timeout 60); SOUL.md and the cardguard plugin hash as the repo; Hermes listed 57 tools at 10:27:03
  (`tagihan_sekali`, `cicilan_dibayar` with `batal`); no errors in either log. CHECK report OK: plan #63 = #62 in money,
  only les-mandarin-manuel 800.000 open.

## Front live, card numbers dropped, prune fixed (M3, 2026-11-01 11:34 WIB, owner: "Setelah ini semua selesai kamu jangan lupa lanjut ke control bot dan front agent ya")
- `cardblock` (702a114), front's only plugin, mounted read-only: a message whose text holds a Luhn-valid 13-19 digit
  run (photo captions and inlined text documents included) is dropped before dispatch, so neither the model nor
  `state.db` sees it. The owner's message is deleted and a fixed notice sent; anyone else's is dropped silently (Hermes
  runs the hook before its sender check); an error drops the message too. Detection equals vault's cardguard (a parity
  test). Photos of a card, account and VA numbers, PINs and OTPs stay with SOUL.md; Luhn also flags some IMEIs (the
  notice says to send again without the digits). It loads like vault's cardguard (the same capability line;
  `hermes plugins show cardblock`: enabled); the proof on Telegram is the owner's test (next steps).
- Weekly prune: the 1 Nov 03:00 run removed the change-proposals and ingest-gmail images (rebuilt by the front start and
  the 06:00 timer) because `config --images` ran without profiles; the digest-pinned Hermes image, listed as `<none>`,
  was kept only because vault was running. `scripts/prune.sh` now keeps the images of every profile, of running
  containers and of the release manifests, compared by full image ID, and stops before removing anything when compose
  cannot list them. Dry run on the VPS before the start: nothing unused.
- Start (11:33:58-11:34:32 WIB, `--profile front up -d --build --wait change-proposals front`): both healthy; Telegram
  polling through squid-front; 6 tool schemas (web search, web extract, `clarify`, `vision_analyze`, memory, `submit`);
  MCP `change_proposals` registered its one tool; gateway as uid 10000, 293 MiB of 2 GiB. The rendered env file is 0600
  with 10 names, the front token differs from control's and the allowlist is the owner alone; the container's env has
  no vault name. The first-boot warnings equal vault's first boot (config migration skipped; 63 commands over
  Telegram's menu limit of 60).
- One-shot 11:40:55 WIB (9 s, USD 0.0016 estimated; the 9.8K-token system prompt is cached): front called `submit` once,
  control took the file from the inbox and posted card #2 (pending; one file,
  `services/hermes/front/skills/uji-control/SKILL.md`). That proves the front key, squid-front, the MCP token and the
  inbox. Squid-front saw at boot, before any chat, model catalogs (models.dev, openrouter.ai), Nous pages
  (portal.nousresearch.com, hermes-agent.nousresearch.com, nousresearch.github.io) and two DNS-over-HTTPS resolvers
  (Telegram fallback IPs); afterwards only api.telegram.org and api.anthropic.com.
- Test proposal #1 was decided at 10:57:10 WIB with Setujui, not Tolak: `approved/1.json` exists and nothing is applied
  (there is no applier, it has no files, and today's rules refuse it). The applier must never apply #1 or #2
  (`docs/SECURITY.md`).
- Tests: 584 (`make test` now also runs both Hermes plugin suites).

## The applier, built (M3, 2026-11-01 afternoon, owner: "Lanjut sampe selesai"); installed 23:23 WIB
- Control v3 (6648796, deployed 2026-11-01 23:22 WIB): before the card, the diff of each file against the installed
  one, computed by control from read-only mounts of `services/hermes/front/` and `config/squid/` (never the agent's
  text) and stored with the proposal as `review` (the installed files' hashes; shown whole or why not). The card says
  what a tap will do: applied exactly as shown, not applied automatically and why, or that applying is not automatic
  yet. The applier's outcomes are told once and counted in `/status`. A v2 `control.db` migrates in place; a proposal
  from before the migration is never applied.
- Zone rules (bddb5ec), found missing while building the applier, that every front change now passes first: front's
  config may set only listed keys (a `model.base_url` would have sent every chat and the Anthropic key elsewhere while
  `provider` still said anthropic); both profiles Anthropic Haiku or Sonnet only, with no env reference or URL outside
  the MCP entry; every squid conf plain lines only (a `url_rewrite_program` or `include` line would run a program in
  the proxy) and front denying private ranges first.
- The applier (eb73863): `services/applier`, contract in `docs/SECURITY.md`. Front only, exactly the diff the owner
  saw, the zone rules and `squid -k parse` before writing, the old files back on any failed check, outcomes through
  control. Its units and `install.sh` are written, not run. No deploy key: the VPS never writes to GitHub; `make deploy`
  holds the applier and refuses while the VPS has an applied change this checkout lacks, and `make applied-pull` brings
  those in, one commit each (591ca94).
- Checked on the VPS, read-only: python3 3.12.3 with PyYAML 6.0.1 (the zone rules run there), flock, Compose 5.6.1,
  systemd 255; the files inside front and squid-front hash as the host's; in the running squid image a broken
  `http_access` line exits 0 and only prints `aclParseAccessLine`, so the applier reads the output, not the exit code.
- (done 2026-11-01 23:22-23:24 WIB on the owner's "Ya, pasang", open question 17) Deployed and installed, section "M3
  installed" below. Until then Setujui only recorded the approval.
- Tests: 639 across all suites, none skipped (applier 22 with a fake docker; its zone-rule test runs the real
  `tests/test_zones.py` against named mutations of the front files).

## Two overlapping bank files no longer count a row twice (2026-11-01 evening, owner: "Oke saya sudah lakukan yg di vault front control dan botfather sesuai permintaanmu")
- Checked on the VPS, read-only, after the owner's steps: control #2 rejected 12:54 WIB; front's card test at 18:26
  (cardblock dropped the message, deleteMessage ok, no card number in front's `state.db`, the ordinary question at
  18:27 answered); vault `/new` 18:21; the Mandiri October e-statement recorded 18:23 (214 rows = the PDF's 214 dated
  lines, reconciled, Rp 1 of cents); Flazz #2438 merged into the Mandiri BI Fast -100.000 of 28 Oct (#2475), Coway
  #2447 into the -540.000 of 30 Oct (#2505); no tool errors, no "Cek angka". Allow Groups cannot be read without the
  bot tokens: the owner's word.
- Found: of the e-statement's 65 new rows, 17 (#2449-#2465, 5-24 Oct) are rows the 1-26 Oct file already holds, read
  with other wording; the dedupe key holds the normalized description, so they were stored again: -82.847.429 of
  October outflow twice (six card payoffs of 15 Oct among them). Each file balances on its own, so neither the
  reconciliation nor `periksa_data` saw it. The bot suspected it ("sekitar 29 baris yang tidak dikenali sebagai
  duplikat") and told the owner "186,8 juta keluar"; without the 17 it is 103.973.941 (64.930.593 of it still
  uncategorized), unverified 117 -> 100. Nothing was stored from them: no plan, snapshot, fund or payment record after
  the file, and the daily pace counts from the payday only. The other 28 files agree with the ledger (|diff| <= 2).
- Fix (live since 2026-11-01 20:13 WIB, below): `record_mutations` first lets every exact key claim its stored row,
  then lets a row left over take a stored row of another file of the account with the same day and amount, the most
  similar wording first, each once; a row the earlier file lacks stays new (`matched_by_date_amount` in the result).
  It also warns BUKU TIDAK COCOK when the account's rows over the file's period no longer add up to its balance change
  (`ledger_gap`), and `periksa_data` reports the same as a MASALAH (audit rule 8). Not matched still: a row the second
  document dates on another day; inside the overlap the ledger check flags it. Tests 644 (5 new).
- Data fix `ops/datafix/2026-11-01-mandiri-dupes`: a backup, the 17 rows removed by id after checks (still the
  e-statement's, uncategorized, nothing merged into them, a same-day same-amount row each in the 1-26 Oct file, both
  files agreeing with the ledger afterwards), each logged whole in `change_log`, the file's `new_rows` 65 -> 48.
  Dry run on an in-memory copy of the live ledger: gaps 0 and -1, audit mutation findings 2 -> 0 with the other three
  findings unchanged; the new code re-recording the e-statement's 65 rows stores 48 and matches 17.
- Found with it: vault's cardguard owner check (e9c1bc4, 14:54 WIB) never reached the VPS. The plugin there hashes
  to a473d4d's, so the earlier note in Next steps that it "loads at the next vault restart" (corrected there) was
  wrong: a restart alone would have reloaded the old one. A content dry run of the whole repo against the VPS: besides
  M3 (control v3, the applier, compose, scripts) and docs, only this fix and cardguard with its test differ.
- `deploy.sh` syncs two folders onto their twins: `services/vault-tools` (rebuilt) and `services/hermes/vault` (only
  cardguard and its test differ). Then it restarts the vault when idle, which loads cardguard and reconnects Hermes
  to the new tool server, and checks that the plugin in the container is the repo's. Pre-checked read-only in the
  vault container with the new module: the allowlist holds exactly the owner, `_is_owner` is true for the owner's
  DM only (not a group, not another id), card detection unchanged. Control stays v2, nothing of M3 ships.
- Deployed on the owner's "Gas", 2026-11-01 20:12:34-20:13:29 WIB: the bot idle (last message 18:25); vault-tools
  rebuilt and healthy; backup `ledger.db.bak-pre-mandiri-dupes` (1987 transactions); the 17 rows removed (gaps 0 and
  -1, 18 `change_log` rows, the file's rows and new_rows 48); the vault restarted 20:13:22 WIB. Then, read-only: 0 of
  30 mutation files off the ledger; October 253 rows, income 44.795.915, expenses 103.973.941, net -59.178.026,
  uncategorized 64.930.593, unverified 100; audit 0 bad, 0 warn, 3 info, no mutation finding; the cardguard in the
  container is the repo's, agent.log says "cardguard: command menu restored" and has no empty-allowlist line; MCP 57
  tools; no error since the restart. The tools need no `/new`, but the vault session still holds the 186,8 juta reply,
  so the owner sends `/new` once. Live-bot snapshot 20:16 WIB: only the M3 gate's files differ (Makefile, compose,
  data-dirs, control v3, the applier, tests).

## A card's repayment is its bill, never a move between own accounts (2026-11-01 night, found checking October's categories; owner: "Lanjuttt")
- Owner `/new` to vault 22:17:48 WIB (session_reset; no error since the 20:13 restart), then October's categorizing
  with the bot. Read-only before it: October's 105 unverified rows sit in 89 keys, each key one wording; no transfer
  to a card number among them.
- Found: from 52e70ac (2026-10-28) `suggest.groups` counted the owner's cards among the own accounts (`own_last4`
  held `cards.last4`), so a BI Fast transfer to an own card's number was suggested `transfer_internal`, and
  `apply_suggestions` stored it so: four September repayments, cimb-9888 -147.268, dbs-5685 -1.215.273, hsbc-5915
  -1.951.647, mega-5855 -2.274.554, together 5.588.742, are missing from September's cashflow expenses. A card's
  spending reaches the bank cashflow only as its repayment, and `health_check` reads that cashflow. Their four stored
  rules would have verified every later payment to those cards the same way on import, and the owner-name branch
  would also have read a card transfer carrying the cardholder's name as an own move. Unaffected: living cost and the
  daily pace leave out both `wajib:` and `transfer_internal`; DSR comes from the debts and statements. Jago's "Main
  Pocket Interest" (August 8.136, September 5.603) and its tax (-1.627, -1.120) were `transfer_internal` rules too:
  the pocket-move pattern matches "main pocket".
- Fix (tests 647, 3 new): `mutations.card_paid` names the card when the text carries its number (`****NNNN`, or a
  long number ending in its last4) and its bank's name; without the bank's name a third party's account with the
  same four digits is not a card. Suggestions: after the fee check, money out to an own card is `wajib:kartu`, also
  in the owner's name (money in from a card gets no suggestion); "pocket interest" is `bunga` before the pocket-move
  check; `own_last4` holds the accounts only. Guard: `set_category` and `set_category_rule` refuse
  `transfer_internal` for an own card's payment ("ini pembayaran kartu ..., pakai kategori 'wajib:kartu'"),
  `set_category_keyword` skips those rows and says how many, `apply_suggestions` skips a refused group and names it,
  a keyword never overrides the card check, and on import a stored `transfer_internal` rule leaves such a row
  unverified. `set_category`'s docstring names `wajib:kartu` for card payments; no SOUL change, so no `/new`.
- Data fix `ops/datafix/2026-11-01-card-internal`: a backup (`ledger.db.bak-pre-card-internal`), then the four card
  rules and rows -> `wajib:kartu`, the two pocket rules and four rows -> `bunga` / `biaya-bank`, each logged in
  `change_log` (14 rows). It stops when the rules found are not those four cards and two pocket keys, when September
  does not hold one row per card, when a card row has no such rule, or when a receipt is merged into a row. Dry run
  with the new code on an in-memory copy of the live ledger: August income +8.136, expenses +1.627; September income
  +5.603, expenses 41.029.662 -> 46.619.524 (+5.588.742 cards, +1.120 tax); October unchanged; living cost August
  4.771.710 -> 4.773.337, September 7.546.005 -> 7.547.125 (the tax; `living_reserve` stays the owner's 7.546.005);
  of the 411 uncategorized groups (643 rows, all months) no suggestion changes; the four fixed rules refuse
  `transfer_internal`; no own-move rule left whose key also holds a card repayment; the audit is the same before and
  after (0 bad, 0 warn, 3 info); no account shares its last four digits with a card. Through the MCP server the
  refusal reaches the bot as the tool's error text, as `set_threshold`'s does. A content dry run against the VPS:
  only the four vault-tools files differ.
- `deploy.sh`: checkout clean and pushed, the idle check, `services/vault-tools` synced onto its twin and rebuilt, the
  fix, the vault restarted when idle, `verify.py`. Deployed on the owner's "Gas sekarang", 2026-11-01 23:12:14-23:13:18
  WIB: the bot idle (last message 18:25); vault-tools rebuilt and healthy; backup `ledger.db.bak-pre-card-internal`
  (1970 transactions, integrity ok); the six rules and eight rows changed (14 `change_log` rows); the vault restarted
  23:12:57. Then, read-only: no own-move rule or row paying an own card, no main-pocket interest left as an own move;
  no mutation file off the ledger; September income 45.928.296, expenses 46.619.524, living cost 7.547.125 (unverified
  52); August 34.834.455, 79.177.797, 4.773.337; October unchanged (unverified 100); audit 0 bad, 0 warn, 3 info. The
  gateway connected to Telegram, cardguard restored its command menu, MCP 57 tools; no error, traceback or recovered
  turn since. No `/new`.

## M3 installed: control v3 and the applier (2026-11-01 23:22-23:25 WIB, owner: "Ya, pasang")
- Before: vault idle (its last message 18:25 WIB); ledger backup `/data/ledger.db.bak-pre-m3` (SQLite API, integrity
  ok, 1970 transactions). Checked first: the compose diff is control's entry only (`CONTROL_REPO_DIR`,
  `APPLIER_OUTCOME_DIR`, the read-only mounts of `services/hermes/front/`, `config/squid/` and `applier/outcome`); what
  change-proposals imports from `control.py` (`PATHS`, `TEXT_LIMITS`, `validate` with `path_allowed`, the size limits)
  is the same in the server's copy and in v3, so its 11:34 image stays right; front and change-proposals are in the
  `front` profile, which `make deploy` leaves alone.
- `make deploy` (23:22 WIB): deploy-guard start and end (no hold left), timers, data folders (`applier/` root 0700,
  `applier/outcome/` root 0755); images control and vault-tools rebuilt, both recreated 23:22:18 and healthy.
  vault-tools rebuilt only because the rsync carries local `__pycache__` files (open question 21). The vault restarted
  while idle at 23:23:13 and exited cleanly ("Previous gateway exited cleanly"): Telegram connected, cardguard's menu
  restored, MCP 57 tools.
- `sudo bash services/applier/install.sh` (23:23:38 WIB): the eight host checks ok (control.db read-only with the
  review column, `approved/` a folder, regular files, `tests/test_zones.py` on the installed tree, front and
  squid-front running, `squid -k parse` on front.conf, front's Telegram state, root's state folders); the install time
  recorded (`outcome/applier.json`); `pa-applier.path` and `pa-applier.timer` enabled and active; the first run logged
  "#1 skipped". `applied/` and `failed/` are empty; the 23:25 timer run finished without error.
- Control v3 after: `control.db` migrated in place (columns `review` and `diff`); #1 approved (skipped by the applier)
  and #2 rejected, neither with a review, so neither can ever be applied; 0 invalid, nothing reported yet; mounts
  `/repo/services/hermes/front`, `/repo/config/squid` and `/outcome` read-only; no restart, no error; squid-ctl logged 9
  Telegram tunnels (200) in its first minutes. Front, change-proposals and the four proxies untouched (front up since
  11:34 WIB).
- From now on a Setujui on a front change applies exactly the diff above the card (front's `config.yaml` and
  `SOUL.md`, `config/squid/front.conf`); everything else stays human-built. When `make deploy` refuses with "applied
  on the VPS but not in this checkout": `make applied-pull`, push, deploy again (`docs/RUNBOOK.md`, Applier). After an
  applied change to front's `config.yaml` or `SOUL.md`: `/new` to `@danoefront_agent`.

## The 30 Nov payday rehearsed; the plan in force is no longer the newest stored row (2026-11-02 night, owner: "Mulai dari sekarang sampai besok pagi jam 10 saya berikan kamu ijin otoritas penuh, jadi kerjakan project ini, semua keputusan saya percayakan ke kamu")
- Rehearsal of the first payday with admin fees (`biaya_admin_mulai` 20261130) on copies of the live ledger with the
  deployed code (same hash as the repo), the /rincian numbers from a stub vault: (A) the ledger as it is, planned on
  30 Nov; (A2) A after a reported leftover; (B) the 30 Oct plan as the bot makes it today, without and with fees;
  (C) each card's latest bill repeated a month later. All four: transfers + fees + cash kept = salary, `plan_errors`
  empty, one fee per destination (a card's minimum and rest together), none for the auto-debits and the bank-app
  menu, the living money's fee kept with it. B without fees equals the stored 30 Oct plan; with fees only the last
  card's rest shrinks, by the fees, and the cash kept stays the living money. C shows the BCA bill due 28 Nov
  (Saturday), before the 30 Nov payday, like 28 Oct: its minimum comes from the balance on hand.
- Found (latent since the bot went live): three readers took the newest row of `plans` as the plan in force:
  `spending_pace` (daily money and the purchase alerts), `_living_balance` (a daily-account balance correcting the
  month) and `_open_transfers` (the auto-debit check of a reported balance). Any plan for another payday stored later
  hid the plan in force: a plan asked for a coming payday (row 41, for 30 Nov, was one), and every plan call from 7
  days after a payday, when `current_payday` turns to the coming one (`PAYDAY_LOOKBACK_DAYS`). `pa-notion.timer` plans
  daily at 06:30 WIB, so on 7 Nov the daily money would have gone silent until 30 Nov ("Belum ada rencana gajian yang
  berjalan" on a balance reading). The writer is right (one row per payday per change); only the readers change.
- Fixed (d597836): `plan_in_force(conn, today)` is the latest payday's plan on or before today, `stored_plan(conn,
  payday)` one payday's newest. `spending_pace` and `_living_balance` read the plan in force, and only while today is
  before its next payday; `_open_transfers` reads the plan of `current_payday(today)`. On a copy of the live ledger:
  the 2 Nov pace is the same before and after a 30 Nov plan is stored, 7 and 10 Nov keep the 30 Oct plan, and 30 Nov
  reads its own. Live since 2 Nov 01:23 WIB (section "Deployed 2 Nov 01:23 WIB" below).

## Payday transfers wait for their category before they count as daily money (2026-11-02 night, decided under the owner's delegation; reversible)
- Found on 2 Nov: the 30 Oct payday's transfers and fees out of the salary account, uploaded on 1 Nov without
  categories (October's categorizing is still to come), counted as day-to-day spending. The month read as almost all
  spent: 'watch' at 89% in `ringkasan_data`, `health_check`, `/anggaran` (a large "selisih saldo") and every purchase
  alert. The figure left was right only because the daily account's reading anchors it. Matching such rows to plan
  items cannot work: each card's two items are paid as one transfer, and several rows differ from the plan by a fee.
- Rule (`UNSORTED_ELSEWHERE`, health.py, commit a7db18b): a `mutation` row with no category, on an account of another
  bank than `LIVING_ACCOUNT`'s, with no receipt merged into it, waits for its category and is reported, not counted.
  A row of any Jago account still counts (Jago files every pocket under one account), and without a daily account
  every row counts, as before. Once categorized, a row counts as spending or stays out as an obligation.
- Where it shows: "BELUM DIHITUNG: N mutasi keluar ..." in `ringkasan_data`, "belum dihitung: ..." in `/anggaran`, an
  info finding in `health_check`.
- Live since 2 Nov 01:23 WIB. The read-only live check with the deployed code shows 30% used ('ok'), the same figure
  left, and 23 rows waiting for a category. To undo: drop the fragment from `_spent_by_category` and `_by_balance`.

## transfer_selesai asks which payday's plan from a week after a payday (2026-11-02 night, under the owner's delegation)
- Found with the rehearsal: from `PAYDAY_LOOKBACK_DAYS` after a payday, `transfer_selesai` marked the coming payday's
  plan. A transfer of the month marked late (the lesson fee of the 30 Oct plan, not paid yet on 2 Nov) would have been
  marked in the 30 Nov plan, and `semua=true` would have marked all of the 30 Nov plan weeks before its salary.
- Rule (commit eeec197): from then on two plans are open, the month's (`plan_in_force`) and the coming one. A
  destination open in both (marked in both, for undo) is asked for: the tool names both paydays and due dates, and the
  bot repeats with `gajian`. A destination open in one plan only goes there; a one-off bill is one bill in both.
  `semua=true` without `gajian` is the month's plan; when nothing is open there, the answer says how to mark the
  coming one. In a payday's week nothing changes.
- On a copy of the live ledger, simulated 8 Nov: the lesson fee is asked for, `gajian='2026-10-30'` marks it in the 30
  Oct plan, `semua=true` marks only that, and the 30 Nov plan stays unmarked. Live since 2 Nov 01:23 WIB; the MCP
  catalog shows `gajian`.
- Owner: `/new` to the vault bot once (a new tool parameter; sent on the morning of 2 Nov). The lesson fee of the 30
  Oct plan is not paid yet: the owner set the money aside (2 Nov morning; this section first said it was paid on 30
  Oct, which was wrong), and the ledger keeps it open. The money sits outside the daily account `jago-harian` (the
  owner, 2 Nov ~10:30 WIB), so the daily money needs no correction. When it is paid, tell the bot: up to 6 Nov it
  marks the 30 Oct plan without asking (`current_payday` keeps a payday for 7 days); from 7 Nov it asks, answer
  "gajian 30 Oktober".

## Deployed 2 Nov 01:23 WIB: the plan in force, the daily-money pace, transfer_selesai, q21 (under the owner's delegation)
- Backup `ledger.db.bak-pre-plan-in-force` (01:22, integrity ok). Both bots idle (the vault's last log line was the
  23:23 restart).
- `make deploy`: vault-tools rebuilt and recreated at 01:23; control rebuilt from cache (its tag gets a new image id on
  every build; the running container keeps its image); vault and front untouched (front's profile is not in `up`). The
  30 deployed `vault_tools` files equal the repo, and the image has no Python caches.
- q21's one-time part: `make deploy` does not build the `jobs` profile and `pa-ingest.service` runs without `--build`,
  so the ingest-gmail image was rebuilt by hand (`--profile jobs build ingest-gmail`, 01:23, no caches inside). rsync
  `--delete` keeps excluded paths, so the 19 `__pycache__` folders from earlier syncs were removed from
  /opt/personal-agent once.
- `restart vault` at 01:24 while idle: exited cleanly, Telegram connected, 57 MCP tools, 59 schemas, no error since.
  Hermes sends its shutdown notice to the owner's Telegram on every restart.
- Read-only live check with the deployed code: plan in force 2026-10-30, pace 30% used ('ok'), 23 rows waiting for a
  category. `make runtime-map` after it (commit e41db72).

## Renewing the Gmail token never leaves the VPS without one (2026-11-02 morning)
- The control bot's warning at 08:00 WIB: the gmail.readonly token (Testing mode, 7 days), minted 27 Oct 13:23 WIB,
  runs out on 3 Nov around 13:20 WIB. The 3 Nov 06:00 ingest still has it; the 4 Nov 06:00 one would not.
- The documented renewal piped gmail-auth.py into `cat > gmail_ingest_token`, which empties the old token as soon as
  ssh starts, before the login. A login that failed or was cancelled left ingest without a token, and
  docs/GMAIL_OAUTH.md even said to delete the old file first. Run alone, gmail-auth.py printed the token.
- `scripts/gmail-renew.sh` (laptop): the new token goes to a temporary file on the VPS and is checked (JSON with a
  refresh token and its issue date). Only then does it rewrite the old file in place; the inode stays, because compose
  mounts the file as a secret. Otherwise the old token stays. gmail-auth.py now refuses a terminal as stdout.
- Tests: tests/test_gmail_renew.py with a fake python and ssh. On the VPS, once against a fake token in /tmp: a
  cancelled login kept the old token, a finished one rewrote it with the same inode; the folder was removed.
- The pa-gmail-token messages name the new script from the next deploy.
- First real renewal, 2 Nov 10:28 WIB (the owner, on the laptop): on the VPS the token file was rewritten at 10:28:53,
  is not empty, and no temporary file is left (`test -s` and `stat` only, the token never read), so the new token
  passed the script's check. The 3 Nov 06:00 ingest is the first to use it with Google. It runs out on 9 Nov around
  10:28 WIB; the 08:00 check stays silent until 8 Nov, when it warns (2 days or less left).

## Open questions for the owner (resume here)
1. (decided 2026-10-28: the 31 Jan 2028 salary counts for the pot)
2. Closing the pot gap without the children's needs: games (owner's own), apps not marked `wajib`, or talking to the friend.
3. Mark each app `wajib` or cuttable: Anthropic Max (kept on purpose), Google One, Apple One, Netflix, Spotify, Microsoft 365,
   Squarespace workspace + domain (email), Telkomsel.
4. Google One Oct 2.69M (owner: downgraded to ~300k from next month) and Coway on Mega (760k x2 + 400k in Oct vs 1.21M recorded):
   check on the November statements (the audit flags them again if they repeat).
5. MID*Tokopedia 204.071 every month on HSBC: an instalment that is not recorded yet?
6. Listrik and internet as fixed expenses (due day, how paid); sender allowlist (CIMB collections address) only with the owner.
7. CIMB Oct statement: GoPro Rp 1.186.072 (USD 65.16) took the card's subscriptions from 524.089 to 1.676.161. Annual charge,
   or something to stop/move? Owner decides.
8. (fixed 2026-10-30: own records merge only into a debit of their own bank, see above)
9. (fixed 2026-10-30: a record made after its statement merges at once; a re-sent screenshot of a merged purchase is flagged)
10. (fixed 2026-10-30: merged records can be corrected, deleted or let go with `lepas`; cash records never merge; see above)
11. (answered 2026-11-01: the Coway arrears of 540.000 were paid 30 Oct from the Mandiri balance; expense #2447, Deploy 2)
12. The bot told the owner 'Jago "fixed-expenses" …9703' was registered: it is not (`accounts` has the alias, `payee_secrets`
    has no number for it). Only if the bot should name it as a destination: `/rekening fixed-expenses Jago <nomor>`. The
    owner pasted that account's full number in the chat on 30 Oct 16:02; it is in Hermes `state.db`.
13. MTF outstanding 102.613.000 is 95.000 below 18 x 5.706.000: check the remaining amount in the MTF app.
14. `payee_secrets` holds a card entry ending 1111 that no card uses (likely an early cardguard test): remove with the owner.
15. Transport over its October budget (1.420.000 of 1.000.000 with the parking): raise the budget or keep it as a warning.
16. (done 2026-11-01: front runs since 11:34 WIB with the `cardblock` guard, section "Front live" above)
17. (done 2026-11-01 23:24 WIB on the owner's "Ya, pasang" at ~23:10 WIB, after the card fix: control v3 and the
    applier are live, section "M3 installed" above) The M3 gate: install the applier (section "The applier" above,
    contract in `docs/SECURITY.md`)? Yes means `make deploy` (control's diff and mounts, the data folders) and then
    `sudo bash services/applier/install.sh` on the VPS (`docs/RUNBOOK.md`, Applier). From then on a Setujui on a front
    change applies it.
18. M4 comms, nothing built (the repo holds net-comms and squid-comms, which allows Anthropic and the Google APIs):
    - What it may do: read and label mail, write drafts, or also send; calendar read only, or create events too.
      Google has no scope for drafts without sending (`gmail.modify` and `gmail.compose` both send), so the broker
      that holds the token, not the scope, keeps comms from sending: it offers only the operations the owner picks.
    - Google consent on the owner's laptop, like the ingest token: a new OAuth client with `gmail.modify`
      (`docs/GMAIL_OAUTH.md`), plus `calendar.readonly` or `calendar.events` if calendar is wanted. In Testing mode
      this refresh token also expires every 7 days.
    - Its own bot: BotFather (Allow Groups off), then `make secret-set NAME=telegram_comms_token`.
    - Which Anthropic key pays its USD 10: a third workspace with its own limit, as front has.
    - card-bus (the Kanban replacement in `docs/ARCHITECTURE.md`, for one zone to hand work to another): still wanted?
19. (done 2026-11-01 20:13 WIB: the 17 doubled Mandiri rows removed and the overlap matching live, with vault's
    cardguard owner check; section "Two overlapping bank files" above)
20. (done 2026-11-01 23:13 WIB on the owner's "Gas sekarang": the card-repayment fix is live; section "A card's
    repayment is its bill" above)
21. (done 2026-11-02 01:23 WIB, decided under the owner's delegation: `--exclude __pycache__` in the rsync, a
    `.dockerignore` for vault-tools and ingest-gmail, `tests/test_deploy.py`; the deploy rebuilt both images once and
    removed the 19 stale folders on the VPS, section "Deployed 2 Nov 01:23 WIB" above) `make deploy` shipped local
    `__pycache__` folders, so after any local test run a deploy rebuilt and recreated vault-tools.
22. `health_check` says WASPADA because the salary account's balance fell two periods in a row. Its period-end
    closings depend on how much of the salary was still there when each bank file ends, and the payday empties it by
    design (October's closing comes after the 30 Oct transfers). Keep the warning, compare balances just before each
    payday, or leave the salary account out of the trend? A manual calibration for the owner; nothing changed.

## Next steps
- (done 2 Nov morning) Owner `/new` to vault after the 2 Nov 01:23 WIB deploy (`transfer_selesai` has `gajian`). The
  30 Oct lesson fee is not paid yet, its money set aside outside the daily account (no correction): tell the bot once
  it is paid. October's categorizing goes on; each categorized payday row leaves "belum dihitung".
- (done 2 Nov 10:28 WIB) Owner: `bash scripts/gmail-renew.sh` on the laptop (see "Renewing the Gmail token" above).
  Next renewal before 9 Nov ~10:28 WIB; the control bot warns on 8 Nov at 08:00.
- (done 2026-11-01 20:13 WIB) The doubled-rows fix. Owner: `/new` once to vault, whose session still holds the 186,8
  juta reply. Bank files over an already recorded period are fine again: same-day same-amount rows match, and BUKU
  TIDAK COCOK flags a row the second file dates otherwise.
- Next: the bot categorizes October with the owner (started after the 22:17 WIB `/new`; 105 rows unverified, 89
  keys: the salary, seven moves to the owner's own accounts in five keys, which count as spending until marked
  `transfer_internal`, the card and instalment payments by VA (`wajib:kartu`), other transfers, fees, interest).
  The card-repayment fix went live before it (23:13 WIB, open question 20), M3 right after (23:24 WIB).
- (done 2026-11-01 18:21 WIB) Owner sent `/new` after the 1 Nov 10:27 deploy (Deploy 2 above).
- (done 2026-11-01, the recalibration section above) The number guard's four flags on 30-31 Oct were the bot's own
  arithmetic or its own reading of a photo. At each calibration, read the replies it flagged since the last one ("Cek
  angka" in Hermes `state.db`): each is a number no tool gave, and the fix is a tool that gives it.
- (done 2026-11-01, Deploy 2) Vault restarts often logged "Previous gateway life exited UNCLEANLY" (8 times up to the
  1 Nov 00:36 restart): the vault service now has `stop_grace_period: 60s`. At the next restarts, check it is gone.
  The 10:27 and 20:13 restarts exited cleanly; the 23:12 one did not (stopped 23:12:57, "no exit path ran", after
  Telegram network errors at 23:01 and 23:04): the bot was idle, nothing to recover, no error since. The 23:23
  restart (M3) exited cleanly again. Keep watching.
- (done 2026-10-31 14:04) Owner sent `/new` after the 30 Oct evening deploy. Still open: les Mandarin once paid
  (`transfer_selesai`; not paid yet on 2 Nov, the money set aside, see "transfer_selesai asks" above). The Mandiri October e-statement was recorded
  on 1 Nov 18:23 WIB (see "Two overlapping bank files" above).
- (done 2026-11-01, Deploy 2 above) Admin fees, bills paid once, the `cicilan_dibayar` undo; the `format_autodebit_check`
  sentence was fixed in the recalibration. Still open: after a week, compare cached tokens per turn and compactions per
  day with the 60K week.
- (done 2026-11-01 18:23 WIB) Coway #2447 merged into its 540.000 debit of 30 Oct (#2505).
- (done 2026-10-30 morning) Owner sent `/new` once before the payday session (deploy: `lepas`/`tunai` on `ubah_belanja`,
  `tunai` on `record_expense`, SOUL). The bot now asks where a purchase was paid from when the screenshot does not show it.
- Done 2026-10-30 (session from 10:02 WIB, edit 10:04 WIB): owner sent `/new` and had the bot fix PHO STREET #2440 (Jenius ->
  jago-harian): the bot listed it, asked what was wrong, showed before -> after, waited for "ya", then `ubah_belanja`;
  `change_log` #1 holds only the account and dedupe key change; no warnings; no new transaction rows. The account of an own
  record feeds no plan or living-cost figure (`living.monthly` sums by month and category).
- After the Jago October e-statement: PHO STREET #2440 must merge into the Jago October POS row (file under
  `jago-utama`). (done 2026-11-01 18:23 WIB) Flazz #2438 (Mandiri, `transfer_internal`; #2439 is merged into it)
  merged into the Mandiri "Transfer BI Fast Ke BCA" -100.000 of 28 Oct (#2475), not into BCA's "FLAZZ BCA TOPUP",
  which stays counted once as transport.
- On the 30 Nov payday: ask the bot for the payday list; it asks for the leftover living cash just BEFORE the salary
  (Mandiri usable + daily account); after paying, tell the bot (card payments, instalments, transfers, pot and emergency
  fund balances, the Mandiri balance in the app). (30 Oct: done in the chat, recorded by the data fix above.)
- After the November statements: calibration per `docs/calibration.md` (Google One, Apple, Coway, bot quality, spend).
- (done 2026-11-01 10:57 WIB, with Setujui) Test proposal #1. (done 12:54 WIB) The owner tapped Tolak on #2, front's
  test of `submit`.
- (done 2026-11-01 18:26 WIB) Front's card test: the public Visa test number (CARD in
  `services/hermes/front/tests/test_cardblock.py`) was dropped and deleted, nothing stored, the next question answered.
- (owner reports done 2026-11-01) BotFather -> Allow Groups off for `@danoevault_agent`, `@danoecontrol_bot` and
  `@danoefront_agent`; not checkable from here without the bot tokens.
- Front follow-ups: (live 2026-11-01 20:13 WIB) vault's cardguard acts only for the owner in a private chat. The
  first TTL sweep that finds an expired `/rincian` message logs how many deletes Telegram accepted (`ttl sweep:
  Telegram deleted N of M`). After a week, front's cost per day from its `state.db` against the USD 40 limit.
- (done 2026-11-01) M2 gate checks: all four closed with evidence (`docs/assumptions.md`).
- Remaining plan: (done 2026-11-01 23:24 WIB) the M3 gate, section "M3 installed" above; next M4 comms once the owner
  has answered open question 18.

## Operating notes
- Deploy: `rsync` from the worktree ROOT (never a subfolder: `--delete` wipes the server tree), back up `ledger.db` first, rebuild `vault-tools`, restart `vault`. Owner must `/new` in Telegram after tool or SOUL changes (owner plans to do it once data and system are done). Since 2026-11-01 23:23 WIB the applier is installed: `make deploy` refuses while the VPS has an applied front change this checkout lacks (`make applied-pull`, push, deploy again).
- `make deploy` never builds the `jobs` profile and `pa-ingest.service` runs without `--build`: after an ingest-gmail
  change, run `--profile jobs build ingest-gmail` on the VPS (as on 2 Nov 01:23 WIB).
- Run the vault agent for batches via `hermes chat --oneshot`, ask for status only, and use a Monitor script for progress.
