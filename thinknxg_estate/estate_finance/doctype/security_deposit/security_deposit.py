import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from thinknxg_estate.core.security import requires_permission


class SecurityDeposit(Document):
    def on_submit(self):
        self.db_set("status", "Held")
        je = self._make_holding_entry()
        if je:
            self.db_set("journal_entry", je)

    def on_cancel(self):
        self.db_set("status", "Draft")

    def _accounts(self):
        settings = frappe.get_single("Property Settings")
        return settings.deposit_bank_account, settings.deposit_liability_account

    def _make_holding_entry(self):
        """Dr Bank / Cr Deposits Held. Skipped when accounts are not configured."""
        bank, liability = self._accounts()
        if not (bank and liability):
            return None
        je = frappe.new_doc("Journal Entry")
        je.company = self.company
        je.posting_date = self.received_date or nowdate()
        je.user_remark = _("Security deposit held for lease {0}").format(self.lease_contract)
        je.append("accounts", {"account": bank, "debit_in_account_currency": self.amount})
        je.append("accounts", {"account": liability, "credit_in_account_currency": self.amount})
        je.insert(ignore_permissions=True)
        je.submit()
        return je.name

    @frappe.whitelist()

    @requires_permission("submit")
    def refund(self, deduction_amount=0, deduction_reason=None, posting_date=None):
        """Settle what is still held: refund = balance - deduction.

        The balance is the deposit actually outstanding (amount less deductions and
        refunds already booked), not the original amount. ``posting_date`` is the
        General Ledger date of the refund entry; it falls back to today only for
        callers that predate the argument (the desk dialog always supplies it).
        """
        from thinknxg_estate.core.lease_settlement import deposit_balance

        if self.docstatus != 1 or self.status != "Held":
            frappe.throw(_("Only Held deposits can be refunded."))
        balance = deposit_balance(self.name)
        deduction = flt(deduction_amount)
        if deduction < 0:
            frappe.throw(_("Deduction cannot be negative."))
        if deduction > balance:
            frappe.throw(_("Deduction {0} cannot exceed the deposit balance {1}.").format(deduction, balance))
        refund_amount = balance - deduction
        total_deduction = flt(self.deduction_amount) + deduction
        total_refunded = flt(self.refunded_amount) + refund_amount
        self.db_set("deduction_amount", total_deduction)
        if deduction_reason:
            self.db_set("deduction_reason", deduction_reason)
        self.db_set("refunded_amount", total_refunded)
        if total_deduction and total_refunded:
            self.db_set("status", "Partially Refunded")
        elif total_refunded:
            self.db_set("status", "Refunded")
        else:
            self.db_set("status", "Forfeited")
        je = self._make_refund_entry(refund_amount, posting_date)
        if je:
            self.db_set("refund_payment_entry", je)
        return self.status

    def _make_refund_entry(self, refund_amount, posting_date=None):
        bank, liability = self._accounts()
        if not (bank and liability and refund_amount):
            return None
        je = frappe.new_doc("Journal Entry")
        je.company = self.company
        je.set_posting_time = 1
        je.posting_date = posting_date or nowdate()
        je.user_remark = _("Security deposit refund for lease {0}").format(self.lease_contract)
        je.append("accounts", {"account": liability, "debit_in_account_currency": refund_amount})
        je.append("accounts", {"account": bank, "credit_in_account_currency": refund_amount})
        je.insert(ignore_permissions=True)
        je.submit()
        return je.name
