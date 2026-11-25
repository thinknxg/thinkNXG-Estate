# Tenant Portal Audit

Scope: the tenant-facing surfaces of thinkNXG Estate before the `/tenant-self-service` rebuild.
Status values: **Implemented**, **Partial**, **UI-only**, **Backend-only**, **Missing**, **Broken**, **Security**.

## 1. Existing architecture (before the rebuild)

| Surface | Route | Files | Sign-in |
|---|---|---|---|
| Tenant portal (website session) | `/tenant-portal`, `/tenant-portal/*` | `www/tenant-portal/*`, `www/tenant_portal_common.py`, `portal/api/tenant.py` | Frappe user linked via `Tenant.portal_user` |
| Access-code portal | `/tenant-portal` (code flow) | `core/tenant_portal_api.py`, DocType *Tenant Portal Session* | Mobile + access code, hashed token in `X-Tenant-Token` |
| Tenant self-service | `/tenant-self-service` | `www/tenant-self-service/index.py` | **Redirected to `/tenant-portal`** (no page of its own) |

Identity helpers: `get_tenant_for_user()` (`estate_leasing/doctype/tenant/tenant.py`), `resolve_tenant_from_token()` (`core/tenant_portal_api.py`). Role gating and permission queries live in `core/permissions.py`; routes and aliases are declared in `hooks.py` (`/api/method/re_*` aliases are kept).

## 2. Existing tenant APIs

`core/tenant_portal_api.py`: `tenant_portal_login`, `tenant_portal_dashboard`, `tenant_portal_documents`, `tenant_portal_maintenance_list`, `tenant_portal_create_maintenance_request`, logout/session helpers.
`portal/api/tenant.py`: website-session equivalents for the standard portal.

## 3. DocType relationships

```
Tenant ──< Lease Contract >── Unit ── Property
              │
              ├── Rent Schedule ──< Rent Installment ── Sales Invoice ──< Payment Entry (receipts)
              │                         └── Post Dated Cheque
              ├── Security Deposit
              ├── Move In Out Inspection
              └── File attachments
Tenant ──< Maintenance Request ── Maintenance Job (supplier / technician)
Tenant ──< Tenant KYC Document ── File
Tenant ── Rent Credit Balance
Unit / Property ── Utility Account, Property Amenity, Property Photo
```

## 4. Feature classification (before)

| Feature | State | Notes |
|---|---|---|
| `/tenant-self-service` page | **Broken** | Redirect only; no UI, no navigation |
| Access-code sign-in and token sessions | Implemented | Hashed token, header transport, rate limited |
| Dashboard | Partial | Lease filter lacked `docstatus = 1`; few metrics |
| My Property | Missing | Only unit name shown |
| Lease view / history | Partial | Active lease only; no history, no documents |
| Renewal / extension / termination requests | Missing | No DocType or API |
| Rent ledger, due / overdue | Partial | Installment list without derived overdue state |
| Invoice and receipt download | Backend-only | No tenant-safe download gateway |
| Deposit and credit balance | Backend-only | Data existed, nothing exposed |
| Maintenance create / list | Partial | Create worked; no tracking stages, tenant notes or feedback |
| Maintenance photos | **Security** | `photo_1` / `photo_2` accepted as client-supplied paths |
| Maintenance detail | **Security** | Resolution notes and job links exposed without filtering |
| Documents | **Security** | Returned every File attached to the lease, including internal ones |
| Service requests (non-maintenance) | Missing | |
| Messages / communication history | Missing | |
| Announcements | Missing | |
| Move-in / move-out | Backend-only | Inspection DocType existed; no tenant view or acknowledgement |
| Profile and contact update | Missing | |
| Notification preferences | Missing | Nothing in the system consumes preferences |
| RTL / language | Missing | Currency hardcoded, no `dir` support |
| Responsive layout | Partial | No mobile navigation pattern |

## 5. Security concerns found

1. Client-supplied file paths on maintenance creation (path injection / foreign file attach).
2. Document list unfiltered by category: internal lease files could reach tenants.
3. Maintenance responses leaked internal resolution notes and linked job records.
4. Dashboard query without `docstatus = 1` could surface draft or cancelled leases.
5. No central download gateway: invoices, receipts and files had no ownership-checked route.
6. Hardcoded currency in the old page.

## 6. UX problems

No application shell, no navigation between sections, no empty / loading / error states, no mobile navigation, no breadcrumbs, no search, no notification centre, no consistent money / date formatting, no RTL.

## 7. Recommendations and priority

| Priority | Item |
|---|---|
| P0 | Dedicated `/tenant-self-service` route with its own SPA (no redirect) |
| P0 | Server-derived identity on every endpoint; ownership checks for lease, invoice, receipt, inspection, request and file ids |
| P0 | Secure download gateway with an allow-list of the tenant's own files |
| P1 | Dashboard, rent ledger with derived Overdue, deposit and credit visibility |
| P1 | Maintenance centre with tenant-safe stage labels, notes and feedback |
| P1 | Documents centre (invoices, receipts, inspections, KYC, uploads) |
| P1 | Service requests (including renewal / extension / termination as requests for approval) and messaging |
| P2 | Announcements, move-in / move-out, profile, notifications |
| P2 | Mobile navigation and RTL support |
| P3 | Online payment provider integration, facility booking, feedback, FAQ (need new backend modules) |
