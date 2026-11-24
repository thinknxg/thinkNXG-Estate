# One-time consolidation scripts (kept for audit)

These produced thinkNXG Estate from the four legacy repositories (re_core `0ee6d04`,
re_crm `99a5382`, RE-Portal `f463988`, RE-Voice `3a8ffbc`). They are not part of the app
and are not needed to install or run it.

| Script | Purpose |
|---|---|
| `consolidate.py` | Copies every legacy file into the unified layout; rewrites imports, method paths, asset URLs and module names; emits the legacy method map (`compat.py`) |
| `fold_custom_fields.py` | Turns legacy Custom Fields / Property Setters on the platform's own DocTypes into standard fields |
| `add_fields.py` | Schema additions made during consolidation (CRM lead links, enquiry contact fields, tenant-portal settings) |
| `build_navigation.py` | Unified workspaces, KPI cards, v16 Sidebar and desktop icon |
| `upgrade_rehearsal.sh` | Restores a legacy-site backup and runs the upgrade, comparing row counts and checking legacy code stays untouched |
| `smoke.sh` | HTTP checks (guest, staff, tenant, legacy URLs, webhook, feeds, pages) against a running server |

After the scripts ran, the code was edited by hand (security and defect fixes); see
`docs/INTEGRATION_REPORT.md`.
