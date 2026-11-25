# thinkNXG Estate demo data - verification report

Site: fresh.test   Date: 2026-11-25   Company: Falak Prime Properties LLC

## 1. Record counts

- Property: 5
- Unit: 34
- Property Owner: 4
- Amenity: 16
- Property Document: 15
- Utility Account: 80
- Tenant: 20
- Lease Contract: 21
- Rent Schedule: 20
- Security Deposit: 20
- Post Dated Cheque: 46
- Move In Out Inspection: 8
- Sales Invoice: 39
- Payment Entry: 57
- Journal Entry: 46
- Purchase Invoice: 27
- Expense Property: 10
- Owner Statement: 6
- Maintenance Request: 20
- Maintenance Job: 11
- RE Agent: 6
- RE Lead: 31
- RE Deal: 23
- Site Visit: 18
- Reservation: 2
- Commission Entry: 5
- Listing: 15
- Property Wishlist: 8
- Saved Search: 4
- Site Visit Booking: 5
- Property Enquiry: 4
- Listing Inquiry: 4
- Customer Thread: 10
- Voice Message: 6
- WhatsApp Message Log: 10
- Lead Score Log: 26
- Sentiment Reading: 10

## 2. Requested minimums

- PASS  Properties (5+): 5
- PASS  Units (20+): 34
- PASS  Tenants (10+): 20
- PASS  Leads (20+): 31
- PASS  Agents and brokers: 6
- PASS  Lease contracts: 21
- PASS  Maintenance requests: 20
- PASS  Published listings: 15

## 3. Scenario coverage

- Vacant units: 13
- Occupied units: 17
- Reserved units: 2
- Units under maintenance or blocked: 2
- Active leases: 13
- Expiring leases: 4
- Expired leases: 1
- Terminated leases: 1
- Renewed leases: 1
- Draft leases (incl. portal request): 1
- Installments fully paid: 29
- Installments partially paid: 2
- Installments overdue: 7
- Installments invoiced: 1
- Installments bounced: 1
- Cheques in hand (Received): 17
- Cheques cleared: 28
- Cheques bounced: 1
- Deposits held: 17
- Deposits refunded / partly refunded: 3
- Emergency maintenance: 3
- Open maintenance: 6
- In-progress maintenance: 3
- Completed maintenance: 8
- Leads New: 5
- Leads Contacted: 8
- Leads Qualified: 8
- Leads Converted: 5
- Leads Disqualified: 5
- Deals Won: 5
- Deals Lost: 4
- Deals in Reservation: 2
- Deals in Negotiation: 3
- Deals Site Visit Scheduled: 3
- Deals Contacted: 3
- Deals New: 3
- Commission Draft / Approved / Paid: 5
- Hot / Warm / Cold leads scored: 26
  - commissions Draft: 1
  - commissions Approved: 2
  - commissions Paid: 2
  - leads Hot: 0
  - leads Warm: 11
  - leads Cold: 15

## 4. Integrity checks

- PASS  Every occupied unit has a live submitted lease: 0 mismatch(es)
- PASS  Every live lease is the current lease of its unit: 0 mismatch(es)
- PASS  Rent schedule totals equal their installments: 0 mismatch(es)
- PASS  Paid installments are fully paid: 0 mismatch(es)
- PASS  Paid installments have settled invoices: 0 mismatch(es)
- PASS  General ledger debits equal credits: debit 5,442,370.00 / credit 5,442,370.00
- PASS  No cancelled Lease Contract left behind: 0
- PASS  No cancelled Security Deposit left behind: 0
- PASS  No cancelled Post Dated Cheque left behind: 0
- PASS  No cancelled Expense Property left behind: 0
- PASS  No cancelled Maintenance Job left behind: 0
- PASS  Rent invoices carry VAT only on commercial units: checked by tax templates
- PASS  No dangling Link values in the seeded doctypes: 0

## 5. Portfolio snapshot (what the dashboards will show)

- Units: 34; occupied 17 (50%)
- Rent invoiced: AED 2,537,500.00; outstanding: AED 221,350.00
- Receipts posted: AED 2,351,150.00
- Annual contract value of live leases: AED 3,074,000.00
- Security deposits held: AED 193,600.00

## Result

ALL CHECKS PASSED
