# Upgrading from re_core / re_crm / re_portal / re_voice

The upgrade is in place. DocType names and tables do not change, so leases, invoices, cheques,
leads, listings and voice logs stay exactly where they are. The upgrade changes ownership
(app and module), navigation, a few stored code paths, and links portal records to the CRM.

## Before you start

1. Upgrade the site to the latest legacy commits and run `bench --site SITE migrate`.
2. Take a full backup and copy it off the server:
   ```bash
   bench --site SITE backup --with-files
   ```
3. Rehearse on a copy of the site first (restore the backup into a staging site).

## Upgrade

```bash
bench get-app <thinkNXG Estate repository URL> --branch version-16
bench --site SITE install-app thinknxg_estate
bench --site SITE migrate
bench build --app thinknxg_estate
bench restart
```

`install-app` detects the legacy apps and prints a summary like this:

```
thinkNXG Estate: legacy apps detected ['re_voice', 're_portal', 're_crm', 're_core']; 31 custom fields and 2 property setters are now standard
thinkNXG Estate legacy migration:
  voice_handlers_rewritten: 24
  portal_records_linked_to_crm: 10
  access_code_portal: kept enabled
  legacy_navigation_removed: [...]
  legacy_scheduled_jobs_removed: 17
  legacy_apps_detached: ['re_voice', 're_portal', 're_crm', 're_core']
  legacy_module_defs_removed: ['RE Core', 'RE CRM', 'RE Portal', 'RE Voice']
```

When every site on the bench is upgraded, remove the legacy code:

```bash
bench remove-app re_voice && bench remove-app re_portal && bench remove-app re_crm && bench remove-app re_core
```

**Never run `bench uninstall-app` on the legacy apps.** Uninstalling deletes the DocTypes of
the app's modules, and with them the data. The installer detaches the apps from the site's
installed-apps list without uninstalling them.

## What the upgrade changes

| Before schema sync | Custom Field and Property Setter records that are now standard fields of the unified DocTypes are deleted. Columns and values stay. |
|---|---|
| Schema sync | All DocTypes, reports, cards and charts are re-homed in the Estate modules. |
| Voice commands | Stored handler paths `re_voice.*` become `thinknxg_estate.voice.*`. |
| CRM links | Property Enquiry, Site Visit Booking, Saved Search and Property Wishlist records that point at an ERPNext Lead get a link to the visitor's RE Lead (an existing one is reused, matched on mobile, then email). |
| Access-code portal | Turned on in Property Settings if any tenant has an access code; otherwise off. |
| Navigation | Legacy workspaces (RE Core, Property Operations, RE Finance, RE Maintenance, RE CRM, RE Portal, Voice CRM), the RE Core sidebar and desktop icon are removed; the thinkNXG Estate sidebar and workspaces replace them. User-created workspaces are not touched. |
| Scheduler | Scheduled Job Types pointing at `re_*` code are removed; thinkNXG Estate registers its own. |
| Apps | The four apps are removed from the site's installed apps; their Module Defs are removed once nothing references them. |

All steps are idempotent. Legacy navigation is deleted at database level, so in developer
mode no exported JSON is removed from the legacy apps' folders.

## Behaviour changes to tell users about

- **Tenants can no longer record payments** in the access-code portal (they could post a
  Payment Entry on their own word). Payments are recorded by staff; the portal shows how to pay.
- **Lease termination from the tenant portal is a request** to the leasing team unless
  *Property Settings → Allow Tenants to Terminate Leases Online* is turned on.
- **Staff APIs require a staff role.** Desk users need one of RE Manager, Property Manager,
  Leasing Officer, Maintenance Supervisor, RE Sales Manager, RE Sales Agent, Voice Ops Manager,
  Accounts User, Accounts Manager or System Manager. Website users are refused.
- **Cheque, deposit and commission actions** (deposit, clear, bounce, refund, mark paid) need
  submit permission on the document; terminate, make job and make deal need write permission.
- **Access-code sessions are invalidated** once: only token hashes are stored now, so tenants
  using `/tenant-self-service` sign in again.
- `/tenant-self-service` redirects to `/tenant-portal` when the access-code portal is off.
- **Sales agents and brokers see only their own leads, deals and site visits** (RE CRM Settings
  → *Sales Agents See Only Their Own Leads*, on by default). Make sure each RE Agent record has its
  user, or turn the setting off to keep the old behaviour.
- **The staff console (`/re-portal`) and dashboard are for portfolio-wide roles.** Sales agents
  work in the desk forms (Leads, Deals, Site Visits), where lead matching and communication
  history are available.
- **Lease terms are counted correctly.** A lease from 24 Nov to 24 Nov the next year is now 12
  months (it was 13, giving 13 monthly installments and 13/12 of the annual rent in generated
  charges). Submitted leases and existing rent schedules are not changed; check draft leases
  created before the upgrade.
- **WhatsApp business messages outside Meta's 24-hour window need an approved template.**
  Messages without one are logged as *Skipped* with the reason (they used to be attempted and
  rejected by Meta). Register templates under WhatsApp Template with a purpose.

## Integrations keep working

No re-registration is needed. Old URLs route to the new code:

- Meta WhatsApp webhook: `/api/method/re_voice.api.webhook.webhook` (and `.receive`, `.verify`)
- Property Finder / Bayut feeds: `/api/method/re_portal.api.feeds.property_finder|bayut?token=...`
- Every other `re_core.*`, `re_crm.*`, `re_portal.*`, `re_voice.*` module-level endpoint
  (170 in total, see `API.md`)

New registrations should use the `thinknxg_estate.*` paths.

## Verify

```bash
bench --site SITE execute thinknxg_estate.tests.verify_install.run
```

Expect: installed apps `frappe, erpnext, thinknxg_estate`; 68 DocTypes across the Estate
modules; `legacy_module_defs`, `legacy_scheduled_jobs` and `duplicate_standard_custom_fields`
empty; `voice_handlers_resolvable: true`.

For a before/after data comparison on a staging copy, run this after `bench get-app` and
before `install-app`, then again after the upgrade, and compare the two files:

```bash
echo "from thinknxg_estate.tests.data_snapshot import run; run('/tmp/before.json')" | bench --site SITE console
```

## Roll back

The upgrade does not change business data, but rollback is a database restore, never an
uninstall:

```bash
bench --site SITE restore /path/to/backup-database.sql.gz --with-public-files ... --with-private-files ...
bench --site SITE migrate
```

Keep the legacy apps on the bench until the upgraded site has run through at least one
billing cycle; `bench remove-app` is the last step.

## Upgrading to 1.2

Applies both to legacy sites (done by the installer) and to sites already on thinkNXG Estate 1.0
or 1.1 (done by `bench migrate`):

- **One public website.** `/listings` redirects to `/properties`. Units that the old `/listings`
  page showed are marked *Published to Portal*, so nothing visible disappears; whole properties
  without units get their own listing. Visitor accounts, wishlists and saved searches carry over.
- **One AI provider.** If only the website chat had an API key, it moves to *AI Settings*. If both
  had keys, *AI Settings* wins and a comment on *Portal Chat Settings* records it. Budgets are
  added together. The old chat fields stay in the database (hidden) for rollback.
- **Document numbering.** The shared `format:` naming counter is moved past every number in use,
  so new tenants, owners, properties and units no longer clash with migrated records. It only
  ever moves forward.
- **Arabic.** Users with language *Arabic* see the desk, console and website in Arabic, right to
  left. Nothing to configure.

Rollback is the same as for any update: restore the backup taken before `migrate`.
