"""Single LLM entry point with budget enforcement and usage logging.

Every AI call in re_voice goes through llm_complete so that cost is observable
and the monthly cap degrades the system gracefully rather than silently."""

import frappe
from thinknxg_estate.core.http import post_json
from frappe.utils import cstr


def budget_available():
    """Shared monthly budget (AI Settings) covering the voice CRM and the chat assistant."""
    from thinknxg_estate.core.ai import budget_available as shared

    return shared()


def log_usage(task, provider, audio_seconds=0, input_tokens=0, output_tokens=0,
              cost=0, reference_doctype=None, reference_name=None):
    frappe.get_doc({
        "doctype": "Voice Usage Log", "task": task, "provider": provider,
        "audio_seconds": audio_seconds, "input_tokens": input_tokens,
        "output_tokens": output_tokens, "cost": cost,
        "reference_doctype": reference_doctype, "reference_name": reference_name,
    }).insert(ignore_permissions=True)


def llm_complete(prompt, system=None, task="Intent", json_mode=False,
                 reference_doctype=None, reference_name=None):
    """Returns the model's text, or None when disabled / over budget / failed.
    Callers must handle None — that is the graceful-degradation path."""
    from thinknxg_estate.core.ai import provider_config

    settings = frappe.get_cached_doc("AI Settings")
    config = provider_config("voice")
    if not settings.llm_enabled or not config:
        return None
    if not budget_available():
        frappe.log_error(title="thinkNXG Estate: monthly AI budget exhausted",
                         message=f"task={task}; falling back to deterministic path")
        return None

    try:
        text, usage = _call_provider(config, prompt, system, json_mode)
        log_usage(task, config.provider,
                  input_tokens=usage.get("input_tokens", 0),
                  output_tokens=usage.get("output_tokens", 0),
                  cost=usage.get("cost") or _token_cost(usage),
                  reference_doctype=reference_doctype,
                  reference_name=reference_name)
        return text
    except Exception:
        frappe.log_error(title="thinkNXG Estate: LLM call failed", message=f"task={task}")
        return None


def _call_provider(config, prompt, system, json_mode):
    if config.provider == "Anthropic":
        body = {"model": config.model, "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        response = post_json(
            config.endpoint,
            headers={"x-api-key": config.key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            data=frappe.as_json(body))
        text = "".join(block.get("text", "")
                       for block in response.get("content", [])
                       if block.get("type") == "text")
        usage = response.get("usage", {})
        return text, {"input_tokens": usage.get("input_tokens", 0),
                      "output_tokens": usage.get("output_tokens", 0)}

    # OpenAI, Gemini (OpenAI-compatible endpoint) and Custom OpenAI-compatible endpoints
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = {"model": config.model, "messages": messages}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    response = post_json(
        config.endpoint,
        headers={"Authorization": f"Bearer {config.key}",
                 "Content-Type": "application/json"},
        data=frappe.as_json(body))
    text = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})
    return text, {"input_tokens": usage.get("prompt_tokens", 0),
                  "output_tokens": usage.get("completion_tokens", 0)}


def _token_cost(usage):
    from thinknxg_estate.core.ai import token_cost

    return token_cost(usage.get("input_tokens"), usage.get("output_tokens"))


def parse_json_response(text):
    """LLMs wrap JSON in prose or fences more often than they should."""
    import json
    import re
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", cstr(text).strip(),
                     flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None
