# Property Admin Portal (/re-portal) audit

Scope: `www/re-portal/index.html` (single page, inline JS) and the `thinknxg_estate.core.api` endpoints it calls, checked against the Property Core DocTypes and ERPNext accounting. Site: `fresh.test` (Falak Prime Properties LLC demo data).

## Method
- Static cross-check: every `callApiWithParams` / `postApi` target resolved to a whitelisted function (79 distinct calls, none missing); every `showScreen()` / nav target has a matching `screen-*`.
- Runtime: logged in as Administrator and exercised `get_dashboard_stats`, `get_lease_contracts_list`, `get_lease_termination_settlement`, `get_termination_options` on the demo data; the page renders and contains the new sections.
- Permissions: 107 of 108 whitelisted functions in `core/api.py` carry `@staff_only`; the page itself is gated by `is_console_user()` (non-console users are redirected to the tenant/owner portals, guests to login).

## Findings and what was done

| # | Area | Finding | Status |
|---|---|---|---|
| 1 | Terminate Lease | No accounting at all: the old flow only changed statuses; no Posting Date, no deposit balance, no charges, no VAT, no journal entry. The "existing Lease Termination backend and journal-entry workflow" referred to in the brief does not exist as a DocType. | Fixed (see LEASE_TERMINATION_IMPLEMENTATION.md) |
| 2 | Terminate Lease | Outstanding rent was a number typed/posted by the browser and compared only with Pending/Overdue installment amounts, ignoring invoices, VAT, credit notes. | Fixed: derived server-side from Sales Invoice ledger balances |
| 3 | Terminate Lease | Rent already invoiced after the end date was left receivable (installment cancelled, invoice untouched). | Fixed: credit notes / pro-rata credit |
| 4 | Dashboard | Only 4 cards. Occupancy used `Unit.status`; monthly rent is contract value ÷ duration (an estimate, not collected rent). Missing: units, vacant, active tenancies, expiring leases, outstanding rent, deposits held, open maintenance, recent terminations. | Fixed: 8 cards added, all from live records |
| 5 | Currency | "OMR" hard-coded in 10 labels while the demo company trades in AED. "VAT (5%)" hard-coded in the invoices table header. | Fixed: labels made currency-neutral; termination screens use the company currency |
| 6 | VAT | `VAT_RATES` is a hard-coded country map used for the jurisdiction breakdown on the dashboard. | Left (display-only); termination VAT is read from ERPNext tax config |
| 7 | Scheduler | `_invoice_installment` built invoices in the site default price-list currency; on a site whose default list is in another currency (demo: OMR list vs AED company) invoicing fails with "Exchange Rate is mandatory". | Fixed: invoices use the company currency and a selling price list in that currency |
| 8 | Deposits | Two independent deposit accounting paths (`Security Deposit.refund` and `update_security_deposit` → `security_deposit_accounting`) and Property Settings `deposit_*_account` unset on the demo. Termination uses `Tenant Security Deposits Payable - ABBR`, the same liability account as `security_deposit_accounting`. | Documented |
| 9 | Rent payment | Recording an installment payment defaulted the date to today. | Fixed earlier (required Posting Date, commit 8bf11a8) |
| 10 | Tenant self-termination | `portal.api.tenant.terminate_lease` called `terminate()` directly. | Fixed: only completes online when no accounting is needed; otherwise a request for the leasing team |
| 11 | Status model | Installment statuses (Pending/Invoiced/Partially Paid/Paid/Overdue/Bounced/Cancelled) were treated inconsistently; the old outstanding query ignored Invoiced and Partially Paid. | Fixed in the settlement engine |
| 12 | Accounting Period | The demo site has no Accounting Period records, so period closure cannot be exercised end to end here; the check is implemented (Closed Document table) and untested against real data. | Open |
| 13 | Accounting Dimensions | Cost center is the company default; no project/property dimension is copied onto settlement entries. | Open (see implementation doc) |

## Property Core integration check
- Properties, Units, Tenants, Leases, Rent Schedules/Installments, Security Deposits, Maintenance Requests are read from their DocTypes (no mock data). Dashboard counts verified against the demo: 5 properties, 34 units (17 occupied, 13 vacant), 17 active tenancies, 10 open maintenance requests.
- Invoices/Payments/Journal Entries are the standard ERPNext documents; the portal creates none of them directly, it calls `Lease Contract.terminate()`.
- Company/currency: read from the Lease Contract's company.

## Residual risks
- `www/re-portal/index.html` is a 7,500-line single file; a screen-by-screen UI revamp beyond the Terminate Lease screen and the dashboard was not attempted, to avoid regressions in working screens.
