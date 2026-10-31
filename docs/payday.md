# Payday plan (spec for `vault_tools/payday.py`)

All amounts are integer Rupiah. No floats anywhere.

## Payday date
Last working day of the month (Mon-Fri, not a public holiday), WIB. If the 31st/30th is a weekend or holiday, move back. The holiday list is an input (`holidays`), not hardcoded: it must be supplied and kept current by the owner (open item). An actual salary credit seen in a bank mutation overrides the expected date and amount.

## Window and funding order
Window = [payday, next payday). Obligations due on/after next payday belong to the next window. Funded strictly in this order, ties by due date then alias:
0. overdue (due before payday)
1. card minimum due
2. essentials (fixed expenses, e.g. school)
3. debt installments and pool-account transfers
4. card remaining balance (default: pay in full)
5. savings

Allocation is sequential: each item gets `min(amount, remaining)`. Once one item is short, every later item gets 0. Nothing is dropped silently: each shortfall is listed with an estimated cost of delay (`amount * late_cost_bp / 10000`, rounded half up).

## Output
Transfers `[date, from account, payee alias, amount, reason]` (transfer date = payday if overdue, else max(payday, due - 3 days)), `cash_to_hold` (salary minus funded), `daily_allowance = cash_to_hold // days_in_window` (the salary part only), warnings. The owner's daily money for the window is `living_money = cash_to_hold + living_leftover` (the top-up from the salary plus last cycle's leftover the owner still held): "jatah harian" (`living_per_day`, `living_money // days_in_window`) and the spending pace use it, never the salary part alone. Cash spent from the payday until the owner reported that leftover is already out of it: `set_leftover_living_cash` keeps that figure (`living_leftover_spent`) and the pace does not count it again. Full destination numbers are never in the plan; they are served by `/rincian` outside the model.

## Worked example (dummy numbers)
Payday 2026-10-30 (31 Oct is Saturday), next payday 2026-11-30, 31 days. Salary Rp 10.000.000.

| Item | Due | Amount | Priority |
|---|---|---|---|
| Kartu dbs-1111, minimum | 5 Nov | 300.000 | 1 |
| Sekolah sekolah-2222 | 10 Nov | 2.000.000 | 2 |
| Cicilan pinjaman-3333 | 2 Nov | 1.500.000 | 3 |
| Kartu dbs-1111, sisa saldo | 5 Nov | 2.700.000 | 4 |
| Tabungan | 29 Nov | 500.000 | 5 |

Funded total 7.000.000, cash to hold 3.000.000, allowance 3.000.000 // 31 = Rp 96.774/hari.
With salary Rp 3.000.000: minimum 300.000, sekolah 2.000.000, cicilan only 700.000; unfunded: cicilan 800.000 (est. cost 16.000 at 2%), sisa kartu 2.700.000, tabungan 500.000; cash to hold 0.

## Tests
`services/vault-tools/tests/test_payday.py`: date rules, the example above, and seeded randomized properties (salary conservation, no negatives, funded + unfunded = total due, determinism under input order).
