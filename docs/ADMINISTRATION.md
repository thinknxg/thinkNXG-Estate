# thinkNXG Estate — Administration Guide

## 1. Requirements

- thinkNXG Framework v16 and thinkNXG ERP v16 (Python 3.14, Node 24, MariaDB 10.6 or later, Redis)
- A completed thinkNXG ERP setup wizard (company, fiscal year, chart of accounts)

## 2. Install

```bash
bench get-app <thinkNXG Estate repository URL> --branch version-16
bench --site SITE install-app thinknxg_estate
bench --site SITE migrate
bench build --app thinknxg_estate
bench restart
```

Sites already running `re_core`, `re_crm`, `re_portal` or `re_voice`: follow `MIGRATION.md`.

Check the result with:

```bash
bench --site SITE execute thinknxg_estate.tests.verify_install.run
```

## 3. Configure

Work through these in order. All are under **thinkNXG Estate → Settings** in the sidebar.

| Settings | What to set |
|---|---|
| **Property Settings** | Rent Item (created automatically as *Rental Charge*), invoice lead days, overdue grace days, auto-create PDCs, Deposits Held liability account and deposit bank account, lease expiry flag days and renewal ToDo days, tenant welcome email, *Enable Access-Code Tenant Portal* (off by default), *Allow Tenants to Terminate Leases Online* (off by default) |
| **RE CRM Settings** | Auto-assign leads (round robin over agents in the assignment pool), first-contact SLA minutes and escalation user, *Sales Agents See Only Their Own Leads* (on by default), booking fee / commission expense / commission payable accounts (needed for journal entries), WhatsApp auto-replies and reminders, rent reminder days, *Recommend Properties When a Lead Is Qualified* (on by default) and whether to also send them on WhatsApp |
| **RE Portal Settings** | Portal title and tagline (also used as the sender name in visitor emails), contact WhatsApp and email, currency label, page size, hourly inquiry limit, map tile server and attribution, default map centre and zoom |
| **Listing Feed Settings** | Only with a valid brokerage licence and signed portal agreements: tick the confirmation, set a long random feed token, enable Property Finder and/or Bayut and the agent details. Listings appear in a feed only when opted in and carrying a permit number. |
| **Portal Chat Settings** | Turn the website chat assistant on, per-chat message cap, extra instructions. Its AI provider, key, model and budget come from **AI Settings**. |
| **WhatsApp Settings** | Meta Cloud API phone number ID, access token, default country code (`+968` for Oman), API version |
| **AI Settings** | The one AI provider for the chat assistant and the voice CRM: provider (Anthropic, OpenAI, Gemini, or Custom for any OpenAI-compatible endpoint), API key, default model and optional chat model, prices per million tokens, and one monthly budget covering both. Also: *Use AI in the Voice CRM*, voice processing, speech-to-text provider with its own Speech API Key (needed for OpenAI Whisper unless the provider is OpenAI), translation / sentiment / summary / scoring switches, audio and transcript retention days |
| **WhatsApp Template** | One approved Meta template per purpose (Lead Welcome, Visit Reminder, Reservation Expiry, Rent Reminder, Property Recommendations, Post Visit Feedback, Follow Up). Variables are filled in this order: Lead Welcome (name); Visit Reminder (unit, date/time); Reservation Expiry (reservation, expiry date); Rent Reminder (tenant, amount, due date); Property Recommendations (name, list of units). |
| **Lead Score Model** | Weights for budget fit, conversation frequency, site visits, response speed and loan requirement; hot and warm thresholds |
| **Voice Locale Profile** | Two are seeded (GCC English/Arabic, India Malayalam/English); sets number system, unit vocabulary and time zone |

Taxes and currency come from thinkNXG ERP: set up the 5% Oman VAT (or other jurisdiction)
Item Tax Templates and select them on Lease Charges. Amounts follow the company currency
(OMR uses 3 decimals).

### WhatsApp messages and the 24-hour rule

Every business message goes through one channel and is logged in **WhatsApp Message Log**
against its record. Meta allows free text only within 24 hours of the customer's last message;
outside that window the channel sends the approved template for the message's purpose. If there
is none, the message is logged as *Skipped* with the reason, so you can see which templates to
register.

### WhatsApp webhook

Add to `site_config.json` (the webhook refuses all traffic without the secret):

```json
{ "whatsapp_app_secret": "<Meta app secret>", "whatsapp_verify_token": "<long random string>" }
```

Callback URL to register with Meta: `https://SITE/api/method/thinknxg_estate.voice.api.webhook.webhook`.
(Existing registrations on `re_voice.api.webhook.webhook` keep working.)

On each **RE Agent** set the WhatsApp number and tick *Voice Commands Enabled*. A number that
does not match an active, voice-enabled agent is treated as a customer and can never run a
command.

## 4. Roles and access

| Role | Typical user | Main access |
|---|---|---|
| System Manager | System administrator | Everything |
| RE Manager | Head of property / company administrator (restrict to one company with a User Permission on Company) | Everything in the app, including delete, cancel and amend |
| Property Manager | Property manager | Properties, units, owners, leases, maintenance; read on cheques, deposits and owner statements |
| Leasing Manager | Leasing manager | Leasing Officer access plus cancel, amend and delete leases and inspections; reservations; read on rent schedules, cheques and deposits |
| Leasing Officer | Leasing executive | Tenants and leases (create, submit), listings; read on units |
| Accounts User / Accounts Manager (thinkNXG ERP) | Accountant | Rent schedules, cheques, deposits, owner statements, commission entries, invoices and payments |
| Maintenance Supervisor | Maintenance manager | Maintenance requests and jobs; read on properties and units |
| Maintenance Technician | Technician | Read properties and units; update maintenance requests and jobs (no submit) |
| RE Sales Manager | CRM manager | All leads, deals, agents, commissions |
| RE Sales Agent | Sales agent | Their own leads, deals and site visits (see *Sales Agents See Only Their Own Leads*); lead matching; own commission statement |
| Broker | External broker | Same as RE Sales Agent; record the brokerage, licence and agreement on the RE Agent (*Agent Type: External Broker*) |
| Receptionist | Front desk | Create leads, enquiries, visit requests and maintenance requests; read properties, units, listings and tenants |
| Voice Ops Manager | Communications lead | Voice, AI and WhatsApp configuration (settings, templates, commands, locales, scoring model); read on all message and voice logs |
| Property Owner | Landlord (website user) | Owner portal only: their properties, units, leases, income, expenses, statements and maintenance |
| Tenant | Tenant (website user) | Own tenant record, leases, rent schedule, cheques, deposit and maintenance requests only; can raise maintenance requests |

Portfolio-wide screens (the `/re-portal` console, the thinkNXG Estate Dashboard page and the
console APIs) are for System Manager, RE Manager, Property Manager, Leasing Manager, Leasing
Officer, Maintenance Supervisor, RE Sales Manager, Voice Ops Manager and the Accounts roles.
Sales agents, brokers, receptionists and technicians work in the desk forms, where document
permissions and ownership rules apply.

Rules enforced on the server, whatever the screen shows:

- Staff APIs and the `/re-portal` console require a desk user with one of the staff roles
  above (or System Manager).
- Tenants only ever see their own records (permission query conditions on Tenant, Lease
  Contract, Rent Schedule, Post Dated Cheque, Security Deposit and Maintenance Request).
- Money and status actions need more than read access: depositing, clearing or bouncing a
  cheque, refunding a deposit and marking a commission paid need *submit* permission;
  terminating a lease, raising a job from a request and converting a lead need *write*.
- Sales agents and brokers see the leads, deals and site visits assigned to their RE Agent
  record (switch off in RE CRM Settings). Each agent's RE Agent record must have their user.
- Multi-company: restrict staff to their landlord companies with User Permissions on
  **Company** (each landlord can be its own company).

Tenant portal users are created automatically when *Enable Portal* is ticked on a Tenant with
an email address (role Tenant, website user, login at `/tenant-portal`). Owner portal users are
created the same way from *Enable Owner Portal* on a Property Owner (role Property Owner, login
at `/owner-portal`).

## 5. Web pages

| URL | Audience |
|---|---|
| `/properties` | Public site: home page (search, categories, featured, locations, new projects, premium), filtered search with grid, list and map views, wishlist, compare and saved-search alerts (`/listings` redirects here). English and Arabic with RTL. Sections with no data are hidden. |
| `/property/<route>` | Listing page: photos, location map, payment plan, enquiry, viewing request, lease request for signed-in visitors |
| `/properties/account` | Visitor sign-in / sign-up, saved properties, saved searches, enquiries, viewings and lease requests |
| `/properties/compare` | Up to three listings side by side |
| `/contact` | Contact page |
| `/tenant-portal` (+ `/lease`, `/payments`, `/maintenance`) | Tenants (website login) |
| `/tenant-self-service` | Tenants with an access code; only when enabled in Property Settings |
| `/owner-portal` | Property owners (website login) |
| `/re-portal` | Staff console (portfolio-wide roles) |
| `/app/estate-dashboard` | Dashboard with company, property, city and period filters |
| `/app/thinknxg-estate` | Desk dashboard and sidebar |

## 6. Scheduled jobs

| Frequency | Job |
|---|---|
| Hourly | Lead SLA escalation; site-visit WhatsApp reminders; post-visit feedback prompts |
| Daily | Invoice due rent installments; transcript retention purge; mark overdue installments; lease expiry pipeline (Expiring flag, renewal ToDos); PDC deposit reminders; document expiry alerts; release expired reservations; rent-due WhatsApp reminders; saved-search alerts; listing publication backfill; nightly lead scoring; thread summaries; audio retention purge; AI spend refresh |
| Monthly | Owner statements |

The scheduler must be enabled: `bench --site SITE enable-scheduler`.

## 6a. Reports

Finance: Rent Roll, Outstanding Rent, Rent Collection, PDC Status, Owner Statement, Deposit
Register, Property Profitability. Leasing: Lease Expiry, Tenant Register. Property: Property
Register, Unit Availability. CRM: Agent Leaderboard (with targets), Lead Source Analysis, Site
Visit Conversion, Broker Commission Statement. Maintenance: Maintenance Overview, Vendor
Performance. Voice: Voice Command Analytics. All export to Excel, CSV and PDF from the report
menu.

## 7. Production deployment

See `DEPLOYMENT.md` for the full procedure (server sizing, nginx and supervisor, HTTPS,
load balancers, workers, upgrades and rollback) and `LOAD_TEST.md` for measured capacity.

## 7a. Languages

English and Arabic are included. A user's language (User → Language) sets the desk, the staff
console at `/re-portal` and the website pages they see when signed in; Arabic switches all of
them to right-to-left. Visitors who are not signed in can choose a language in the website
footer if *Website Settings → Show Language Picker* is on.

Translations live in `thinknxg_estate/locale/ar.po`. After changing user-facing text:

```bash
bench generate-pot-file --app thinknxg_estate
bench update-po-files --app thinknxg_estate --locale ar
# translate the new entries in ar.po, then
bench compile-po-to-mo --app thinknxg_estate --locale ar
```

The test `tests/test_translations.py` fails if any string has no Arabic translation.

## 8. Backup and recovery

- Schedule automatic backups (`bench setup backups` adds a cron job; thinkNXG Cloud backs up sites automatically). Keep at least 7 days and copy them off the server.
- Before every update or migration: `bench --site SITE backup --with-files`.
- Restore: `bench --site SITE restore <database.sql.gz> --with-public-files <files.tar> --with-private-files <private-files.tar>`, then `bench --site SITE migrate`.
- Private files hold tenant KYC documents, signed contracts and inspection photos; include them
  in every backup.
- Audio from voice notes is purged after *AI Settings → Audio Retention Days*; transcripts
  are kept.

## 9. Tests

```bash
bench --site TEST_SITE set-config allow_tests true
bench --site TEST_SITE run-tests --app thinknxg_estate
python3 -m pytest thinknxg_estate/tests/unit
```

The test site needs a completed setup wizard (a company and fiscal year).

## 10. Support

Support: https://thinknxg.com/thinkdesk · Sales: sales@kreatao.com · Community: discuss.thinknxg.com
