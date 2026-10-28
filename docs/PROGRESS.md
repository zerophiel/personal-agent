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

## Notion
Snapshot pages created 2026-10-28 (private): `Agent` > `Finance` (Rencana gajian, Tagihan kartu, Cicilan kartu dan langganan, Peta jalan bebas utang, Anggaran dan batas) and `Agent` > `General` (empty). Written from the ledger summaries by Claude Code through the Notion connector; no card/account numbers.
AUTOMATED since 2026-10-28: `vault_tools/notion_sync.py` (no LLM) rewrites the five Finance sub-pages from the ledger every day at 06:30 WIB (`pa-notion.timer` -> `docker exec ... python -m vault_tools.notion_sync`). Token in the `notion_token` docker secret (vault-tools), page id in `/opt/personal-agent-data/vault-tools/notion.json`, egress via squid-vault (api.notion.com). New blocks are appended first, then the old ones are archived; child pages are never deleted. Run by hand: `ssh ... sudo docker exec personal-agent-vault-tools-1 python -m vault_tools.notion_sync`.
Card payment targets: Mandiri via app menu; BCA, HSBC, CIMB, Mega, DBS transfer to the card number; Jenius transfer to the owner's Jenius account. The owner registers numbers in the vault bot (card number as a plain message, `/rekening` for the Jenius account); `link_card_payees` then fills `cards.pay_to_alias` by last 4 digits. A leftover test payee `num-1111` exists from the early spike (not deleted automatically).
Card budgets are `kartu:<category>` (count only rows paid by a card, via `record_expense card_alias`); cash budgets (listrik, internet, transport) count account payments.

## Open questions for the owner (resume here)
1. Google One: statements show Rp 175.380 a month on Jenius (Jul-Sep), the owner said 309.000. Which is right?
2. Anthropic on Jenius Sep: three charges the same day (USD 5.55, 11.10, 22.20); also DeepSeek and Moonshot AI top-ups. Subscription or one-off credits?
3. Squarespace workspace (304k), Catchplay, AWS: still used? GoPro and domain: owner wants to stop them.
4. SPayLater installment of 312.668 in November: tenor, total remaining; Coway monthly total (three charges seen in Oct).
5. Listrik (token, ~2.3M), internet (~0.54M): due day and how paid, to become fixed expenses; transport ~1M budget.
6. BCA October mutation as text PDF; BCA card Sep/Oct and Jenius Oct statements for installment scan.
7. Sender allowlist: rejected senders are notification addresses (DBS, Mandiri, Mega) and `consumer@collection.cimbniaga.co.id` (CIMB collections: the owner should check whether it is a late-payment notice). Do not widen without the owner.
8. Notion sync: needs a Notion integration token (owner runs `make secret-set`) and the Agent/Finance page shared with the integration; exporter not built yet.
9. Decide the card/pot strategy (reduce new card spending, or Option B deferral) and then set the real `living_reserve`.

## Next steps
- Verify Google One / Anthropic from statements, record confirmed subscriptions, add listrik/internet as fixed expenses.
- Recompute `living_cost_analysis` with cards and subscriptions separated; propose and set the final `living_reserve`; regenerate the payday plan.
- Build the Notion exporter; tune per-card `interest_bp_month`; remaining plan: M3 front/control/applier, M4 comms, M2 gate checks (`docs/assumptions.md`).

## Operating notes
- Deploy: `rsync` from the worktree ROOT (never a subfolder: `--delete` wipes the server tree), back up `ledger.db` first, rebuild `vault-tools`, restart `vault`. Owner must `/new` in Telegram after tool or SOUL changes (owner plans to do it once data and system are done).
- Run the vault agent for batches via `hermes chat --oneshot`, ask for status only, and use a Monitor script for progress.
