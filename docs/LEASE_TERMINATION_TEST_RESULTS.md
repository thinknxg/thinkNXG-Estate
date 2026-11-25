# Lease termination: test results

Command: `bench --site fresh.test run-tests --app thinknxg_estate`
Result: **126 tests, OK** (21 in `tests/test_lease_termination_settlement.py`).

Figures below use the test lease: rent 1,200/yr paid quarterly (300 per installment), deposit 100, company currency AED.

| Scenario | Test | Result |
|---|---|---|
| Early termination, refundable deposit, charges | `test_early_termination_deposit_refund_with_charges_payable` – deposit 100, rent 0, charges 30 ⇒ 70 payable; JE: Dr deposit liability 100, Cr charges invoice 30, Cr Cash 70; deposit ends deducted 30 / refunded 70 | Pass |
| Rent exceeds deposit | `test_rent_exceeds_deposit_is_receivable` – receivable, JE Dr Cash = amount owed, rent invoice outstanding 0 | Pass |
| VAT applicable / not applicable | `test_vat_applicable_and_not_applicable` – 100 with VAT (rate from the UAE VAT 5% template) + 20 without ⇒ VAT 5.00, invoice total 125, VAT account credit 5.00 | Pass |
| VAT without configuration | `test_vat_without_configuration_is_refused` | Pass |
| Charge validation | `test_charge_validation` (blank, ≤0, duplicate; unchecked ⇒ zero) | Pass |
| No security deposit | `test_no_security_deposit` – receivable, Mode of Payment required | Pass |
| Zero settlement | `test_zero_settlement_creates_no_cash_entry` – no JE, no Mode of Payment needed | Pass |
| Different posting date | `test_different_posting_date` – all JE GL entries on the Posting Date, Tenancy End Date unchanged | Pass |
| Posting date outside fiscal year | `test_posting_date_outside_fiscal_year_refused` | Pass |
| Posting Date mandatory / stale calculation | `test_posting_date_is_mandatory`, `test_token_required_and_stale_calculation_refused` | Pass |
| Duplicate submission | `test_duplicate_submission_is_refused` – second call fails, one JE | Pass |
| Failed accounting, no partial termination | `test_failed_accounting_leaves_no_partial_termination` – lease stays Active, charges invoice rolled back, deposit untouched | Pass |
| Historical lease unchanged | `test_historical_terminated_lease_is_untouched` | Pass |
| Rent invoiced after the end date | `test_rent_invoiced_beyond_end_date_is_credited_automatically` – credit note dated the Posting Date, original invoice credited in full | Pass |
| Final period pro rata | `test_final_period_is_prorated_with_a_credit_note` – credit + owed = 300 within rounding | Pass |
| Reversal | `test_reversal_restores_the_lease_and_cancels_entries` – JE and invoice cancelled, deposit and unit restored | Pass |
| Outstanding from invoice balances | `test_outstanding_counts_invoiced_and_partially_paid_balances` | Pass |
| Three dates separate; deposit balance | `test_three_dates_stay_separate`, `test_settlement_uses_deposit_balance_not_original_amount`, `test_deposit_refund_pays_out_the_balance_only` | Pass |

GL verification is done inside the tests (GL Entry per voucher: debit = credit, posting dates, accounts). The brief's example figures (50,000 / 10,000 / 5,000 ⇒ 35,000 and 20,000 / 25,000 / 5,000 ⇒ 10,000 receivable) follow the same formula; the tests use smaller amounts so the invoice rounding rule does not obscure the checks.

Manual check on the demo site (HTTP, Administrator): settlement preview for LEASE-2026-1440 with a 500 charge at VAT 5% ⇒ charges 525, deposit 24,000, 23,475 payable. Dashboard endpoint returns the new metrics.

Not covered: Accounting Period closure (none on the demo), browser-level interaction of the new screen (the inline script passes `node --check` and the page serves; clicking through was not automated).
