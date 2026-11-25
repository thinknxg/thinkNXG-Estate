# Demo Data - Falak Prime Properties LLC (Dubai, AED)

A fictional, interconnected dataset for showcasing thinkNXG Estate. Everything is created
through the app's own DocTypes and flows (lease submit builds the rent schedule and deposit,
PDC hooks create payment entries, deposit refunds, owner statements, deal-to-commission, portal
sync and lead scoring), so dashboards and reports behave as they do in production.

## Commands

Run on a development or demo site only, as the bench user:

    bench --site SITE execute thinknxg_estate.demo.seeder.seed      # build (idempotent)
    bench --site SITE execute thinknxg_estate.demo.seeder.verify    # integrity + counts report
    bench --site SITE execute thinknxg_estate.demo.seeder.reset     # remove all demo data
    bench --site SITE execute thinknxg_estate.demo.seeder.reset --kwargs "{'drop_company': 1}"

`seed` can be re-run safely: a registry (DefaultValue `estate_demo_registry`) and natural-key
lookups prevent duplicates. Every record is tagged `demo-data`. `verify` writes
`private/files/demo_verification_report.md` (a copy of the last run is in
`docs/DEMO_VERIFICATION_REPORT.md`). A benign `NameError: thinknxg_estate` may print after
`bench execute`; ignore it.

## Contents

| Area | Volume |
|---|---|
| Company / finance | Falak Prime Properties LLC (FPP), AED, chart of accounts, UAE VAT 5% (residential exempt, commercial 5%) |
| Property | 5 projects, 34 units, 4 owners, 16 amenities, photos, documents, 80 utility accounts |
| Leasing | 20 tenants with KYC, 21 leases (live, expired, terminated), move-in/out inspections |
| Finance | rent schedules, 39 invoices, 57 payments, 46 PDCs (cleared/deposited/bounced/pending), deposits and refunds, 10 expenses, 8 owner statements |
| Maintenance | 20 requests, 11 jobs, 12 vendors |
| CRM | 31 leads, 6 agents/brokers, 23 deals across stages, 18 site visits, 2 reservations, 5 commissions |
| Portal | 15 listings (incl. 3 sale), wishlists, saved searches, viewings, enquiries |
| Voice / AI | 10 WhatsApp threads with sentiment, voice messages and intents, 26 lead scores |

Portfolio snapshot: occupancy 50% (17 of 34), rent invoiced AED 2.54M, outstanding AED 221k,
deposits held AED 194k, live contract value AED 3.07M.

Demo portal logins use password `Demo@Falak2026`, or the value of site_config key
`estate_demo_password`. Emails use `@falakprime.example.com`.

## Side effects handled during load

The seeder temporarily mutes emails, suppresses background enqueues (sites without workers),
disables WhatsApp auto-reply, auto-assignment and AI scoring, and sets site defaults
(currency, price lists, company) to AED values. All are restored afterwards.

## Known app gaps found while seeding (app logic was not modified)

- Expense JE credits Supplier with is_advance=Yes, which ERPNext v16 rejects (seeder relaxes the check only while posting expenses).
- `Security Deposit.process_refund_or_forfeit` pays from the bank in a way v16 rejects; the seeder posts the refund journal itself.
- Owner remittance Purchase Invoices are created without company/currency, so multi-company AED sites need AED site defaults.
- No setup step for deposit accounts; rent invoicing is not currency-aware on multi-company sites.
- Rent Installments in "Invoiced" status are excluded from TBP; clearing a PDC can create a second Payment Entry.
- `core/demo_data` is a stale older tool; this package supersedes it.

## Notes

Hot-band lead scores are not produced by the current scoring weights on this dataset
(11 warm, 15 cold). Reserved and sale-only units exist so the portal shows varied inventory.
