# Progress and resume point (finance / vault)

Last updated: 2026-10-28. Branch `worktree-m1-skeleton`, draft PR #1. 221 vault-tools tests pass.
No secrets or personal amounts are recorded here; the numbers live in the ledger on the VPS.

## Done
- M1 platform and M2 vault deployed; 40 MCP tools; Hermes vault bot uses them (`tools.tool_search.enabled: "off"`).
- Mutations Jan-Oct recorded and verified complete for BCA, Mandiri, Jago (28 files). Categorization ~85-96% for Jan-Aug.
- Categories: `perantara:` (pass-through money), `berhenti:` (ended costs: driver, house installment, Allianz commission), `sekali:` (one-offs: gold sale, Avrist surrender), `bunga`.
- Card statements recorded for all 7 cards (BCA/Jenius/CIMB/Mandiri Jan-Oct, HSBC Feb-Oct, DBS 3, Mega 2). Reconciliation tolerates Rp 3 (cents).
- Card installments (x/y): 10 active, tracked per scanned statement; they count in the roadmap and shrink card capacity. Subscriptions table (active/ended/unsure).
- Owner answers applied: pot for the friend's debt stays 9M/month; salary 42M net, no other income; house/gold proceeds are NOT the owner's (spouse handles them); car installment 5.706.000 incl. admin; Apple One, Spotify, Microsoft, gym (child), Telkomsel are active recurring costs.
- `living_reserve` = Rp 7.500.000 (owner approved 2026-10-28): cash daily living only; median Jan-Sep cash living ~7.4M with the Sep hospital stay marked `sekali:medis`. Card spending is controlled separately by the budgets below.
- Oct BCA mutation CSV recorded (39 rows, reconciled). Jago has no Oct statement (owner barely uses it); Mandiri through 26 Oct.
- Owner-explained names are stored as `category_keywords` in the ledger (teachers -> `wajib:les`), never in the repo.

## Key finding
After fixed costs (11.1M), car (5.7M) and the pot (9M), about 16.2M is left from 42M. Cash living is ~6.7M and card installments ~6.2M, so little room remains for other card spending; the observed card run-rate (median ~20.9M new charges a month, installments included) exceeds it. The balance keeps rolling onto cards unless card spending drops or the pot changes.

## Card spending budgets (owner approved 2026-10-28; update monthly as installments end)
November: kesehatan 500k, makan 200k, game-digital 250k, belanja-online 300k, lain-lain 200k (total 1.45M = the room left after fixed costs, car, pot 9M, cash living, recurring and installments). Room grows: Dec ~2.0M, Jan ~2.3M, Feb-Mar ~2.5M, Apr-Jun ~2.8M, Jul ~4.4M. Also set: listrik 2.3M, internet 540k, transport 1M.
Biggest avoidable costs: game/digital top-ups (PlayStation, Steam, Apple non-One, AWS) and Rp 1.5-2.1M a month of late/overlimit fees and interest. Autodebit or minimum on time on all 7 cards.
Fixed this session: the current bill is the latest by statement date; the same card+statement date is one bill (duplicates from email + Telegram).

## Payday 30 Oct 2026: scenario A (owner approved 2026-10-28)
Owner paid BCA 1.538.834 on 28 Oct from Mandiri (recorded) and holds ~5.06M in Mandiri, which counts as part of the 7.5M daily cash. One-off `living_reserve_override` = 2.438.834 until 2026-10-31 (`reserve_for`); from the Nov payday the normal 7.5M applies again by itself. Effect: Jenius paid in full (6.361.689 + minimum on 10 Nov), HSBC +1.179.205, other cards minimum; card interest next month ~173k instead of ~309k; card balance ~10.6M, cleared ~Jul 2027 (was ~Oct 2027). SPayLater autodebit day 1 (270k x 5, Nov-Mar), car autodebit day 2; salary must land in Mandiri on 30 Oct. The plan's "jatah harian" for this cycle shows only the 2.44M part; real daily cash is the full 7.5M.
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
  date itself; `due_payday`, NOT set: owner's decision): 133.539.315, short 1.460.685. Card spending beyond the 7.5M living money
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

## Open questions for the owner (resume here)
1. (decided 2026-10-28: the 31 Jan 2028 salary counts for the pot)
2. Closing the pot gap without the children's needs: games (owner's own), apps not marked `wajib`, or talking to the friend.
3. Mark each app `wajib` or cuttable: Anthropic Max (kept on purpose), Google One, Apple One, Netflix, Spotify, Microsoft 365,
   Squarespace workspace + domain (email), Telkomsel.
4. Google One Oct 2.69M (owner: downgraded to ~300k from next month) and Coway on Mega (760k x2 + 400k in Oct vs 1.21M recorded):
   check on the November statements (the audit flags them again if they repeat).
5. MID*Tokopedia 204.071 every month on HSBC: an instalment that is not recorded yet?
6. Listrik and internet as fixed expenses (due day, how paid); sender allowlist (CIMB collections address) only with the owner.

## Next steps
- Owner: `/new` in Telegram. On 1 Nov ask for the payday list and give the leftover living cash; after paying, tell the bot (card
  payments, pot balance, emergency fund balance).
- After the November statements: calibration per `docs/calibration.md` (Google One, Apple, Coway, bot quality, spend).
- Remaining plan: M3 front/control/applier, M4 comms, M2 gate checks (`docs/assumptions.md`).

## Operating notes
- Deploy: `rsync` from the worktree ROOT (never a subfolder: `--delete` wipes the server tree), back up `ledger.db` first, rebuild `vault-tools`, restart `vault`. Owner must `/new` in Telegram after tool or SOUL changes (owner plans to do it once data and system are done).
- Run the vault agent for batches via `hermes chat --oneshot`, ask for status only, and use a Monitor script for progress.
