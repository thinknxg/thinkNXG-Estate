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
| **RE CRM Settings** | Auto-assign leads (round robin over agents in the assignment pool), first-contact SLA minutes and escalation user, booking fee / commission expense / commission payable accounts (needed for journal entries), WhatsApp auto-replies and reminders, rent reminder days |
| **RE Portal Settings** | Portal title and tagline (also used as the sender name in visitor emails), contact WhatsApp and email, currency label, page size, hourly inquiry limit |
| **Listing Feed Settings** | Only with a valid brokerage licence and signed portal agreements: tick the confirmation, set a long random feed token, enable Property Finder and/or Bayut and the agent details. Listings appear in a feed only when opted in and carrying a permit number. |
| **Portal Chat Settings** | Listings chatbot provider (Anthropic or Gemini), API key, model, per-chat message cap, monthly budget |
| **WhatsApp Settings** | Meta Cloud API phone number ID, access token, default country code (`+968` for Oman), API version |
| **AI Settings** | Voice processing, ASR and LLM providers, monthly AI budget, translation / sentiment / summary / scoring switches, audio retention days |
| **Lead Score Model** | Weights for budget fit, conversation frequency, site visits, response speed and loan requirement; hot and warm thresholds |
| **Voice Locale Profile** | Two are seeded (GCC English/Arabic, India Malayalam/English); sets number system, unit vocabulary and time zone |

Taxes and currency come from thinkNXG ERP: set up the 5% Oman VAT (or other jurisdiction)
Item Tax Templates and select them on Lease Charges. Amounts follow the company currency
(OMR uses 3 decimals).

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
| RE Manager | Head of property / company administrator | Everything in the app, including delete, cancel and amend |
| Property Manager | Property manager | Properties, units, owners, leases, maintenance; read on cheques and deposits |
| Leasing Officer | Leasing executive | Tenants and leases (create, submit), listings; read on units |
| Maintenance Supervisor | Maintenance manager / technician lead | Maintenance requests and jobs; read on properties and units |
| Accounts User / Accounts Manager (thinkNXG ERP) | Accountant | Rent schedules, cheques, deposits, commission entries, invoices and payments |
| RE Sales Manager | CRM manager | Leads, deals, agents, commissions |
| RE Sales Agent | Sales agent / broker | Leads and deals (create and edit); read on commission entries and voice logs |
| Voice Ops Manager | Communications lead | Voice, AI and WhatsApp configuration (settings, templates, commands, locales, scoring model); read on all message and voice logs |
| Tenant | Tenant (website user) | Own tenant record, leases, rent schedule, cheques, deposit and maintenance requests only; can raise maintenance requests |

Rules enforced on the server, whatever the screen shows:

- Staff APIs and the `/re-portal` console require a desk user with one of the staff roles
  above (or System Manager).
- Tenants only ever see their own records (permission query conditions on Tenant, Lease
  Contract, Rent Schedule, Post Dated Cheque, Security Deposit and Maintenance Request).
- Money and status actions need more than read access: depositing, clearing or bouncing a
  cheque, refunding a deposit and marking a commission paid need *submit* permission;
  terminating a lease, raising a job from a request and converting a lead need *write*.
- Agents currently see all leads and deals; to limit an agent to their own, add a User Permission
  on **RE Agent** for that user (row-level lead ownership is planned work).
- Multi-company: restrict staff to their landlord companies with User Permissions on
  **Company** (each landlord can be its own company).

Tenant portal users are created automatically when *Enable Portal* is ticked on a Tenant with
an email address (role Tenant, website user, login at `/tenant-portal`).

## 5. Web pages

| URL | Audience |
|---|---|
| `/properties`, `/property/<route>`, `/contact` | Public listing search and listing pages |
| `/listings` | Public listings app with visitor accounts, wishlist, saved searches, visit and lease requests |
| `/tenant-portal` (+ `/lease`, `/payments`, `/maintenance`) | Tenants (website login) |
| `/tenant-self-service` | Tenants with an access code; only when enabled in Property Settings |
| `/re-portal` | Staff console |
| `/app/thinknxg-estate` | Desk dashboard and sidebar |

## 6. Scheduled jobs

| Frequency | Job |
|---|---|
| Hourly | Lead SLA escalation; site-visit WhatsApp reminders; post-visit feedback prompts |
| Daily | Invoice due rent installments; mark overdue installments; lease expiry pipeline (Expiring flag, renewal ToDos); PDC deposit reminders; document expiry alerts; release expired reservations; rent-due WhatsApp reminders; saved-search alerts; listing publication backfill; nightly lead scoring; thread summaries; audio retention purge; monthly AI spend reset |
| Monthly | Owner statements |

The scheduler must be enabled: `bench --site SITE enable-scheduler`.

## 7. Production deployment

1. `bench setup production <user>` (nginx + supervisor), or deploy on thinkNXG Cloud.
2. HTTPS on the site domain (`bench setup lets-encrypt SITE`); the WhatsApp webhook needs it.
3. Turn developer mode off on production sites.
4. Workers: at least one `short` and one `long` queue worker (webhook processing uses
   `short`, lead scoring uses `long`).
5. Outbound HTTPS to `graph.facebook.com` (WhatsApp) and to the configured ASR / LLM / chatbot
   providers.
6. Run `bench --site SITE migrate` after every app update.

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
