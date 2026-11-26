# Lease termination: implementation

Replaces/extends `LEASE_TERMINATION_SETTLEMENT.md` (design notes). Core module: `thinknxg_estate/core/lease_settlement.py`.

## Dates
| Field | Meaning | Where |
|---|---|---|
| Schedule End Date | contractual end, never overwritten | `Lease Contract.end_date` |
| Tenancy End Date | actual end; decides rent owed. May be earlier or later than the Schedule End Date (a warning is shown when later) | `tenancy_end_date` |
| Posting Date | date the settlement enters the GL; mandatory, independent of the Tenancy End Date | `termination_posting_date` |

Posting Date validation: a Fiscal Year must exist, Company "accounts frozen till" (unless the user has the allowed role) and closed Accounting Periods (Journal Entry / Sales Invoice) are checked before anything is posted; ERPNext re-checks at GL posting.

## Files changed
`core/lease_settlement.py` (rewritten), `core/tasks.py` (`_rent_invoice_doc`, `set_company_currency`), `core/api.py` (terminate/preview/reverse/options endpoints, dashboard metrics), `compat.py` (aliases), `estate_leasing/.../lease_contract.{py,js,json}`, `estate_property/.../property_settings.json`, `portal/api/tenant.py`, `www/re-portal/index.html`, `tests/test_lease_termination_settlement.py`.

## New fields
Lease Contract (read-only): `termination_settlement_status`, `termination_mode_of_payment`, `termination_journal_entry`, `termination_charge_invoice`, `terminated_by`, `terminated_on` (plus `tenancy_end_date`, `termination_posting_date`, `termination_settlement` JSON snapshot from the earlier commit). The snapshot holds the audit record: original Schedule End Date, Tenancy End Date, prior financial position (deposit, rent, adjustments), charges and VAT, final amount, Posting Date, created documents and the pre-termination state needed for reversal.
Property Settings: `prorate_final_rent` (default on).

## APIs
- `Lease Contract.get_termination_settlement(tenancy_end_date, posting_date, charges, apply_charge_to_tenant)` – authoritative calculation; returns a `token`. API: `get_lease_termination_settlement`.
- `Lease Contract.terminate(..., charges, calc_token)` – recalculates server-side; refused if the token no longer matches (inputs or ledger changed). API: `terminate_lease_contract`.
- `Lease Contract.reverse_termination(reason)` (System Manager / RE Manager). API: `reverse_lease_termination`.
- `get_termination_options(company, lease)` – Modes of Payment with their account, VAT config.

## Calculation (company currency)
`Net = Deposit balance + advance rent/credit to refund − Outstanding rent − Tenant charges (incl. VAT)`
- positive → Payable to Tenant, negative → Receivable from Tenant, zero → Settled (no cash entry; Mode of Payment not required).
- Deposit balance = amount − deductions − refunds on the submitted Security Deposit.
- Outstanding rent = Payment Ledger outstanding of the live rent Sales Invoices (VAT included, net of payments, JE allocations and credit notes). Installments due on/before the Tenancy End Date that were never invoiced are invoiced first (same builder as the scheduler) on the Posting Date. Total invoice amounts are never summed blindly.
- Rent after the Tenancy End Date: invoiced installments get a full credit note (ERPNext return); never-invoiced ones are cancelled.
- Final period: if the Tenancy End Date falls inside an installment's period (due date to day before the next due date; last period ends at the Schedule End Date) and `prorate_final_rent` is on, the unused fraction (unused days ÷ period days) is credited with a partial credit note (qty −1, reduced rate; tax recalculated). Part of the credit that exceeds what is unpaid is treated as paid rent to refund.
- Amounts follow the invoice rounding rule (Global Defaults rounded total).

## Tenant charges and VAT
Charge amounts are VAT-exclusive (same convention as the rent rate). One Sales Invoice is created on the Posting Date, one item per charge. VAT-applicable lines use the company's default Sales Taxes and Charges Template, falling back to the template on the tenant's latest rent invoice; rate and tax account come from that template. Non-VAT lines use an existing zero-rated Item Tax Template for the same tax account. If VAT is applicable but no template/rate is configured, the calculation is refused. Validation: description required, amount > 0, no duplicate (description+amount), max 25 lines. "Apply Charge to Tenant" off ⇒ charges are ignored.

## Journal Entry mapping (one Journal Entry per termination, Posting Date)
| Line | Account | Party | Reference |
|---|---|---|---|
| Dr deposit applied | `Tenant Security Deposits Payable - ABBR` | Customer | – |
| Cr each rent invoice outstanding | invoice `debit_to` | Customer | that Sales Invoice |
| Dr each credit note balance | invoice `debit_to` | Customer | that credit note |
| Cr charges invoice outstanding | invoice `debit_to` | Customer | charges invoice |
| Cr (payable) / Dr (receivable) difference | Mode of Payment account (company) | – | – |

Rent income, VAT and deposit liability are not re-recognised: income/VAT are posted by the invoices and credit notes, the JE only allocates existing balances. Debits equal credits (checked before submit). Cost center = company default. Receivable settlements are treated as collected through the Mode of Payment at the Posting Date.
Security Deposit: deductions/refunded amounts are updated (status Refunded, or Forfeited when nothing is returned).

## Atomicity and controls
Row lock on the lease, status re-check (no re-termination or duplicate settlement), a savepoint around all posting; any exception rolls back credit notes, invoices, JE and status changes. Only users with write permission on Lease Contract; the portal endpoint is `@staff_only`. Reversal cancels JE, charges invoice, credit notes and termination-created rent invoices, restores installments, deposit and unit.

## UI
Desk dialog and `/re-portal` Terminate Lease screen use sections A Lease Information (dates visually distinct), B Financial Position, C Tenant Charges (description, amount, VAT Yes/No, rate, VAT amount, total, add/remove), D Settlement Calculation (Calculate Amount, Payable/Receivable/Settled badge, breakdown), E Accounting Details (Posting Date, Mode of Payment, account), F Confirmation. Any input change invalidates the calculation and disables Terminate Lease; the button shows a loading state and ignores double clicks.

## Opening Terminate Lease from one lease (contextual entry)
- Lease Contract form: **Terminate** navigates to `/re-portal?screen=terminate_lease&lease=<LEASE>` (the previous dialog remains under Actions > Terminate in Dialog). The Lease Contracts list **Terminate** button uses the same route. Guests are sent to login and returned to the same URL.
- The page calls `get_lease_for_termination(name, property?, unit?)`, which loads the lease from the backend and verifies: lease exists, submitted, not already terminated, Active/Expiring, the user has write permission, any browser-supplied property/unit equal the lease's, the Unit belongs to the lease's Property, the Tenant exists. It returns Property, Unit, Tenant, Schedule End Date and deposit; the page then runs the normal Calculate Amount (rent schedule, outstanding, deposit).
- Property, Unit and Lease Contract are read-only in this mode; Tenant is shown. Tenancy End Date and Posting Date stay editable.
- `terminate` and `get_termination_settlement` re-run the same server checks (`lease_settlement.termination_context`); the portal also sends property/unit, which are validated.
- The sidebar "Terminate Lease" entry keeps the general property/unit/lease selection.

## Known limitations / decisions for the owner
- Proration policy is new (no rule existed); a Property Settings checkbox controls it.
- Charge income is booked through the configured Rent Item's income account (no new accounts); a dedicated charge item/account may be preferred.
- Accounting dimensions beyond cost center are not propagated; Accounting Period closure not exercised on demo data.
- Tenancy End Date later than the Schedule End Date is allowed with a warning; no approval workflow was added.
- Property Settings deposit accounts remain unset on the demo; termination uses the existing `Tenant Security Deposits Payable` account.
- /re-portal screens other than Terminate Lease and the dashboard were audited but not redesigned.
