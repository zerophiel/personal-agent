# Progress and resume point (finance / vault)

Last updated: 2026-10-30. Branch `worktree-m1-skeleton`, draft PR #1. 383 vault-tools tests pass.
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
Owner paid BCA 1.538.834 on 28 Oct from Mandiri (recorded); the living cash he still holds counts toward this payday's living money (since 2026-10-30 stored as the owner's own figure `living_leftover`, see "Leftover living cash as a fact" below; the derived `living_reserve_override` is gone). Effect at the time: Jenius paid in full (6.361.689 + minimum on 10 Nov), HSBC +1.179.205, other cards minimum; card interest next month ~173k instead of ~309k; card balance ~10.6M, cleared ~Jul 2027 (was ~Oct 2027). SPayLater autodebit day 1 (270k x 5, Nov-Mar), car autodebit day 2; salary must land in Mandiri on 30 Oct. The plan's living transfer for this cycle is only the part taken from the salary; real daily cash is the full `living_reserve`.
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
  changed `living_reserve` (7.500.000 -> 7.546.005) the 30 Oct plan #53 said "move 4.940.162", a figure he never had;
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

## Next steps
- Owner: send `/new` once before the 1 Nov payday session (2026-10-30 deploy: `lepas`/`tunai` on `ubah_belanja`, `tunai` on
  `record_expense`, SOUL). The bot now asks where a purchase was paid from when the screenshot does not show it.
- Done 2026-10-30 (session from 10:02 WIB, edit 10:04 WIB): owner sent `/new` and had the bot fix PHO STREET #2440 (Jenius ->
  jago-harian): the bot listed it, asked what was wrong, showed before -> after, waited for "ya", then `ubah_belanja`;
  `change_log` #1 holds only the account and dedupe key change; no warnings; no new transaction rows. The account of an own
  record feeds no plan or living-cost figure (`living.monthly` sums by month and category).
- After the next uploads, check the two live own records merged where they belong: PHO STREET #2440 into the Jago October
  POS row (file under `jago-utama`); Flazz #2438 (Mandiri, `transfer_internal`; #2439 is merged into it) into the Mandiri
  "Transfer BI Fast Ke BCA" -100.000 of 28 Oct, NOT into BCA's "FLAZZ BCA TOPUP" (all 129 Flazz top-ups go through BCA,
  `transport` by rule; that row must stay counted once as transport).
- Owner: on 1 Nov ask for the payday list; the bot asks again on purpose for the leftover living cash just BEFORE the salary (Mandiri usable + daily account); after
  paying, tell the bot (card payments, pot balance, emergency fund balance) and the Mandiri balance shown in the app.
- After the November statements: calibration per `docs/calibration.md` (Google One, Apple, Coway, bot quality, spend).
- Remaining plan: M3 front/control/applier, M4 comms, M2 gate checks (`docs/assumptions.md`).

## Operating notes
- Deploy: `rsync` from the worktree ROOT (never a subfolder: `--delete` wipes the server tree), back up `ledger.db` first, rebuild `vault-tools`, restart `vault`. Owner must `/new` in Telegram after tool or SOUL changes (owner plans to do it once data and system are done).
- Run the vault agent for batches via `hermes chat --oneshot`, ask for status only, and use a Monitor script for progress.
