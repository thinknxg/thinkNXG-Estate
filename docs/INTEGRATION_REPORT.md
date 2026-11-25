# thinkNXG Estate — Repository Integration Report

**Scope:** audit of four repositories and their consolidation into one app, `thinknxg_estate`
(Phases 1 and 2 of the master plan, plus the security fixes the audit made necessary).
**Date:** 24 November 2026 (Phases 1–2), updated the same day with Phases 3–8 and release 1.2
**Test platform:** Frappe Framework 16.60.2 + ERPNext 16.60.0, Python 3.14, MariaDB 10.11.

## 1. Summary

The four repositories were already four Frappe v16 apps from the same generator, written by the
same team and sharing one data model (re_crm, re_portal and re_voice all depend on re_core).
They are not four products that need merging so much as one product split across four
installs. They are now a single app with seven modules, one install, one navigation, one role
set and one compatibility layer that keeps every old API URL working.

What was done:

- **One app:** all 68 DocTypes, 9 reports, 22 KPI cards, 8 charts, 2 print formats, 17
  scheduled jobs, 24 voice commands and all web pages live in `thinknxg_estate`. DocType
  names and database tables are unchanged, so no business data moves.
- **In-place upgrade:** a site running the four legacy apps is upgraded by installing
  thinkNXG Estate. This was rehearsed on a site with demo data: row counts across 69 tables
  were identical before and after, and the legacy app code on disk was untouched.
- **Compatibility:** 170 legacy `/api/method/re_*` paths, including the Meta webhook and
  Property Finder / Bayut feed URLs, route to the unified code. The live tests ran with the
  legacy packages blocked from import.
- **Security:** five vulnerabilities found and fixed (§6), two of them critical, each
  reproduced on the original code first.
- **Defects:** nine functional defects found and fixed (§5).
- **Tests:** 96 automated tests (78 integration + 18 unit), 62 HTTP checks through nginx and an
  11-step browser walk-through, all passing on a freshly upgraded legacy site and on a new site.

Phases 3–8 are summarised in §10, release 1.2 in §11; what is still open is in §12.

## 2. Repositories audited

| Repository | Commit audited | App | Python lines | Web lines (JS/HTML/CSS) | DocTypes (child / single) | Reports | Whitelisted endpoints (guest) | Scheduled jobs |
|---|---|---|---|---|---|---|---|---|
| thinknxg/re_core | `0ee6d04` (13 Nov) | re_core | 8,213 | 10,611 | 35 (11 / 1) | 7 | 145 (20) | 7 |
| thinknxg/re_crm | `99a5382` (11 Nov) | re_crm | 1,191 | 50 | 11 (1 / 2) | 1 | 16 (0) | 4 |
| thinknxg/RE-Portal | `f463988` (23 Nov) | re_portal | 1,712 | 741 | 7 (1 / 3) | 0 | 16 (9) | 1 |
| thinknxg/RE-Voice | `3a8ffbc` (23 Nov) | re_voice | 3,191 | 10 | 15 (2 / 2) | 1 | 3 (3) | 5 |

All four use Frappe v16 + ERPNext v16, `flit_core` packaging, no third-party Python
dependencies, and the same `scripts/generate_doctypes.py` generator pattern. There are no
framework conflicts: nothing had to be ported from another stack.

### re_core — property, tenant, lease and finance core
Property → Unit → Lease Contract (submittable) → Rent Schedule / Rent Installment → Sales
Invoice / Payment Entry; Post Dated Cheques with a Received → Deposited → Cleared/Bounced
lifecycle; Security Deposits with journal entries; owner statements and remittances;
maintenance requests and jobs; move-in/out inspections; bulk rent receipts. Row-level
isolation for portal tenants (permission query conditions on six DocTypes). Three web pages:
`/re-portal` (a 7,587-line single-page staff console), `/listings` (a public listings app
with visitor sign-up, wishlist, saved searches, site-visit and lease requests) and
`/tenant-self-service` (a tenant page using mobile number + access code tokens). Demo-data
exporter/loader with personal data scrubbed.

### re_crm — leads, deals, reservations, commissions, WhatsApp
RE Lead (round-robin assignment, first-contact SLA with escalation), RE Deal (kanban
pipeline; *Won* requires a submitted lease and drafts the agent's commission), Site Visit,
Reservation (submittable, blocks the unit, booking fee), RE Agent with flat / percent /
tiered commission plans, Commission Entry (submittable, journal entry). WhatsApp text sending
through the Meta Cloud API with a message log.

### RE-Portal — public listings, inquiries, tenant portal, feeds, AI chat
Listing (website generator at `/property/<route>`, auto-synced from Property/Unit),
Listing Inquiry with honeypot, time-trap and rate limit, bridged to RE Lead; `/properties`
search and `/contact`; a session-based tenant portal at `/tenant-portal` (dashboard, lease,
payments, maintenance); token- and brokerage-gated Property Finder and Bayut XML feeds; an
Arabic/English listings chatbot (Anthropic or Gemini) that can only read published listings.

### RE-Voice — voice-first WhatsApp CRM
Signature-verified Meta webhook (fails closed without the app secret), deduplicated and
processed in the background; agent pipeline (ASR → translation → keyword matcher → LLM
fallback → locale-aware entity extraction → confirmation for destructive commands → executes
as the agent's user) strictly separated from the customer pipeline (auto-reply with matching
listings, post-visit feedback). 24 data-driven voice commands, transparent lead scoring,
sentiment, conversation summaries, monthly AI budget, audio retention purge.

## 3. Overlaps and conflicts, and how each was resolved

| Area | What existed | Resolution |
|---|---|---|
| App boundaries | Four apps with a strict dependency chain; re_core shipped custom fields on `RE Lead` (owned by re_crm) and on its own DocTypes; re_voice created custom fields in code at install | One app. 31 custom fields and 2 property setters on the platform's own DocTypes are now standard fields. 9 fields on ERPNext/Frappe DocTypes (User, Purchase Invoice) remain as fixtures. |
| Navigation | 7 workspaces (RE Core hub, Property Operations, RE Finance, RE Maintenance, RE CRM, RE Portal, Voice CRM), a Workspace Sidebar and a desktop icon | One **thinkNXG Estate** sidebar (v16 `Sidebar`, 73 items in the requested structure), a main dashboard workspace and three focused dashboards (Finance, Maintenance, CRM). Legacy navigation is removed on upgrade. |
| Visitor / lead records | `/listings` visitors became **ERPNext Leads**; `/properties` inquiries became **RE Leads**; Property Enquiry, Site Visit Booking, Saved Search and Property Wishlist link to ERPNext Lead only | RE Lead is the single CRM record. Those four DocTypes gained a `re_lead` link, every portal action resolves one RE Lead per person (matched on mobile, then email), and the upgrade links existing records. |
| Inquiry endpoints | Three guest write paths: `re_portal.api.listings.submit_inquiry`, `re_portal.api.inquiries.create` (no CRM bridge, wrote non-existent fields) and `listing_portal.submit_enquiry` | All three create the CRM lead. |
| Site visits | `Site Visit Booking` (portal request, no deal) vs `Site Visit` (CRM, requires a deal) | Kept both, with distinct roles: the booking is the visitor's request and is linked to the RE Lead; agents convert it into a deal and site visit. |
| Tenant portals | `/tenant-portal` (website login) and `/tenant-self-service` (mobile + access code tokens) | `/tenant-portal` is the standard portal. The access-code portal is hardened and opt-in (Property Settings); the upgrade keeps it on where tenants already use it. |
| WhatsApp | re_crm `send_whatsapp` (text, Message Log) and re_voice outbound (interactive, templates, 24-hour window, Webhook Log), both reading one WhatsApp Settings | Kept both code paths on one settings record. Merging them into one channel service is Phase 5 work (§10). |
| AI providers | `Portal Chat Settings` (chatbot) and `AI Settings` (voice) configure LLM providers separately | Unchanged for now; consolidation listed in §10. |
| Public listing pages | `/listings` (unit-based app with visitor accounts) and `/properties` + `/property/<route>` (Listing-based, SEO, feeds) | Both kept and rebranded. Converging them into one public portal is Phase 3 work. |

## 4. Consolidated architecture

```
thinknxg_estate/
  estate_property/     Property, Unit, Property Owner, Amenity, photos, documents, utility accounts, Property Settings
  estate_leasing/      Tenant (+KYC), Lease Contract, Lease Charge, inspections, Tenant Portal Session
  estate_finance/      Rent Schedule/Installment/Payment, Post Dated Cheque, Security Deposit, Owner Statement,
                       Tenancy Bulk Payment, Rent Credit Balance, Expense Property  (+ 5 finance reports)
  estate_maintenance/  Maintenance Request, Maintenance Job  (+ Maintenance Overview report)
  estate_crm/          RE Lead, RE Deal, RE Agent, Commission Entry/Slab, Reservation, Site Visit, Lead Source RE,
                       Property Enquiry, Site Visit Booking, Saved Search, Property Wishlist, WhatsApp settings/log
  estate_portal/       Listing (+photos), Listing Inquiry, feed / chat / portal settings, Portal Chat Session
  estate_voice/        15 voice DocTypes  (+ Voice Command Analytics report)
  thinknxg_estate/     home module: workspaces, Sidebar, number cards, dashboard charts and chart sources
  core/ crm/ portal/ voice/   business logic carried over from each legacy app (APIs, tasks, integrations)
  setup/               install hooks and the legacy upgrade (migrate_legacy.py)
  compat.py            legacy method path → unified path (170 entries)
  www/  templates/  public/   web pages and assets of all four apps
```

Decisions:

- **DocType names unchanged.** Renaming (for example "RE Lead" to "Estate Lead") would mean
  migrating every table, link, report, permission and client. It is cosmetic and was left out.
- **Business logic kept, not rewritten.** The code of each app was moved with mechanical import
  rewriting (`tools/consolidate.py` in the build workspace), then fixed where the audit found
  defects. This keeps the working behaviour of the source repositories.
- **Compatibility at the routing layer.** `hooks.override_whitelisted_methods` maps every old
  module-level path to the new one. Document methods need no mapping because DocType names
  are unchanged.
- **No new services.** Same single Frappe app, same scheduler, same queues.

## 5. Functional defects found and fixed

| # | Defect | Impact | Fix |
|---|---|---|---|
| D1 | `/listings` guest enquiries discarded the visitor's name and phone (the form sends them, the endpoint ignored them) | Agents received enquiries with no way to reply | Contact details stored; guests must leave name + valid mobile; enquiry linked to an RE Lead |
| D2 | The portal → CRM bridge created RE Leads with mobile `"N/A"`, which RE Lead validation rejects; the error was swallowed | Visitors who signed up without a phone never reached the CRM | Bridge uses real contact data; RE Lead accepts mobile **or** email, still validating mobile format |
| D3 | `re_portal.api.inquiries.create` created inquiries with no CRM lead and wrote two fields that do not exist | Leads lost from that form | Same CRM bridge as the main inquiry endpoint |
| D4 | `pdc_bank_sync` imported `get_payment_entry` from `frappe.model.mapper` | Submitting any Post Dated Cheque failed on v16 | Imports from ERPNext; regression test submits a cheque and checks the Payment Entry |
| D5 | re_core's installer used the group "All Item Groups" when the ERPNext setup wizard had not run | `install-app re_core` crashed half-way, so its fixtures (custom fields, roles, print formats) never synced | Rent item is created when Item Groups exist; retried after migrate and before rent invoicing |
| D6 | RE-Voice's report lived outside its module folder | *Voice Command Analytics* was never installed | Report now ships in the Estate Voice module |
| D7 | A new Tenant reused any Customer with the same name | Two tenants with the same name would share one receivable ledger | Reuse only if no other tenant bills against that Customer |
| D8 | `submit_inquiry` read the User-Agent header unconditionally | Crashed outside an HTTP request (background bridges, tests) | Guarded |
| D9 | The *Voice Ops Manager* role (re_voice) had no permission on any DocType | The role could be assigned but gave no access | Manages voice, AI and WhatsApp configuration; reads all message and voice logs |

## 6. Security findings

| # | Severity | Finding (present in the original apps) | Fix | Verified |
|---|---|---|---|---|
| S1 | **Critical** | Whitelisted document methods changed state after Frappe's default *read* check. A tenant can read their own cheques and deposit, so they could mark their own cheque Deposited → Cleared (posting a Payment Entry, marking rent paid and triggering owner remittance), refund their own security deposit, or terminate their own lease. Agents with read access could mark commissions paid. | Every state-changing document method checks the matching permission (`submit` for cheques, deposits and commissions, `write` for terminate, make job and make deal) | Reproduced on the legacy code (tenant moved own cheque to *Deposited*); integration test asserts refusal |
| S2 | **Critical** | None of the 118 staff endpoints (`re_core` / `re_crm` API) checked roles. Several aggregate with direct SQL that ignores record permissions, and some write with `ignore_permissions`. Any logged-in website user (a tenant, or anyone who signed up on `/listings`) could call them. | `staff_only` guard: desk users with an estate or accounts role; the `/re-portal` console redirects non-staff | Reproduced on the legacy code (tenant read portfolio totals and monthly rent income); integration and HTTP tests assert 403 |
| S3 | High | Access-code tenant API: any guest could post a rent payment (Payment Entry) for an installment, on the tenant's word | Payments cannot be recorded from the tenant side; the page shows payment instructions instead | Test asserts refusal |
| S4 | High | Access-code login had no rate limit, a non-constant-time code comparison, and stored session tokens in plain text | Rate limited (10 per 15 min per IP), `hmac.compare_digest`, only the SHA-256 of the token is stored, disabled tenants are rejected, and the whole API is off unless enabled in Property Settings | Tests assert hash-only storage and default-off |
| S5 | Medium | Tenants could terminate their lease from the portal with immediate effect (unit freed, installments cancelled), bypassing notice, inspection and deposit settlement | By default this becomes a request (comment, notification, ToDo for the leasing team); an optional setting allows online termination | Test asserts the lease stays Active |
| S6 | Medium | Visitor sign-up, login and enquiry endpoints had no rate limits | Rate limited and POST-only | — |

Unchanged and confirmed sound: the WhatsApp webhook (HMAC signature, fails closed, verify
token compared in constant time); the feed endpoints (token, brokerage confirmation, per-listing
opt-in and permit number); public listing search (published records only, rate limited); the
chatbot's tool scope; the session-based tenant portal resolving the tenant server-side.

## 7. Technical debt (documented, not changed)

- **Generator drift:** each repo's `scripts/generate_doctypes.py` no longer matches its
  committed JSON (fields were added later), and re_core's README says 19 DocTypes where there
  are 35. The JSON files are the source of truth; the generators were not carried over.
- **One-off console scripts** at the root of re_core (`check_*.py`, `rename_*.py`,
  `fix_workspace.py`, `build_workspace.py`, `list_doctypes.py`) were not carried over.
- **`/re-portal` is a 7,587-line single HTML file** that duplicates many desk forms. It works
  and is kept, but it is the main candidate for the Phase 6 UI rebuild.
- **Mixed indentation** (tabs and spaces) across modules.
- **No automated tests in the sources** apart from RE-Voice's framework-free logic tests
  (ported); the DocType test files were empty stubs.

## 8. Upgrade of existing sites

See `MIGRATION.md`. Rehearsed on a site with all four legacy apps and 131 demo records:

| Step | Result |
|---|---|
| Legacy custom fields / property setters made standard | 31 / 2 |
| Voice command handler paths rewritten | 24 |
| Legacy portal records linked to CRM leads | 10 (matched to existing leads, no duplicates) |
| Access-code portal | kept enabled (a tenant had an access code) |
| Legacy workspaces, sidebar, icon, scheduled jobs removed | 7 workspaces, 1 sidebar, 1 icon, 17 jobs |
| Legacy apps detached / module defs removed | 4 / 4 |
| Row counts across 69 tables (plus rent and lease value checksums) | identical before and after |
| Legacy app code on disk | unchanged |

## 9. Verification

| Check | Result |
|---|---|
| Fresh install on thinkNXG ERP v16 (68 DocTypes, 9 reports, 22 cards, 8 charts, sidebar, roles, seeds) | pass |
| `bench migrate` after install | pass |
| Upgrade rehearsal (§8) | pass, repeatable script |
| Integration tests (`tests/test_estate_integration.py`, `tests/test_estate_portal_crm.py`) | 41 / 41 |
| Unit tests (`tests/unit`): voice entities and matcher, feed XML, compatibility map, lease months | 18 / 18 |
| HTTP checks on the upgraded site with legacy packages blocked from import (guest, staff, tenant, owner, legacy URLs, webhook, feeds, pages, dashboard, reports) | 56 / 56 |
| Every `frappe` / `erpnext` import in the app, top-level and nested | resolves |

Not verified here: the JavaScript bundle build (the sandbox could not download one frontend
dependency of Frappe itself; pages were rendered server-side with a stub asset manifest), live
WhatsApp / Meta and LLM calls, and real Property Finder / Bayut onboarding.

## 10. Phases 3–8 (second delivery)

| Phase | Delivered | Verified by |
|---|---|---|
| 3 — Portal | **Owner portal** (`/owner-portal`, role *Property Owner*, provisioned from *Enable Owner Portal* on the owner): properties and units, occupancy, active leases, rent collected and outstanding, monthly billed vs collected, expenses, owner statements with PDF, maintenance. All data scoped server-side to the owner's properties and units; owners hold no document permissions. **Schedule a viewing** on every listing page (date + slot, creates a Site Visit Booking for the visitor's CRM lead). **Search**: bathrooms, furnishing, area range, sorting, map coordinates; similar properties on listing pages. | Integration tests (owner isolation, foreign statement refused, viewing flow and date rules, search filters/sort); HTTP checks for owner pages and isolation |
| 4 — CRM | **Property matching** on the lead (budget, type, bedrooms, location, area, amenities, move-in date; occupied units whose lease ends in time count), shown live on the lead form with one-click *Set as interest*; **recommendations recorded automatically** when a lead is qualified (optional WhatsApp). **Lead ownership**: sales agents and brokers see only their leads, deals and site visits (setting). **Brokers**: agent type, brokerage, licence, agreement and expiry. **Targets**: monthly deal and value targets with achievement in the Agent Leaderboard. | Tests for scoring, exclusions, possession date, qualify comment, ownership on/off |
| 5 — Communications | **One WhatsApp channel** for every business message: logged once against its record, free text inside the 24-hour window, the approved template for the message's purpose outside it, otherwise *Skipped* with the reason. **Communication History** on leads, deals, tenants, owners and properties (WhatsApp, voice notes, email, notes, enquiries, visits, maintenance). **Transcript retention** setting and purge job. | Tests for skip/queue rules and timeline content |
| 6 — Interface | **Design system** (`estate.css`: navy/teal tokens, cards, KPI tiles, tables, pills, buttons, fields, tabs) on owner, tenant, listing and search pages. **thinkNXG Estate Dashboard** desk page (`/app/estate-dashboard`) with company, property, city and period filters: 18 KPIs and 9 charts from live records, each KPI opening the matching list or report; company User Permissions respected. | Test comparing KPIs with records; HTTP check |
| 7 — Reports | Property Register, Unit Availability (incl. units freeing up by a date), Tenant Register (outstanding rent, deposit held), Deposit Register, Property Profitability, Lead Source Analysis, Site Visit Conversion, Broker Commission Statement (agents see only their own), Vendor Performance. | All 18 reports run on demo data; test cross-checks figures against source records |
| 8 — Production | **Role matrix**: Leasing Manager, Broker, Receptionist, Maintenance Technician added; Owner Statement opened to finance roles. **Console vs desk split**: portfolio-wide console APIs and dashboard for management roles only; scoped roles work through permission-checked desk forms. **71 database indexes** on the fields the scheduler, portals and reports filter on. | Role tests; full suite, upgrade rehearsal and HTTP checks re-run |

Defects found and fixed in this round:

| # | Defect | Impact | Fix |
|---|---|---|---|
| D10 | Lease duration used `month_diff`, which counts both end months | A one-year lease ending on its anniversary got **13 monthly installments**, and generated term charges of **13/12 of the annual rent** | `lease_months()` used for installments and term totals; unit-tested |
| D11 | `/properties` offered unit type "4BR", which does not exist (the option is "4BR+"), and omitted Studio, 1BR and commercial types | The filter never matched 4-bedroom units | Options read from the Unit schema |
| D12 | Property Owner reused any Supplier with the same name | Two owners with one name would share one payable ledger | Same guard as tenants |
| D13 | Console endpoints use unfiltered queries | Sales agents would bypass lead ownership through the console | Console limited to portfolio-wide roles |
| D14 | New checkbox settings read as 0 on upgraded sites until the form is saved | Defaults of 1 silently off | `utils.setting()` honours the declared default |

## 11. Release 1.2 (third delivery)

| Item | Delivered | Verified by |
|---|---|---|
| One public website | `/properties` is the single public site; `/listings` redirects to it (301). Its visitor features moved over: sign-up and sign-in (`/properties/account`), wishlist hearts on every card, saved searches with daily email alerts (now matched against published listings, with links), viewing requests, and lease requests with a cheque payment plan on the listing page. Whole properties without units (a villa, a shop) can now be listed. New compare page (up to three listings). Upgrade patch keeps everything the old `/listings` showed. | 16 integration tests; browser walk-through (sign-up → save → save search → compare → viewing → lease request → account page); HTTP checks |
| Map view | Grid/map switch on `/properties` with every matching listing pinned (Leaflet, bundled; tile server configurable in RE Portal Settings), location map on listing pages, `map_points` API following the search filters. | Tests (filters, missing coordinates, no internal ids exposed); browser screenshots |
| Staff console | `/re-portal` rebuilt on the Estate design system (navy/teal tokens, line icons instead of emoji, local Inter font instead of Google Fonts, keyboard-reachable navigation, mobile layout with a menu button, right-to-left support). All console logic kept; its "+ New" button now works by screen id rather than English title text. | Browser screenshots at desktop and mobile width, no script errors |
| One AI provider | AI Settings holds the provider (Anthropic, OpenAI, Gemini, or any OpenAI-compatible endpoint), key, default and chat models, prices and one monthly budget shared by the website chat assistant and the voice CRM. Portal Chat Settings keeps only chat behaviour. Speech-to-text has its own key, so a non-OpenAI key is never sent to Whisper. Upgrade patch moves an existing chat key across. | 17 tests (shared config, shared budget, OpenAI vs Gemini payloads, speech key, upgrade patch) |
| Arabic | Every user-facing string (2,313) has Arabic: 2,066 in the app, the rest from thinkNXG Framework / ERP. Desk forms, the console and the website switch to right-to-left. Estate-specific meanings ("Property" = عقار on Estate forms) are scoped to Estate forms; generic mistranslations used on Estate screens ("Due Date", "Amount", "Bounced", "Draft"…) corrected. | Coverage test fails on any untranslated string; placeholder test; Arabic screenshots |
| Production | Assets built; deployed behind nginx with gunicorn, Socket.IO, scheduler and workers under supervisor; load-tested with 1,000 units: 300 concurrent users at 57 req/s, 95% under 320 ms, no errors (`LOAD_TEST.md`). Deployment guide (`DEPLOYMENT.md`). | 62 HTTP checks through nginx; load test |

Defects found and fixed in this round:

| # | Defect | Impact | Fix |
|---|---|---|---|
| D15 | Document numbering on upgraded sites: legacy records were numbered from per-prefix counters, but `format:` names in Framework 16 use one shared counter that started at zero | After an upgrade, creating a tenant, owner, property or unit failed with a duplicate name | Counter moved past every number in use, at upgrade and on every migrate |
| D16 | The voice layer and WhatsApp called `frappe.make_post_request` / `make_get_request`, removed in Framework 16 | Every AI call, transcription, WhatsApp send and voice-note download failed and was swallowed by error handling | Helper with timeouts; media kept as bytes |
| D17 | `nowdate` used without import in bulk PDC payment and purchase invoice creation | Those actions crashed when a date was left blank | Import added |
| D18 | A local variable shadowed the translation function in the voice confirmation handler | Confirm/cancel replies crashed | Renamed |
| D19 | Listing names came from titles | Two properties with the same name collided, and the error blocked saving the property | Unique names and routes |
| D20 | Each `/properties` page view counted against the 120/hour search API limit; the chat widget's per-page call was limited to 120/hour | Visitors paging results, or an office sharing one IP, would be locked out | Page views no longer count; public read limits 600/hour, chat settings 1,200/hour |
| D21 | Publishing a building and importing leads queued one background job per listing / lead | Large go-lives, the upgrade patch or a lead import hit the 700-job queue cap and failed | One reindex per bulk sync; imports skip per-lead scoring (nightly run covers them) |
| D22 | Visitors who signed up through the standard sign-up page could not save properties | Error: lead owner equals lead email | Lead created as Administrator |
| D23 | Legacy forms labelled column breaks "Col Break 1" etc. | Shown as headings on 29 forms | Labels removed |

## 12. Remaining work

| Area | Remaining |
|---|---|
| Live providers | WhatsApp, AI and speech calls were tested with mocked providers (request shape, logging, budgets). Live calls need the client's accounts and are part of user acceptance testing. |
| Map tiles | The default OpenStreetMap tile server suits light use; a busy public site should use a commercial or self-hosted tile service (setting in RE Portal Settings). |
| Load test scope | Measured on one 2 vCPU server with the load generator on the same machine; repeat on the client's production hardware before go-live (`scripts/load/`). |


## 13. Release 1.3 – public site redesign

The public `/properties` experience and the property page were rebuilt on the existing records, with no new frontend framework and no DocType renames.

**Schema (additive only).** `Listing.usage` and `Listing.development_status` (read-only, copied from the unit or property and kept in step by `portal/sync.py`; patch `v1_3.listing_facets` fills existing rows); `Saved Search.search_params` (the full filter set as JSON); search indexes on listing city, locality, price and publish date.

**Backend.** `portal/api/catalog.py` (cached counts, categories, facets, home data, translated filter chips, server-rendered result cards, suggestions); `portal/site.py` (header, footer, navigation and language context); `listing_query()` extends `build_filters()` with category, usage, development status, featured, new, permit, project, amenities (all selected), multi-value type/city/area/furnishing and map bounds. Existing endpoints and arguments are unchanged; saved searches without the new JSON keep working.

**Front end.** One design system (`portal.css`, `eb-*`/`pc-*`, logical properties for RTL), four small scripts, a Leaflet price-pin map (tiles configurable in RE Portal Settings), lightbox gallery, sticky inquiry card and mobile bar.

**Verification.** 85 integration tests (7 new) and the Arabic coverage test pass; the visitor browser flow (sign up, save, save search, compare, viewing, lease request, account) passes; desktop, mobile (390 px) and Arabic RTL pages show no horizontal overflow or console errors apart from blocked map tiles in the sandbox.

**Limits (data, not code).** Listings have no verified flag, so the site offers a "Permit on file" filter and badge instead (the hero text mentions verified listings as specified; review it before launch). There is no developer, possession date, agent or posted-by data, so New projects means properties under development and agents are not shown. Categories are the unit types in use (no plots, independent houses or "luxury"; Premium means highest priced). No image thumbnails are generated. Social links come from Website Settings footer items.

## 14. Release 1.3 – Portal Template & Theme Settings (admin CMS)

Administrators now change the look and layout of `/properties` from the desk, with no code. No DocType renames and no new frontend framework; schema changes are additive.

**New DocTypes.** `Portal Theme` (the design: template, colours, typography, shape, header, branding, home sections, listing layout, SEO, custom CSS; version history on), child tables `Portal Theme Section` and `Portal Theme Link`, and the single `Portal Theme Settings` (live theme, template gallery).

**Templates.** Classic Navy, Modern Light, Dark Luxury and Marketplace. One set of site templates serves all four; they differ by CSS variables and layout attributes (hero, card style, columns, filter placement, default view, detail layout), so ordinary edits never need a developer.

**Draft, preview, publish.** Edits are drafts. Publishing stores a snapshot, which is what visitors see; the previous snapshot is kept so a theme can be reverted. `?theme_preview=NAME` (remembered by a cookie) shows a draft to RE Manager and System Manager only, with a banner and exit link. The live theme cannot be deleted.

**Safeguards.** Colours must be valid hex; text and button contrast is checked on save (unreadable combinations are rejected, weak ones warn); link URLs are restricted; custom CSS (System Manager only) may not use `@import`, external `url()`, scripts or HTML.

**Admin UI.** The theme form has Preview (page picker and device width), Publish, Duplicate, Apply Template and Revert. Theme Settings lists themes and templates and creates a theme from a template.

**APIs** (`portal/api/theme_admin.py`, RE Manager / System Manager): `templates`, `gallery`, `create_from_template`, `apply_template`, `duplicate`, `publish`, `revert`, `preview_links`. Public endpoints are unchanged.

**Upgrade.** Patch `v1_3.portal_themes` and `after_migrate` create one theme per template and publish Classic Navy, which matches the previous look.

**Verification.** 97 integration tests (12 new in `test_portal_themes.py`) and the Arabic coverage test pass; all four templates render home, results, list, map and property pages with no horizontal overflow at 1366 px and 390 px.

**Limits.** Admin-entered text is translated only through the Translation DocType. No export/import or scheduled publishing. The transparent header is non-sticky and applies on pages with a hero. Compare and map toggles are applied in CSS. Fonts are system or bundled only. Trust-section wording is fixed text.
