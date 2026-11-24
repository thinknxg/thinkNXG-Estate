"""Legacy entry point for CRM WhatsApp messages; delegates to the unified channel."""

from thinknxg_estate.channels.whatsapp import send_text


def send_whatsapp(to_number, message, reference_doctype=None, reference_name=None,
                  purpose=None, variables=None):
    """Queue a WhatsApp message. Safe to call unconditionally (logs Skipped when it cannot be sent)."""
    return send_text(to_number, message, reference_doctype=reference_doctype,
                     reference_name=reference_name, purpose=purpose, variables=variables)


def _dispatch(log_name):
    """Kept so jobs queued before the upgrade still run."""
    from thinknxg_estate.channels.whatsapp import dispatch

    return dispatch(log_name)
