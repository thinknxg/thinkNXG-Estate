from thinknxg_estate.portal.api.tenant import installments
from thinknxg_estate.portal.utils import money
from thinknxg_estate.www.tenant_portal_common import require_tenant_context

BADGE = {"Paid": "success", "Invoiced": "info", "Pending": "secondary",
         "Overdue": "danger", "Bounced": "danger", "Cancelled": "light"}


def get_context(context):
    require_tenant_context(context)
    context.update(installments())
    context.money = money
    context.badge = BADGE
    context.title = "Payments"
    return context
