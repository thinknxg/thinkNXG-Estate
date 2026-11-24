"""One AI provider for the website chat assistant and the voice CRM (AI Settings).

Before 1.2 the chat assistant had its own provider, key, model, prices and budget in Portal Chat
Settings. This moves them into AI Settings:

- If only the chat had a key, AI Settings takes the chat's provider, key, model (as the chat
  model), prices and budget. The voice CRM stays off unless "Use AI in the Voice CRM" was on.
- If both had keys, AI Settings keeps its provider and key and the chat now uses them. The chat's
  model is kept as the chat model only when the providers match. A comment on Portal Chat
  Settings records the change.
- Budgets: the shared budget is the sum of the two budgets that were set.

The old chat fields stay in the database (hidden) so the upgrade can be rolled back."""

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.exists("DocType", "Portal Chat Settings"):
		return
	ai = frappe.get_single("AI Settings")
	chat = frappe.get_single("Portal Chat Settings")
	ai_key = ai.get_password("api_key", raise_exception=False)
	chat_key = chat.get_password("api_key", raise_exception=False)
	chat_provider = chat.get("provider") or "Gemini"

	if chat_key and not ai_key:
		ai.llm_provider = chat_provider
		ai.llm_endpoint = None
		ai.api_key = chat_key
		ai.chat_model = chat.get("model")
	elif chat_key and ai_key:
		if ai.llm_provider == chat_provider:
			ai.chat_model = chat.get("model")
		if ai.llm_provider != chat_provider or ai_key != chat_key:
			chat.add_comment("Comment", (
				"From thinkNXG Estate 1.2 the chat assistant uses the AI provider in AI Settings "
				f"({ai.llm_provider}). Its previous provider ({chat_provider}) and key are no longer used."))

	if not flt(ai.get("input_cost_per_mtok")) and flt(chat.get("input_cost_per_mtok")):
		ai.input_cost_per_mtok = chat.input_cost_per_mtok
		ai.output_cost_per_mtok = chat.output_cost_per_mtok
	if not flt(ai.get("input_cost_per_mtok")) and frappe.conf.get("llm_input_cost_per_mtok"):
		ai.input_cost_per_mtok = flt(frappe.conf.get("llm_input_cost_per_mtok"))
		ai.output_cost_per_mtok = flt(frappe.conf.get("llm_output_cost_per_mtok"))

	budgets = [flt(b) for b in (ai.monthly_budget, chat.get("monthly_budget")) if flt(b)]
	if budgets:
		ai.monthly_budget = sum(budgets)

	ai.flags.ignore_permissions = True
	ai.save()
