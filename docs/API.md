# thinkNXG Estate API reference

Generated from the code by `scripts/generate_api_docs.py`. Call any endpoint at
`/api/method/<path>` with a session cookie (and the `X-Frappe-CSRF-Token` header for POST),
or with token authentication (`Authorization: token <api_key>:<api_secret>`).

Access levels:

- **Estate staff**: desk (System User) accounts holding one of RE Manager, Property Manager,
  Leasing Officer, Maintenance Supervisor, RE Sales Manager, RE Sales Agent, Voice Ops Manager,
  Accounts User, Accounts Manager or System Manager. Document permissions still apply on top.
- **Public (guest)**: no login; every write is rate limited per IP.
- **Logged-in user**: identity is resolved server-side from the session (tenant portal, visitor
  account); IDs sent by the client are never trusted.

Legacy aliases: every `re_core.*`, `re_crm.*`, `re_portal.*` and `re_voice.*` path keeps working
and routes to the endpoint shown, so existing scripts, the Meta webhook registration and
portal feed registrations need no change.

Document actions (`run_doc_method`) such as *Post Dated Cheque → mark_cleared* check the
matching document permission (submit or write), not only read.

## Staff console API (desk users with an estate or accounts role)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.core.api.get_properties_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_properties_list` |
| `thinknxg_estate.core.api.get_sidebar_counts` | Estate staff | GET/POST | — | `re_core.re_core.api.get_sidebar_counts` |
| `thinknxg_estate.core.api.mark_notifications_read` | Estate staff | POST only | — | `re_core.re_core.api.mark_notifications_read` |
| `thinknxg_estate.core.api.get_notifications` | Estate staff | GET/POST | — | `re_core.re_core.api.get_notifications` |
| `thinknxg_estate.core.api.get_dashboard_stats` | Estate staff | GET/POST | — | `re_core.re_core.api.get_dashboard_stats` |
| `thinknxg_estate.core.api.get_units_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_units_list` |
| `thinknxg_estate.core.api.get_units_for_dropdown` | Estate staff | GET/POST | — | `re_core.re_core.api.get_units_for_dropdown` |
| `thinknxg_estate.core.api.global_search` | Estate staff | GET/POST | — | `re_core.re_core.api.global_search` |
| `thinknxg_estate.core.api.get_tenants_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_tenants_list` |
| `thinknxg_estate.core.api.get_portal_tenants_list` | Estate staff | GET/POST | Tenant profiles auto-created from portal signups (via lease requests), | `re_core.re_core.api.get_portal_tenants_list` |
| `thinknxg_estate.core.api.get_lease_form_options` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_form_options` |
| `thinknxg_estate.core.api.get_units_for_property` | Estate staff | GET/POST | — | `re_core.re_core.api.get_units_for_property` |
| `thinknxg_estate.core.api.compute_charge_term_total` | Estate staff | GET/POST | Convert a per-period charge amount into a lease-term total, for live | `re_core.re_core.api.compute_charge_term_total` |
| `thinknxg_estate.core.api.get_lease_term_charges_preview` | Estate staff | GET/POST | Preview what Lease Contract charges would auto-populate from the | `re_core.re_core.api.get_lease_term_charges_preview` |
| `thinknxg_estate.core.api.create_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.create_lease_contract` |
| `thinknxg_estate.core.api.submit_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.submit_lease_contract` |
| `thinknxg_estate.core.api.get_invoices_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_invoices_list` |
| `thinknxg_estate.core.api.delete_invoice` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_invoice` |
| `thinknxg_estate.core.api.get_compliance_status` | Estate staff | GET/POST | — | `re_core.re_core.api.get_compliance_status` |
| `thinknxg_estate.core.api.get_crm_pipeline` | Estate staff | GET/POST | — | `re_core.re_core.api.get_crm_pipeline` |
| `thinknxg_estate.core.api.get_viewings_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_viewings_list` |
| `thinknxg_estate.core.api.get_portal_listings` | Public (guest) | GET/POST | — | `re_core.re_core.api.get_portal_listings` |
| `thinknxg_estate.core.api.get_maintenance_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_maintenance_list` |
| `thinknxg_estate.core.api.get_property_detail` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_detail` |
| `thinknxg_estate.core.api.get_property_documents` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_documents` |
| `thinknxg_estate.core.api.create_property_document` | Estate staff | GET/POST | — | `re_core.re_core.api.create_property_document` |
| `thinknxg_estate.core.api.delete_property_document` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_property_document` |
| `thinknxg_estate.core.api.set_unit_portal_publish` | Estate staff | GET/POST | — | `re_core.re_core.api.set_unit_portal_publish` |
| `thinknxg_estate.core.api.set_property_portal_publish` | Estate staff | GET/POST | — | `re_core.re_core.api.set_property_portal_publish` |
| `thinknxg_estate.core.api.get_property_financials` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_financials` |
| `thinknxg_estate.core.api.get_pdc_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_pdc_list` |
| `thinknxg_estate.core.api.get_bank_accounts` | Estate staff | GET/POST | — | `re_core.re_core.api.get_bank_accounts` |
| `thinknxg_estate.core.api.get_modes_of_payment` | Estate staff | GET/POST | — | `re_core.re_core.api.get_modes_of_payment` |
| `thinknxg_estate.core.api.update_pdc_status` | Estate staff | GET/POST | — | `re_core.re_core.api.update_pdc_status` |
| `thinknxg_estate.core.api.delete_pdc` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_pdc` |
| `thinknxg_estate.core.api.get_rent_schedule` | Estate staff | GET/POST | — | `re_core.re_core.api.get_rent_schedule` |
| `thinknxg_estate.core.api.get_rent_schedule_detail` | Estate staff | GET/POST | — | `re_core.re_core.api.get_rent_schedule_detail` |
| `thinknxg_estate.core.api.get_security_deposits` | Estate staff | GET/POST | — | `re_core.re_core.api.get_security_deposits` |
| `thinknxg_estate.core.api.update_security_deposit` | Estate staff | GET/POST | — | `re_core.re_core.api.update_security_deposit` |
| `thinknxg_estate.core.api.delete_security_deposit` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_security_deposit` |
| `thinknxg_estate.core.api.get_lease_charges` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_charges` |
| `thinknxg_estate.core.api.add_lease_charge` | Estate staff | GET/POST | — | `re_core.re_core.api.add_lease_charge` |
| `thinknxg_estate.core.api.get_property_photos` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_photos` |
| `thinknxg_estate.core.api.add_property_photo` | Estate staff | GET/POST | — | `re_core.re_core.api.add_property_photo` |
| `thinknxg_estate.core.api.set_cover_photo` | Estate staff | GET/POST | — | `re_core.re_core.api.set_cover_photo` |
| `thinknxg_estate.core.api.delete_property_photo` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_property_photo` |
| `thinknxg_estate.core.api.get_amenities` | Estate staff | GET/POST | — | `re_core.re_core.api.get_amenities` |
| `thinknxg_estate.core.api.get_property_amenities` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_amenities` |
| `thinknxg_estate.core.api.set_property_amenities` | Estate staff | GET/POST | — | `re_core.re_core.api.set_property_amenities` |
| `thinknxg_estate.core.api.get_utility_accounts` | Estate staff | GET/POST | — | `re_core.re_core.api.get_utility_accounts` |
| `thinknxg_estate.core.api.add_utility_account` | Estate staff | GET/POST | — | `re_core.re_core.api.add_utility_account` |
| `thinknxg_estate.core.api.update_utility_account` | Estate staff | GET/POST | — | `re_core.re_core.api.update_utility_account` |
| `thinknxg_estate.core.api.get_tenant_kyc_documents` | Estate staff | GET/POST | — | `re_core.re_core.api.get_tenant_kyc_documents` |
| `thinknxg_estate.core.api.add_tenant_kyc_document` | Estate staff | GET/POST | — | `re_core.re_core.api.add_tenant_kyc_document` |
| `thinknxg_estate.core.api.delete_tenant_kyc_document` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_tenant_kyc_document` |
| `thinknxg_estate.core.api.get_inspections` | Estate staff | GET/POST | — | `re_core.re_core.api.get_inspections` |
| `thinknxg_estate.core.api.get_inspection_detail` | Estate staff | GET/POST | — | `re_core.re_core.api.get_inspection_detail` |
| `thinknxg_estate.core.api.create_inspection` | Estate staff | GET/POST | — | `re_core.re_core.api.create_inspection` |
| `thinknxg_estate.core.api.update_inspection` | Estate staff | GET/POST | — | `re_core.re_core.api.update_inspection` |
| `thinknxg_estate.core.api.terminate_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.terminate_lease_contract` |
| `thinknxg_estate.core.api.get_lease_outstanding_rent` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_outstanding_rent` |
| `thinknxg_estate.core.api.get_lease_request_detail` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_request_detail` |
| `thinknxg_estate.core.api.update_lease_request` | Estate staff | GET/POST | — | `re_core.re_core.api.update_lease_request` |
| `thinknxg_estate.core.api.reject_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.reject_lease_contract` |
| `thinknxg_estate.core.api.get_property_enquiries_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_enquiries_list` |
| `thinknxg_estate.core.api.update_property_enquiry` | Estate staff | GET/POST | — | `re_core.re_core.api.update_property_enquiry` |
| `thinknxg_estate.core.api.get_site_visit_bookings_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_site_visit_bookings_list` |
| `thinknxg_estate.core.api.update_site_visit_booking` | Estate staff | GET/POST | — | `re_core.re_core.api.update_site_visit_booking` |
| `thinknxg_estate.core.api.get_lease_contracts_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_contracts_list` |
| `thinknxg_estate.core.api.get_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_contract` |
| `thinknxg_estate.core.api.update_lease_contract` | Estate staff | GET/POST | — | `re_core.re_core.api.update_lease_contract` |
| `thinknxg_estate.core.api.get_pdc_suggested_amount` | Estate staff | GET/POST | — | `re_core.re_core.api.get_pdc_suggested_amount` |
| `thinknxg_estate.core.api.get_lease_installments` | Estate staff | GET/POST | — | `re_core.re_core.api.get_lease_installments` |
| `thinknxg_estate.core.api.link_pdc_to_installment` | Estate staff | GET/POST | — | `re_core.re_core.api.link_pdc_to_installment` |
| `thinknxg_estate.core.api.create_pdc` | Estate staff | GET/POST | — | `re_core.re_core.api.create_pdc` |
| `thinknxg_estate.core.api.create_rent_schedule` | Estate staff | GET/POST | — | `re_core.re_core.api.create_rent_schedule` |
| `thinknxg_estate.core.api.update_installment_status` | Estate staff | GET/POST | — | `re_core.re_core.api.update_installment_status` |
| `thinknxg_estate.core.api.update_rent_schedule_status` | Estate staff | GET/POST | — | `re_core.re_core.api.update_rent_schedule_status` |
| `thinknxg_estate.core.api.delete_rent_schedule` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_rent_schedule` |
| `thinknxg_estate.core.api.create_security_deposit` | Estate staff | GET/POST | — | `re_core.re_core.api.create_security_deposit` |
| `thinknxg_estate.core.api.delete_lease_charge` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_lease_charge` |
| `thinknxg_estate.core.api.create_amenity` | Estate staff | GET/POST | — | `re_core.re_core.api.create_amenity` |
| `thinknxg_estate.core.api.update_tenant_kyc_document` | Estate staff | GET/POST | — | `re_core.re_core.api.update_tenant_kyc_document` |
| `thinknxg_estate.core.api.update_inspection_items` | Estate staff | GET/POST | — | `re_core.re_core.api.update_inspection_items` |
| `thinknxg_estate.core.api.get_companies` | Estate staff | GET/POST | — | `re_core.re_core.api.get_companies` |
| `thinknxg_estate.core.api.get_property_owners_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_property_owners_list` |
| `thinknxg_estate.core.api.create_property` | Estate staff | GET/POST | — | `re_core.re_core.api.create_property` |
| `thinknxg_estate.core.api.update_property` | Estate staff | GET/POST | — | `re_core.re_core.api.update_property` |
| `thinknxg_estate.core.api.create_unit` | Estate staff | GET/POST | — | `re_core.re_core.api.create_unit` |
| `thinknxg_estate.core.api.update_unit` | Estate staff | GET/POST | — | `re_core.re_core.api.update_unit` |
| `thinknxg_estate.core.api.delete_unit` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_unit` |
| `thinknxg_estate.core.api.create_tenant` | Estate staff | GET/POST | — | `re_core.re_core.api.create_tenant` |
| `thinknxg_estate.core.api.update_tenant` | Estate staff | GET/POST | — | `re_core.re_core.api.update_tenant` |
| `thinknxg_estate.core.api.delete_tenant` | Estate staff | GET/POST | — | `re_core.re_core.api.delete_tenant` |
| `thinknxg_estate.core.api.create_maintenance_request` | Estate staff | GET/POST | — | `re_core.re_core.api.create_maintenance_request` |
| `thinknxg_estate.core.api.record_partial_payment` | Estate staff | GET/POST | — | `re_core.re_core.api.record_partial_payment` |
| `thinknxg_estate.core.api.get_bulk_pdc_due_installments` | Estate staff | GET/POST | — | `re_core.re_core.api.get_bulk_pdc_due_installments` |
| `thinknxg_estate.core.api.submit_bulk_pdc_payments` | Estate staff | GET/POST | — | `re_core.re_core.api.submit_bulk_pdc_payments` |
| `thinknxg_estate.core.api.get_purchase_invoices_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_purchase_invoices_list` |
| `thinknxg_estate.core.api.get_suppliers_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_suppliers_list` |
| `thinknxg_estate.core.api.create_purchase_invoice` | Estate staff | GET/POST | — | `re_core.re_core.api.create_purchase_invoice` |
| `thinknxg_estate.core.api.get_expense_properties_list` | Estate staff | GET/POST | — | `re_core.re_core.api.get_expense_properties_list` |
| `thinknxg_estate.core.api.create_expense_property` | Estate staff | GET/POST | — | `re_core.re_core.api.create_expense_property` |
| `thinknxg_estate.core.api.submit_expense_property` | Estate staff | GET/POST | — | `re_core.re_core.api.submit_expense_property` |
| `thinknxg_estate.core.api.record_expense_partial_payment` | Estate staff | GET/POST | — | `re_core.re_core.api.record_expense_partial_payment` |

## CRM API (desk users with an estate or accounts role)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.crm.api.get_lead_sources` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_lead_sources` |
| `thinknxg_estate.crm.api.get_commission_entries` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_commission_entries` |
| `thinknxg_estate.crm.api.create_commission_entry` | Estate staff | GET/POST | — | `re_crm.re_crm.api.create_commission_entry` |
| `thinknxg_estate.crm.api.update_commission_status` | Estate staff | GET/POST | — | `re_crm.re_crm.api.update_commission_status` |
| `thinknxg_estate.crm.api.get_commission_slabs` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_commission_slabs` |
| `thinknxg_estate.crm.api.set_commission_slabs` | Estate staff | GET/POST | — | `re_crm.re_crm.api.set_commission_slabs` |
| `thinknxg_estate.crm.api.get_whatsapp_logs` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_whatsapp_logs` |
| `thinknxg_estate.crm.api.get_agents_list` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_agents_list` |
| `thinknxg_estate.crm.api.create_lead` | Estate staff | GET/POST | — | `re_crm.re_crm.api.create_lead` |
| `thinknxg_estate.crm.api.get_deals_list` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_deals_list` |
| `thinknxg_estate.crm.api.update_deal_stage` | Estate staff | GET/POST | — | `re_crm.re_crm.api.update_deal_stage` |
| `thinknxg_estate.crm.api.get_leads_list` | Estate staff | GET/POST | — | `re_crm.re_crm.api.get_leads_list` |
| `thinknxg_estate.crm.api.convert_lead_to_deal` | Estate staff | GET/POST | — | `re_crm.re_crm.api.convert_lead_to_deal` |
| `thinknxg_estate.crm.api.create_site_visit` | Estate staff | GET/POST | — | `re_crm.re_crm.api.create_site_visit` |

## Public listings and visitor accounts (/listings)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_csrf_token` | Public (guest) | GET/POST | Plain-GET, CSRF-exempt endpoint so a static www page (no Desk boot, | `re_core.re_core.listing_portal_api.listing_portal.get_csrf_token` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.portal_signup` | Public (guest); rate limit 10 per 3600s | POST only | — | `re_core.re_core.listing_portal_api.listing_portal.portal_signup` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.portal_login` | Public (guest); rate limit 20 per 900s | POST only | — | `re_core.re_core.listing_portal_api.listing_portal.portal_login` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.portal_logout` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.portal_logout` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_current_portal_user` | Public (guest) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.get_current_portal_user` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_live_properties` | Public (guest) | GET/POST | Returns published portal listings — either a Unit inside a building, or | `re_core.re_core.listing_portal_api.listing_portal.get_live_properties` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_property_detail` | Public (guest) | GET/POST | Full detail for a single dossier view — either a Unit, or a standalone | `re_core.re_core.listing_portal_api.listing_portal.get_property_detail` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.toggle_wishlist` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.toggle_wishlist` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.submit_enquiry` | Public (guest); rate limit 20 per 3600s | POST only | Unit enquiry from /listings. Guests must leave a name and a mobile number; signed-in | `re_core.re_core.listing_portal_api.listing_portal.submit_enquiry` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.book_site_visit` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.book_site_visit` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.request_lease_contract` | Logged-in user (checked in code) | GET/POST | Portal-originated lease request. Creates a Draft Lease Contract only - | `re_core.re_core.listing_portal_api.listing_portal.request_lease_contract` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_my_requests` | Logged-in user (checked in code) | GET/POST | Everything the logged-in portal visitor has submitted - enquiries, | `re_core.re_core.listing_portal_api.listing_portal.get_my_requests` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.create_saved_search` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.create_saved_search` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.get_my_saved_searches` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.get_my_saved_searches` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.delete_saved_search` | Logged-in user (checked in code) | GET/POST | — | `re_core.re_core.listing_portal_api.listing_portal.delete_saved_search` |
| `thinknxg_estate.core.listing_portal_api.listing_portal.calculate_rent_plan` | Public (guest) | GET/POST | Splits the annual rent into an even cheque schedule — the standard | `re_core.re_core.listing_portal_api.listing_portal.calculate_rent_plan` |

## Public listings, inquiries and AI chat (/properties)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.portal.api.listings.search` | Public (guest); rate limit 120 per 3600s | GET/POST | — | `re_portal.api.listings.search` |
| `thinknxg_estate.portal.api.listings.get` | Public (guest); rate limit 240 per 3600s | GET/POST | — | `re_portal.api.listings.get` |
| `thinknxg_estate.portal.api.listings.submit_inquiry` | Public (guest); rate limit key='inquiry' 20 per 3600s | POST only | Create a Listing Inquiry. Guards: honeypot (website_url must stay empty), | `re_portal.api.listings.submit_inquiry` |

## Legacy inquiry form

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.portal.api.inquiries.create` | Public (guest); rate limit 10 per 3600s | POST only | Public inquiry endpoint. `website` is a honeypot field — must stay empty. | `re_portal.api.inquiries.create` |

## Listings AI chat

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.portal.api.chat.config` | Public (guest); rate limit 120 per 3600s | GET/POST | — | `re_portal.api.chat.config` |
| `thinknxg_estate.portal.api.chat.history` | Public (guest); rate limit 120 per 3600s | GET/POST | Replay the visible turns of this visitor's own chat (the token is the secret). | `re_portal.api.chat.history` |
| `thinknxg_estate.portal.api.chat.send` | Public (guest); rate limit 60 per 3600s | POST only | — | `re_portal.api.chat.send` |

## Property Finder / Bayut feeds

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.portal.api.feeds.property_finder` | Public (guest); rate limit 60 per 3600s | GET/POST | — | `re_portal.api.feeds.property_finder` |
| `thinknxg_estate.portal.api.feeds.bayut` | Public (guest); rate limit 60 per 3600s | GET/POST | — | `re_portal.api.feeds.bayut` |

## Tenant portal (website login, role Tenant)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.portal.api.tenant.dashboard` | Logged-in user (checked in code) | GET/POST | — | `re_portal.api.tenant.dashboard` |
| `thinknxg_estate.portal.api.tenant.installments` | Logged-in user (checked in code) | GET/POST | — | `re_portal.api.tenant.installments` |
| `thinknxg_estate.portal.api.tenant.maintenance_list` | Logged-in user (checked in code) | GET/POST | — | `re_portal.api.tenant.maintenance_list` |
| `thinknxg_estate.portal.api.tenant.get_outstanding_rent` | Logged-in user (checked in code) | GET/POST | — | `re_portal.api.tenant.get_outstanding_rent` |
| `thinknxg_estate.portal.api.tenant.terminate_lease` | Logged-in user (checked in code) | POST only | Tenant self-service termination. The lease is always resolved from the session | `re_portal.api.tenant.terminate_lease` |
| `thinknxg_estate.portal.api.tenant.create_maintenance` | Logged-in user (checked in code) | POST only | — | `re_portal.api.tenant.create_maintenance` |

## Access-code tenant portal (opt-in)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_login` | Public (guest); rate limit 10 per 900s | POST only | Validate mobile + access code, issue an opaque session token. | `re_core.re_core.tenant_portal_api.tenant_portal_login` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_logout` | Public (guest) | POST only | — | `re_core.re_core.tenant_portal_api.tenant_portal_logout` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_dashboard` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_dashboard` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_lease` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_lease` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_installments` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_installments` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_pay_installment` | Public (guest) | POST only | Kept for API compatibility. Tenants cannot post payments against their own rent: | `re_core.re_core.tenant_portal_api.tenant_portal_pay_installment` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_pdcs` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_pdcs` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_maintenance_list` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_maintenance_list` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_create_maintenance_request` | Public (guest); rate limit 20 per 3600s | POST only | — | `re_core.re_core.tenant_portal_api.tenant_portal_create_maintenance_request` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_units` | Public (guest) | GET/POST | Helper for the New Request form — units the tenant can raise a request against. | `re_core.re_core.tenant_portal_api.tenant_portal_units` |
| `thinknxg_estate.core.tenant_portal_api.tenant_portal_documents` | Public (guest) | GET/POST | — | `re_core.re_core.tenant_portal_api.tenant_portal_documents` |

## WhatsApp webhook (Meta Cloud API)

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.voice.api.webhook.verify` | Public (guest) | GET/POST | GET handshake from Meta when the callback URL is registered. | `re_voice.api.webhook.verify` |
| `thinknxg_estate.voice.api.webhook.receive` | Public (guest) | POST only | Entry point. Persists, ACKs, and queues — never processes inline. | `re_voice.api.webhook.receive` |
| `thinknxg_estate.voice.api.webhook.webhook` | Public (guest) | GET/POST | Single callback URL for Meta: GET = verification handshake, POST = messages. | `re_voice.api.webhook.webhook` |

## Other

| Endpoint | Access | HTTP | Description | Legacy path |
|---|---|---|---|---|
| `thinknxg_estate.core.demo_data.tools.run_load` | Logged-in user (checked in code) | GET/POST | — | `re_core.demo_data.tools.run_load` |
| `thinknxg_estate.portal.sync.run_backfill` | Logged-in user (checked in code) | GET/POST | Manually triggerable version of backfill_all(), restricted to System Managers. | `re_portal.sync.run_backfill` |
| `thinknxg_estate.thinknxg_estate.dashboard_chart_source.re_lease_expirations_by_month.re_lease_expirations_by_month.get` | Estate staff | GET/POST | — | `re_core.re_core.dashboard_chart_source.re_lease_expirations_by_month.re_lease_expirations_by_month.get` |
| `thinknxg_estate.thinknxg_estate.dashboard_chart_source.re_rent_arrears_ageing.re_rent_arrears_ageing.get` | Estate staff | GET/POST | — | `re_core.re_core.dashboard_chart_source.re_rent_arrears_ageing.re_rent_arrears_ageing.get` |
| `thinknxg_estate.thinknxg_estate.dashboard_chart_source.re_rent_billed_vs_collected.re_rent_billed_vs_collected.get` | Estate staff | GET/POST | — | `re_core.re_core.dashboard_chart_source.re_rent_billed_vs_collected.re_rent_billed_vs_collected.get` |

