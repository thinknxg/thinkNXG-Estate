import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

OWNER_ROLE = "Property Owner"


class PropertyOwner(Document):
    def validate(self):
        if not self.supplier and self.owner_name:
            self.supplier = self._get_or_make_supplier()
        if self.enable_portal and not self.email:
            frappe.throw(_("An email address is required to enable the owner portal."))

    def on_update(self):
        if self.enable_portal and not self.portal_user:
            self._provision_portal_user()

    def _get_or_make_supplier(self):
        # Reuse a same-named Supplier only if no other owner is paid through it; otherwise two
        # owners with the same name would share one payable ledger.
        existing = frappe.db.exists("Supplier", {"supplier_name": self.owner_name})
        if existing and not frappe.db.exists(
                "Property Owner", {"supplier": existing, "name": ["!=", self.name or ""]}):
            return existing
        supplier = frappe.new_doc("Supplier")
        supplier.supplier_name = self.owner_name
        supplier.supplier_group = (
            frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
        )
        supplier.supplier_type = "Individual" if self.owner_type == "Individual" else "Company"
        supplier.insert(ignore_permissions=True)
        return supplier.name

    def _provision_portal_user(self):
        if frappe.db.exists("User", self.email):
            user = frappe.get_doc("User", self.email)
        else:
            user = frappe.new_doc("User")
            user.email = self.email
            user.first_name = self.owner_name
            user.user_type = "Website User"
            user.send_welcome_email = 1
            user.insert(ignore_permissions=True)
        user.add_roles(OWNER_ROLE)
        self.db_set("portal_user", user.name)
        frappe.msgprint(_("Owner portal user {0} provisioned. Login: {1}").format(
            user.name, get_url("/owner-portal")))


def get_owner_for_user(user=None):
    """Resolve the Property Owner record for a session user (owner portal)."""
    user = user or frappe.session.user
    if user in ("Guest", "Administrator"):
        return None
    return frappe.db.get_value("Property Owner", {"portal_user": user, "enable_portal": 1}, "name")
