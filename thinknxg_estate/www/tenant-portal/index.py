import frappe
from thinknxg_estate.portal.api.tenant import dashboard
from thinknxg_estate.portal.utils import money
from thinknxg_estate.www.tenant_portal_common import require_tenant_context


def get_context(context):
    require_tenant_context(context)
    context.update(dashboard())
    context.money = money
    context.title = "My Tenancy"
    return context
