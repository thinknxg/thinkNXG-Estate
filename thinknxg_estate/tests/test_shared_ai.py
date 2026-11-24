"""One AI provider (AI Settings) for the website chat assistant and the voice CRM.

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_shared_ai
"""

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime


def configure(provider="Anthropic", key="test-key", model=None, chat_model=None, budget=0, endpoint=None,
              price_in=1.0, price_out=2.0, llm_enabled=1):
	ai = frappe.get_single("AI Settings")
	ai.update({"llm_provider": provider, "api_key": key, "llm_model": model, "chat_model": chat_model, "asr_api_key": None,
	           "monthly_budget": budget, "llm_endpoint": endpoint, "input_cost_per_mtok": price_in,
	           "output_cost_per_mtok": price_out, "llm_enabled": llm_enabled})
	ai.save(ignore_permissions=True)
	frappe.clear_document_cache("AI Settings", "AI Settings")
	chat = frappe.get_single("Portal Chat Settings")
	chat.enabled = 1
	chat.save(ignore_permissions=True)
	frappe.clear_document_cache("Portal Chat Settings", "Portal Chat Settings")


class TestProviderConfig(IntegrationTestCase):
	def test_no_provider_means_no_ai(self):
		from thinknxg_estate.core.ai import provider_config
		from thinknxg_estate.portal.api.chat import config

		configure(provider="None")
		self.assertIsNone(provider_config("chat"))
		self.assertFalse(config()["enabled"])

	def test_one_key_serves_both_features(self):
		from thinknxg_estate.core.ai import ANTHROPIC_URL, provider_config
		from thinknxg_estate.portal.api.chat import config

		configure(provider="Anthropic", model="model-voice", chat_model="model-chat")
		chat, voice = provider_config("chat"), provider_config("voice")
		self.assertEqual((chat.key, voice.key), ("test-key", "test-key"))
		self.assertEqual((chat.endpoint, voice.endpoint), (ANTHROPIC_URL, ANTHROPIC_URL))
		self.assertEqual((chat.model, voice.model), ("model-chat", "model-voice"))
		self.assertTrue(config()["enabled"])

	def test_custom_provider_needs_an_endpoint(self):
		from thinknxg_estate.core.ai import provider_config

		configure(provider="Custom")
		self.assertIsNone(provider_config("voice"))
		configure(provider="Custom", endpoint="https://llm.example.com/v1/chat/completions", model="local")
		self.assertEqual(provider_config("voice").endpoint, "https://llm.example.com/v1/chat/completions")


class TestSharedBudget(IntegrationTestCase):
	def test_chat_spend_stops_the_voice_crm_and_the_reverse(self):
		from thinknxg_estate.portal.api.chat import _budget_ok
		from thinknxg_estate.voice.ai.client import budget_available

		configure(budget=1)
		self.assertTrue(budget_available())
		frappe.get_doc({"doctype": "Portal Chat Session", "session_token": frappe.generate_hash(length=20),
		                "last_active": now_datetime(), "cost": 0.6}).insert(ignore_permissions=True)
		self.assertTrue(_budget_ok(None))
		frappe.get_doc({"doctype": "Voice Usage Log", "task": "Intent", "provider": "Anthropic",
		                "cost": 0.5}).insert(ignore_permissions=True)
		self.assertFalse(budget_available(), "chat 0.6 + voice 0.5 exceeds the shared budget of 1")
		self.assertFalse(_budget_ok(None))

	def test_token_cost_uses_shared_prices(self):
		from thinknxg_estate.core.ai import token_cost

		configure(price_in=3, price_out=15)
		self.assertAlmostEqual(token_cost(1_000_000, 100_000), 3 + 1.5)


class TestProviderCalls(IntegrationTestCase):
	def _ok(self, payload):
		response = MagicMock(status_code=200)
		response.json.return_value = payload
		return response

	def test_chat_on_openai_sends_no_gemini_fields(self):
		from thinknxg_estate.core.ai import OPENAI_URL
		from thinknxg_estate.portal.api import chat

		configure(provider="OpenAI", chat_model="gpt-test")
		reply = {"choices": [{"message": {"content": "Hello"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
		messages = [{"role": "user", "content": "hi"},
		            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "search_listings",
		                                               "input": {}, "extra_content": {"google": "sig"}}]},
		            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "[]"}]}]
		with patch.object(chat.requests, "post", return_value=self._ok(reply)) as post:
			out = chat._call_model(None, "system", messages)
		url, body = post.call_args.args[0], post.call_args.kwargs["json"]
		self.assertEqual(url, OPENAI_URL)
		self.assertEqual(body["model"], "gpt-test")
		self.assertNotIn("reasoning_effort", body)
		dumped = json.dumps(body)
		self.assertNotIn("extra_content", dumped)
		self.assertNotIn('"name": "search_listings", "content"', dumped)
		self.assertEqual(out["content"][0]["text"], "Hello")

	def test_chat_on_gemini_keeps_thought_signatures(self):
		from thinknxg_estate.core.ai import GEMINI_URL
		from thinknxg_estate.portal.api import chat

		configure(provider="Gemini")
		messages = [{"role": "user", "content": "hi"},
		            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "search_listings",
		                                               "input": {}, "extra_content": {"google": "sig"}}]},
		            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "[]"}]}]
		reply = {"choices": [{"message": {"content": "Hi"}}], "usage": {}}
		with patch.object(chat.requests, "post", return_value=self._ok(reply)) as post:
			chat._call_model(None, "system", messages)
		self.assertEqual(post.call_args.args[0], GEMINI_URL)
		self.assertIn("extra_content", json.dumps(post.call_args.kwargs["json"]))
		self.assertEqual(post.call_args.kwargs["json"]["reasoning_effort"], "low")

	def test_voice_crm_on_gemini_logs_usage(self):
		from thinknxg_estate.core.ai import GEMINI_URL
		from thinknxg_estate.voice.ai import client

		configure(provider="Gemini", price_in=1_000_000, price_out=0)
		reply = {"choices": [{"message": {"content": "{\"intent\": \"x\"}"}}],
		         "usage": {"prompt_tokens": 7, "completion_tokens": 3}}
		with patch.object(client, "post_json", return_value=reply) as post:
			text = client.llm_complete("prompt", task="Intent")
		self.assertEqual(text, "{\"intent\": \"x\"}")
		self.assertEqual(post.call_args.args[0], GEMINI_URL)
		log = frappe.get_last_doc("Voice Usage Log")
		self.assertEqual((log.provider, log.input_tokens, log.cost), ("Gemini", 7, 7))

	def test_voice_crm_off_when_disabled(self):
		from thinknxg_estate.voice.ai import client

		configure(llm_enabled=0)
		with patch.object(client, "post_json") as post:
			self.assertIsNone(client.llm_complete("prompt"))
		post.assert_not_called()


class TestSpeechKey(IntegrationTestCase):
	def test_anthropic_key_is_never_sent_to_whisper(self):
		from thinknxg_estate.voice.voice.asr import _whisper_key

		configure(provider="Anthropic", key="anthropic-secret")
		settings = frappe.get_single("AI Settings")
		with patch.dict(frappe.conf, {"openai_api_key": None}):
			with self.assertRaises(frappe.ValidationError):
				_whisper_key(settings)
			settings.asr_api_key = "whisper-key"
			settings.save(ignore_permissions=True)
			self.assertEqual(_whisper_key(frappe.get_single("AI Settings")), "whisper-key")

	def test_openai_key_is_reused_for_whisper(self):
		from thinknxg_estate.voice.voice.asr import _whisper_key

		configure(provider="OpenAI", key="openai-secret")
		with patch.dict(frappe.conf, {"openai_api_key": None}):
			self.assertEqual(_whisper_key(frappe.get_single("AI Settings")), "openai-secret")


class TestUpgradePatch(IntegrationTestCase):
	def _chat(self, provider, key, model, budget):
		frappe.db.set_single_value("Portal Chat Settings", {"provider": provider, "model": model,
		                                                    "monthly_budget": budget})
		from frappe.utils.password import set_encrypted_password

		set_encrypted_password("Portal Chat Settings", "Portal Chat Settings", key, "api_key")

	def test_chat_key_moves_to_ai_settings(self):
		from thinknxg_estate.patches.v1_2.shared_ai_provider import execute

		configure(provider="None", key="", budget=0, price_in=0, price_out=0)
		frappe.db.set_single_value("AI Settings", "api_key", None)
		from frappe.utils.password import remove_encrypted_password

		remove_encrypted_password("AI Settings", "AI Settings", "api_key")
		self._chat("Gemini", "gemini-key", "gemini-x", 20)
		execute()
		ai = frappe.get_single("AI Settings")
		self.assertEqual((ai.llm_provider, ai.chat_model, ai.monthly_budget), ("Gemini", "gemini-x", 20))
		self.assertEqual(ai.get_password("api_key"), "gemini-key")

	def test_ai_settings_wins_when_both_have_keys(self):
		from thinknxg_estate.patches.v1_2.shared_ai_provider import execute

		configure(provider="Anthropic", key="anthropic-key", budget=30)
		self._chat("Gemini", "gemini-key", "gemini-x", 20)
		execute()
		ai = frappe.get_single("AI Settings")
		self.assertEqual((ai.llm_provider, ai.get_password("api_key")), ("Anthropic", "anthropic-key"))
		self.assertFalse(ai.chat_model, "a Gemini model name must not be sent to Anthropic")
		self.assertEqual(ai.monthly_budget, 50)
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Portal Chat Settings",
		                                             "content": ["like", "%no longer used%"]}))


class TestProviderHttp(IntegrationTestCase):
	"""Frappe 16 removed frappe.make_post_request; WhatsApp and media now use core.http."""

	def test_whatsapp_send_reaches_the_cloud_api(self):
		from thinknxg_estate.voice.channel import outbound

		ws = frappe.get_single("WhatsApp Settings")
		ws.update({"enabled": 1, "phone_number_id": "123", "access_token": "tok", "api_version": "v19.0"})
		ws.save(ignore_permissions=True)
		frappe.clear_document_cache("WhatsApp Settings", "WhatsApp Settings")
		with patch.object(outbound, "post_json", return_value={"messages": [{"id": "wamid.1"}]}) as post:
			response = outbound._api({"to": "96890000000", "type": "text", "text": {"body": "hi"}})
		self.assertEqual(response["messages"][0]["id"], "wamid.1")
		self.assertTrue(post.call_args.args[0].endswith("/123/messages"))

	def test_media_download_keeps_bytes(self):
		from thinknxg_estate.voice.channel import media

		ws = frappe.get_single("WhatsApp Settings")
		ws.update({"access_token": "tok"})
		ws.save(ignore_permissions=True)
		frappe.clear_document_cache("WhatsApp Settings", "WhatsApp Settings")
		with patch.object(media, "get_json", return_value={"url": "https://cdn/x", "mime_type": "audio/ogg"}), \
		     patch.object(media, "get_bytes", return_value=b"OggS\x00\xff") as raw:
			content, mime, name = media.download_media("m1")
		self.assertEqual((content, mime, name), (b"OggS\x00\xff", "audio/ogg", "m1.ogg"))
		raw.assert_called_once()


class TestNamingCounters(IntegrationTestCase):
	"""Upgraded sites: legacy records were numbered from per-prefix counters, but format: names in
	Framework 16 use one shared counter, which could sit below numbers already taken."""

	def test_counter_moves_past_numbers_in_use(self):
		from thinknxg_estate.core.naming import highest_number_in_use, sync_naming_counters
		from thinknxg_estate.tests.test_estate_integration import company

		frappe.get_doc({"doctype": "Property Owner", "owner_name": "Counter Probe", "company": company()}).insert()
		top = highest_number_in_use()
		frappe.db.sql("UPDATE `tabSeries` SET current = 0 WHERE name = ''")  # the legacy state
		sync_naming_counters()
		owner = frappe.get_doc({"doctype": "Property Owner", "owner_name": "Counter Probe 2",
		                        "company": company()}).insert()
		self.assertGreater(int(owner.name.rsplit("-", 1)[1]), top)

	def test_never_moves_backwards(self):
		from thinknxg_estate.core.naming import sync_naming_counters

		frappe.db.sql("UPDATE `tabSeries` SET current = 999999 WHERE name = ''")
		sync_naming_counters()
		self.assertEqual(frappe.db.sql("SELECT current FROM `tabSeries` WHERE name = ''")[0][0], 999999)
