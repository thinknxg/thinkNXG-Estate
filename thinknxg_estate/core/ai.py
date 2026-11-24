"""The one AI provider setting (AI Settings) shared by the website chat assistant and the voice CRM.

Both features call the provider through their own request code (the chat assistant needs tool
use; the voice CRM needs plain completions), but provider, endpoint, key, model, prices and the
monthly budget all come from here, and spend from both counts against the same budget."""

import frappe
from frappe.utils import cstr, flt, get_first_day, get_last_day, nowdate

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

ENDPOINTS = {"Anthropic": ANTHROPIC_URL, "OpenAI": OPENAI_URL, "Gemini": GEMINI_URL}

# Defaults when no model is set: the chat assistant favours a fast model.
DEFAULT_MODELS = {
	"chat": {"Anthropic": "claude-haiku-5-5", "OpenAI": "gpt-4o-mini", "Gemini": "gemini-3.8-flash"},
	"voice": {"Anthropic": "claude-sonnet-5-5", "OpenAI": "gpt-4o-mini", "Gemini": "gemini-3.8-flash"},
}

FEATURES = ("chat", "voice")


def settings():
	return frappe.get_cached_doc("AI Settings")


def provider_config(feature="voice"):
	"""What a feature needs to call the shared provider, or None when no provider is usable.

	Returns a dict: provider, endpoint, key, model, openai_compatible (bool)."""
	if feature not in FEATURES:
		raise ValueError(feature)
	s = settings()
	provider = s.llm_provider
	if not provider or provider == "None":
		return None
	key = s.get_password("api_key", raise_exception=False)
	endpoint = cstr(s.llm_endpoint).strip() or ENDPOINTS.get(provider)
	if not key or not endpoint:
		return None
	model = ((s.chat_model if feature == "chat" else None) or s.llm_model
	         or DEFAULT_MODELS[feature].get(provider) or "")
	return frappe._dict(provider=provider, endpoint=endpoint, key=key, model=model,
	                    openai_compatible=provider != "Anthropic")


def is_configured():
	return provider_config("voice") is not None


def token_cost(input_tokens, output_tokens):
	"""Cost of one call in the budget's currency. Prices come from AI Settings; the older
	site_config keys (llm_input_cost_per_mtok / llm_output_cost_per_mtok) still work."""
	s = settings()
	price_in = flt(s.get("input_cost_per_mtok")) or flt(frappe.conf.get("llm_input_cost_per_mtok"))
	price_out = flt(s.get("output_cost_per_mtok")) or flt(frappe.conf.get("llm_output_cost_per_mtok"))
	return (flt(input_tokens) * price_in + flt(output_tokens) * price_out) / 1_000_000


def spend_this_month():
	"""Voice CRM usage (Voice Usage Log) plus chat assistant usage (Portal Chat Session)."""
	start, end = get_first_day(nowdate()), get_last_day(nowdate())
	voice = frappe.db.sql(
		"SELECT COALESCE(SUM(cost), 0) FROM `tabVoice Usage Log` WHERE DATE(creation) BETWEEN %s AND %s",
		(start, end))[0][0]
	chat = frappe.db.sql(
		"SELECT COALESCE(SUM(cost), 0) FROM `tabPortal Chat Session` WHERE DATE(last_active) BETWEEN %s AND %s",
		(start, end))[0][0]
	return flt(voice) + flt(chat)


def budget_available():
	budget = flt(settings().monthly_budget)
	return not budget or spend_this_month() < budget


def refresh_month_spend():
	"""Scheduled: keep the read-only 'Spend This Month' figure on AI Settings current."""
	frappe.db.set_single_value("AI Settings", "month_spend", spend_this_month())
