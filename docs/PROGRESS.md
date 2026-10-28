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
- `living_reserve` is still the provisional 16M set earlier; analysis says it is not achievable together with the pot and cards (see below).

## Key finding
After fixed costs (11.1M), car (5.7M) and the pot (9M), about 16.2M is left from 42M. Cash living is ~6.7M and card installments ~6.2M, so little room remains for other card spending; the observed card run-rate (median ~20.9M new charges a month, installments included) exceeds it. The balance keeps rolling onto cards unless card spending drops or the pot changes.

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
