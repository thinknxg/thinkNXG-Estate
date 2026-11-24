"""Generate docs/API.md from the code: every whitelisted endpoint, its access level and legacy alias.

Run from the repository root:  python3 scripts/generate_api_docs.py
"""

import ast
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "thinknxg_estate")
sys.path.insert(0, ROOT)

from thinknxg_estate.compat import LEGACY_METHODS  # noqa: E402

LEGACY_BY_NEW = {}
for old, new in LEGACY_METHODS.items():
	LEGACY_BY_NEW.setdefault(new, []).append(old)

SECTIONS = [
	("Staff console API (desk users with an estate or accounts role)", "core/api.py"),
	("CRM API (desk users with an estate or accounts role)", "crm/api.py"),
	("Public listings and visitor accounts (/listings)", "core/listing_portal_api/listing_portal.py"),
	("Public listings, inquiries and AI chat (/properties)", "portal/api/listings.py"),
	("Legacy inquiry form", "portal/api/inquiries.py"),
	("Listings AI chat", "portal/api/chat.py"),
	("Property Finder / Bayut feeds", "portal/api/feeds.py"),
	("Tenant portal (website login, role Tenant)", "portal/api/tenant.py"),
	("Access-code tenant portal (opt-in)", "core/tenant_portal_api.py"),
	("WhatsApp webhook (Meta Cloud API)", "voice/api/webhook.py"),
	("Other", None),
]


def describe(node):
	decos = [ast.unparse(d) for d in node.decorator_list]
	wl = next((d for d in decos if "whitelist" in d), None)
	if wl is None:
		return None
	guest = "allow_guest=True" in wl
	methods = "POST only" if "methods=['POST']" in wl or 'methods=["POST"]' in wl else "GET/POST"
	staff = any(d == "staff_only" for d in decos)
	rl = next((d for d in decos if d.startswith("rate_limit")), None)
	if staff:
		access = "Estate staff"
	elif guest:
		access = "Public (guest)"
	else:
		access = "Logged-in user (checked in code)"
	if rl:
		limit = rl[rl.index("(") + 1:-1].replace("limit=", "").replace("seconds=", "per ").replace(", ", " ")
		access += f"; rate limit {limit}s"
	doc = (ast.get_docstring(node) or "").strip().split("\n")[0]
	return access, methods, doc


def collect():
	rows = {}
	for dirpath, _, files in os.walk(APP):
		if "/tests" in dirpath or "/doctype/" in dirpath:
			continue
		for fn in files:
			if not fn.endswith(".py"):
				continue
			path = os.path.join(dirpath, fn)
			rel = os.path.relpath(path, APP)
			module = "thinknxg_estate." + rel[:-3].replace(os.sep, ".")
			tree = ast.parse(open(path).read())
			for node in tree.body:
				if isinstance(node, ast.FunctionDef):
					info = describe(node)
					if info:
						rows.setdefault(rel, []).append((f"{module}.{node.name}",) + info)
	return rows


def main():
	rows = collect()
	out = ["# thinkNXG Estate API reference", "",
	       "Generated from the code by `scripts/generate_api_docs.py`. Call any endpoint at",
	       "`/api/method/<path>` with a session cookie (and the `X-Frappe-CSRF-Token` header for POST),",
	       "or with token authentication (`Authorization: token <api_key>:<api_secret>`).", "",
	       "Access levels:", "",
	       "- **Estate staff**: desk (System User) accounts holding one of RE Manager, Property Manager,",
	       "  Leasing Officer, Maintenance Supervisor, RE Sales Manager, RE Sales Agent, Voice Ops Manager,",
	       "  Accounts User, Accounts Manager or System Manager. Document permissions still apply on top.",
	       "- **Public (guest)**: no login; every write is rate limited per IP.",
	       "- **Logged-in user**: identity is resolved server-side from the session (tenant portal, visitor",
	       "  account); IDs sent by the client are never trusted.", "",
	       "Legacy aliases: every `re_core.*`, `re_crm.*`, `re_portal.*` and `re_voice.*` path keeps working",
	       "and routes to the endpoint shown, so existing scripts, the Meta webhook registration and",
	       "portal feed registrations need no change.", "",
	       "Document actions (`run_doc_method`) such as *Post Dated Cheque → mark_cleared* check the",
	       "matching document permission (submit or write), not only read.", ""]
	done = set()
	for title, rel in SECTIONS:
		items = rows.get(rel, []) if rel else [r for k, v in sorted(rows.items()) if k not in done for r in v]
		if rel:
			done.add(rel)
		if not items:
			continue
		out += [f"## {title}", "", "| Endpoint | Access | HTTP | Description | Legacy path |",
		        "|---|---|---|---|---|"]
		for path, access, methods, doc, in items:
			legacy = "<br>".join(f"`{x}`" for x in LEGACY_BY_NEW.get(path, [])) or "—"
			out.append(f"| `{path}` | {access} | {methods} | {doc.replace('|', '/') or '—'} | {legacy} |")
		out.append("")
	with open(os.path.join(ROOT, "docs", "API.md"), "w") as f:
		f.write("\n".join(out) + "\n")
	print("endpoints documented:", sum(len(v) for v in rows.values()))


main()
