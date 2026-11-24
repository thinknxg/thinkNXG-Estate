"""Keep document numbering ahead of the numbers already in use.

Estate document types are named with `format:` patterns such as `format:TEN-{#####}`. In
thinkNXG Framework 16 every `{#...}` in a `format:` pattern draws from one shared counter (the
blank key in tabSeries). Records migrated from the legacy apps were numbered from older
per-prefix counters, so on an upgraded site that shared counter can sit below numbers that are
already taken, and the next new tenant, owner or property fails with a duplicate name.

sync_naming_counters() raises the shared counter to the highest number in use by any Estate
document type. It only ever moves the counter forward and runs on every migrate."""

import re

import frappe

BRACED = re.compile(r"\{([^}]+)\}")


def _name_regex(pattern):
	"""format:TEN-{#####} -> ^TEN\\-(\\d{5,})$ with one capture group for the counter."""
	out, pos, captured = "^", 0, False
	for m in BRACED.finditer(pattern):
		out += re.escape(pattern[pos:m.start()])
		token = m.group(1)
		if token.startswith("#") and not captured:
			out += rf"(\d{{{len(token)},}})"
			captured = True
		elif token in ("YYYY",):
			out += r"\d{4}"
		elif token in ("YY", "MM", "DD"):
			out += r"\d{2}"
		else:
			out += r".+?"
		pos = m.end()
	out += re.escape(pattern[pos:]) + "$"
	return re.compile(out) if captured else None


def estate_format_doctypes():
	return frappe.get_all(
		"DocType",
		filters={"module": ["in", frappe.get_all("Module Def", filters={"app_name": "thinknxg_estate"}, pluck="name")],
		         "autoname": ["like", "format:%{#%"], "istable": 0},
		fields=["name", "autoname"])


def highest_number_in_use():
	top = 0
	for dt in estate_format_doctypes():
		regex = _name_regex(dt.autoname[len("format:"):])
		if not regex:
			continue
		for name in frappe.get_all(dt.name, pluck="name", order_by="creation desc", limit=None):
			m = regex.match(name)
			if m:
				top = max(top, int(m.group(1)))
	return top


def sync_naming_counters():
	top = highest_number_in_use()
	current = frappe.db.sql("SELECT current FROM `tabSeries` WHERE name = ''")
	if not current:
		frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES ('', %s)", (top,))
		return {"from": None, "to": top}
	if current[0][0] < top:
		frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = ''", (top,))
		return {"from": current[0][0], "to": top}
	return {"from": current[0][0], "to": current[0][0]}
