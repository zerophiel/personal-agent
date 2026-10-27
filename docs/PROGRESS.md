# Progress and resume point (finance / vault)

Last updated: 2026-10-27. Branch `worktree-m1-skeleton`, draft PR #1. 221 vault-tools tests pass.
No secrets or personal amounts are recorded here; the numbers live in the ledger on the VPS.

## Done
- M1 platform and M2 vault deployed; 36+ MCP tools; Hermes vault bot uses them (`tools.tool_search.enabled: "off"`).
- Mutations Jan-Oct recorded and verified complete for BCA, Mandiri, Jago (28 files). Categorization ~85-96% for Jan-Aug.
- Categories added: `perantara:` (money only passing through the owner), `berhenti:` (ended costs: driver, house installment, Allianz commission), `sekali:` (one-offs), `bunga`.
- Card statements recorded: CIMB, Mandiri (Jan-Oct), HSBC (Feb-Oct), DBS, Mega (partial), BCA and Jenius (Oct only).
- Card installments (x/y on statements) in the ledger, the roadmap and card capacity. Subscriptions table (active/ended/unsure).
- `living_reserve` is set by the owner to Rp 16.000.000 (cash + card, provisional).
- `pending_statements` queue is derived from the ledger (the events cursor lost work).

## Open questions for the owner (resume here)
1. Subscriptions to confirm and record: Apple (fixed charge + variable ones), Spotify, Squarespace workspace, Microsoft (plan change), Catchplay, AWS (usage based), GoPro and domain (yearly?), Google One (which card?). Anthropic/OpenAI/Netflix/YouTube not found on the 7 card statements read: maybe on BCA/Jenius or another account.
2. Anomalies: Coway charged three times in Oct, gym doubled in July, CIMB April statement does not reconcile, HSBC January statement belongs to an older card number (skipped).
3. Mei (26M) and Aug (38.8M) card charges: unknown one-offs; decides whether the reserve should be ~16M or ~18M.
4. BCA and Jenius card statements before Oct, and the BCA Oct text mutation PDF (12-19 Oct is image-only).
5. Sender allowlist: 11 rejected emails (Mega 1, CIMB 6, Mandiri 1, DBS 2). Needs the real sender address first; do not widen without the owner.
6. Vanessa Inka incoming monthly transfers: skipped by the owner for now (not categorized).

## Next steps
- Record confirmed subscriptions; separate installments and subscriptions from day-to-day spending.
- Recompute `living_cost_analysis` including card spending, then propose the final `living_reserve` and regenerate the payday plan.
- Tune: per-card `interest_bp_month` from statements, MTF autodebit amount (5.706.000 vs 5.701.000), SPayLater/Xendit as possible debts.
- Remaining plan: Notion sync, daily alert cron, M3 front/control/applier, M4 comms, M2 gate checks (`docs/assumptions.md`).

## Operating notes
- Deploy: `rsync` from the worktree ROOT (never a subfolder: `--delete` wipes the server tree), back up `ledger.db` first, rebuild `vault-tools`, restart `vault`. Owner must `/new` in Telegram after tool or SOUL changes.
- Run the vault agent for batches via `hermes chat --oneshot` and ask for status only.
