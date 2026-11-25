# Tenant Self-Service Portal: Implementation

`/tenant-self-service` is a dedicated single-page application with its own shell, navigation, dashboard and API. It does not redirect to or alias `/tenant-portal`, which is unchanged.

## Access

| Mode | Requirement |
|---|---|
| Website account | Frappe user linked through `Tenant.portal_user` |
| Mobile + access code | Property Settings > `enable_access_code_portal`, plus `Tenant.enable_portal` and `Tenant.portal_access_code` |

Both modes pass through the same server-side checks (`_tenant()`).

## Pages

Overview, My Property, My Lease, Rent & Payments (ledger, payment history, cheques, deposit and credit, CSV statement), Maintenance, Documents, Service Requests, Messages, Announcements, Move-in / Move-out, Profile & Settings. Top bar: property / lease selector, search, notifications, help, profile and sign-out. Mobile uses a drawer plus a bottom tab bar. Layout uses logical CSS properties and honours `is_rtl`.

## Files created

- `thinknxg_estate/core/tenant_self_service.py` (API)
- `thinknxg_estate/public/js/tenant_self_service.js`, `public/css/tenant_self_service.css`
- DocTypes: `estate_leasing/doctype/tenant_service_request/`, `tenant_request_message/`, `tenant_announcement/`
- `thinknxg_estate/tests/test_tenant_self_service.py`
- `docs/TENANT_PORTAL_AUDIT.md`, `docs/TENANT_PORTAL_IMPLEMENTATION.md`

## Files modified

- `www/tenant-self-service/index.py` (redirect removed; serves the shell) and `index.html` (standalone shell)
- `demo/seeder.py` (`seed_tenant_access()`), `docs/DEMO_DATA.md`

## Existing code reused

- Sign-in and sessions: `tenant_portal_login`, `resolve_tenant_from_token`, DocType *Tenant Portal Session*, `get_tenant_for_user()`
- DocTypes: Tenant, Tenant KYC Document, Lease Contract, Rent Schedule, Rent Installment, Post Dated Cheque, Security Deposit, Rent Credit Balance, Sales Invoice, Payment Entry, Maintenance Request, Maintenance Job, Move In Out Inspection, Property, Unit, Property Amenity, Property Photo, Utility Account, File, Comment
- Print formats via `frappe.get_print` for invoices, receipts and inspections

## New APIs

All under `thinknxg_estate.core.tenant_self_service.*`, `allow_guest=True`, each calling `_tenant()` first.

- Read: `session_info`, `bootstrap`, `overview`, `announcements`, `my_property`, `lease_detail`, `payments`, `maintenance`, `documents`, `service_requests`, `communications`, `inspections`, `profile`, `notifications`
- Write: `create_maintenance`, `maintenance_feedback`, `upload`, `create_service_request`, `reply_service_request`, `cancel_service_request`, `send_message`, `acknowledge_inspection`, `update_profile`, `sign_out_everywhere`
- Files: `download(kind, ref)` for `invoice`, `receipt`, `inspection` and `file`

## New DocTypes

- **Tenant Service Request** (`TSR-.YYYY.-.#####`) with child **Tenant Request Message**: renewal, extension and termination requests, move-out inspection, damage report, key / access card, parking, address change, occupant update, facility access, profile correction. Permissions: System Manager, RE Manager, Leasing Officer.
- **Tenant Announcement**: category, optional property scope, publish window, body.

Run `bench --site SITE migrate` to install them.

## Security model

- Tenant identity always comes from the token or session. Lease, invoice, receipt, inspection, request and file identifiers from the browser are only looked up inside the tenant's own records; anything else raises `PermissionError`.
- File downloads are checked against an allow-list built from the tenant's own records; arbitrary paths are refused. PDFs are rendered only after the ownership check.
- Uploads: JPG, PNG, WebP or PDF, 8 MB, magic-byte check. Files stay private and are attached to the tenant until claimed by a record.
- No endpoint changes an invoice or payment status. Payment shows instructions only. Lease terms are read-only; renewal, extension and termination are requests for management approval.
- Tenant-visible maintenance data uses tenant stage labels; staff comments and resolution internals are not exposed. Tenant notes are stored as comments prefixed `[Tenant] `.
- Identity numbers are masked in the profile view.
- Invoice PDFs are rendered without third-party stylesheet fetches.

## Configuration

- Enable access-code sign-in in Property Settings and set the tenant's access code (demo: see `docs/DEMO_DATA.md`).
- Set `host_name` in site config so `wkhtmltopdf` can load `/assets` when rendering PDFs.
- Optional: create *Tenant Announcement* records; create Bank Accounts so payment instructions list bank details.

## Test results

- Full app suite: `bench --site fresh.test run-tests --app thinknxg_estate` → 105 tests, OK (includes 8 new tests in `test_tenant_self_service.py`; they skip when no demo data is present).
- Browser (Playwright, 1440 px and 390 px): sign-in through the access-code form, all 11 routes, no console errors, no horizontal overflow.
- HTTP security checks, two demo tenants: own invoice and receipt PDFs download as valid PDFs; cross-tenant invoice, receipt, file, lease parameter, request reply and request cancel all return 403; guest and invalid token return 401; path traversal and `/etc/passwd` return 403; `.exe` upload rejected; no payment-marking endpoint exists.
- Fixed during testing: PDF rendering for access-code sessions (Guest has no print permission), and PDF failures when a print format pulls external web fonts.

## Known limitations

- No online payment provider integration: the portal shows payment instructions; balances change only when finance records the payment.
- Notification preferences, facility booking, satisfaction feedback, FAQ, building rules and occupant records have no backend and are not offered.
- No language selector or Arabic string translation yet; only direction (`dir`) switching via the site language.
- Maintenance statuses are those of the existing module (Open, In Progress, On Hold, Completed, Rejected, Cancelled); tenant stage labels are derived. Tenant completion feedback is recorded as a comment and staff notification; status stays staff-controlled.
- Staff replies to service requests are posted from the DocType form (message table and response field).
- New DocTypes require `bench migrate` on existing sites.
- Browser testing was done on one demo site; file-upload flows were verified through the API.
