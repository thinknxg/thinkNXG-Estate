# Lease termination: dates, settlement and accounting adjustments

## What existed before

`Lease Contract.terminate()` only changed statuses. It had one date (labelled "Schedule End Date" in the dialog but stored nowhere), no Posting Date and no ledger entries. Findings from tracing it:

- Outstanding rent summed only `Pending` and `Overdue` installments at their full amount, so `Invoiced` and `Partially Paid` installments were missed.
- Rent is invoiced ahead of its due date (`invoice_lead_days`). Installments due after the termination date that already held a Sales Invoice were left untouched, so the invoice stayed receivable.
- `Security Deposit.refund()` used the original deposit amount, not what was still held, and both deposit refund paths posted on today's date.
- There is no Lease Termination DocType and no termination journal entry; the deposit already had two separate accounting paths (`Security Deposit.refund()` and `update_security_deposit` → `core/security_deposit_accounting.py`).

## The three dates

| Field | Meaning |
|---|---|
| Schedule End Date | Contractual end: `Lease Contract.end_date`. Never changed by termination. |
| Tenancy End Date | Actual end (`tenancy_end_date`). Decides which rent is owed. `termination_date` is kept as an alias for existing callers. |
| Posting Date | Date entries enter the General Ledger (`termination_posting_date`). Required whenever credit notes are issued; never defaulted silently. |

## Settlement (`core/lease_settlement.py`)

```
rent_outstanding = Σ (amount − paid) of installments due on/before the Tenancy End Date, any unpaid status
net_settlement   = deposit_balance + paid_after_end − rent_outstanding      (> 0 refundable, < 0 payable by tenant)
deposit_balance  = deposit amount − deductions − refunds already booked      (0 unless the deposit was received)
```

Rent already invoiced for installments due **after** the Tenancy End Date is handled by a standard ERPNext credit note (Sales Invoice return) dated the Posting Date. Terminating is refused until staff confirm the credit notes (`issue_credit_notes`) and give a Posting Date; the outstanding figure is never just reduced. The credited installment is set to Cancelled with a remark, and a snapshot of the settlement (including credit note names) is stored on the lease. Cash already received against those invoices stays on the customer account as credit and is refunded through the normal Payment Entry; nothing is refunded automatically.

Tenant-initiated termination (`portal.api.tenant.terminate_lease`) cannot issue credit notes, so it is refused when advance invoices exist and stays a staff matter.

## Screens and APIs

- Desk: Lease Contract > Terminate Lease shows the three dates, live outstanding rent, deposit balance, net settlement and any invoices needing credit notes. Security Deposit > Refund / Settle shows the balance and asks for a Posting Date.
- Staff portal (`re-portal`): Terminate Lease screen mirrors the desk dialog; Rent Schedule > Pay and the deposit editor ask for a Posting Date.
- APIs: `terminate_lease_contract` (new `tenancy_end_date`, `posting_date`, `issue_credit_notes`), `get_lease_termination_settlement` (new, with `re_core` alias), `update_security_deposit` (new required `posting_date` when posting entries).

## Not covered (needs a business decision)

- **Pro-rata rent.** An installment due on/before the Tenancy End Date is owed in full, as before. Rent for a period that straddles the end date is not pro-rated.
- Applying the deposit against unpaid rent in one ledger entry. The settlement figure is calculated, but the deposit is still refunded or deducted through the existing deposit flow.
- Post-dated cheques linked to cancelled installments are not cancelled automatically.
