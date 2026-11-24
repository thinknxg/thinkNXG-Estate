"""Outbound HTTP for provider calls (AI, speech, WhatsApp).

Frappe 16 no longer exposes frappe.make_post_request / frappe.make_get_request, which the voice
layer used; every such call failed and was swallowed by its error handler. These helpers replace
them with explicit timeouts, raise on HTTP errors, and return raw bytes for media downloads."""

import requests

DEFAULT_TIMEOUT = 45


def post_json(url, headers=None, data=None, json=None, files=None, timeout=DEFAULT_TIMEOUT):
	response = requests.post(url, headers=headers, data=data, json=json, files=files, timeout=timeout)
	response.raise_for_status()
	return response.json()


def get_json(url, headers=None, params=None, timeout=DEFAULT_TIMEOUT):
	response = requests.get(url, headers=headers, params=params, timeout=timeout)
	response.raise_for_status()
	return response.json()


def get_bytes(url, headers=None, timeout=DEFAULT_TIMEOUT):
	response = requests.get(url, headers=headers, timeout=timeout)
	response.raise_for_status()
	return response.content
