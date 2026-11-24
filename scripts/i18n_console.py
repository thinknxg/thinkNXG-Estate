"""Mark the /re-portal console's user-facing strings for translation (one-off, idempotent).

HTML part (before the first <script>):
  * text nodes                -> {{ _("...") }}
  * placeholder / title attrs -> {{ _("...") }}
  * <option>X</option>        -> <option value="X">{{ _("X") }}</option>   (submitted value stays English)
Script part:
  * the screens table (title / bread / btn)          -> __('...')
  * first literal argument of showToast/alert/confirm -> __('...')
  * text between tags inside string literals          -> translated at runtime with __()

Usage: python scripts/i18n_console.py thinknxg_estate/www/re-portal/index.html
"""

import re
import sys

WORD = re.compile(r"[A-Za-z]{2,}")
SKIP_TEXT = {"N"}  # logo mark


def jinja_str(text):
	if '"' not in text:
		return '"' + text.replace("\\", "\\\\") + '"'
	return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def wrap_html(html):
	# <option>Text</option> without a value attribute: keep the English value, translate the label
	def option(m):
		attrs, text = m.group(1), m.group(2)
		if "value=" in attrs or not WORD.search(text) or "{{" in text:
			return m.group(0)
		value = text.strip().replace('"', "&quot;")
		return f'<option{attrs} value="{value}">{{{{ _({jinja_str(text.strip())}) }}}}</option>'

	html = re.sub(r"<option([^>]*)>([^<]*)</option>", option, html)

	def attr(m):
		name, text = m.group(1), m.group(2)
		if not WORD.search(text) or "{{" in text or "${" in text:
			return m.group(0)
		return f'{name}="{{{{ _({jinja_str(text)}) }}}}"'

	html = re.sub(r'\b(placeholder|title|aria-label)="([^"]*)"', attr, html)

	def node(m):
		text = m.group(1)
		core = text.strip()
		if (not WORD.search(core) or "{{" in core or "{%" in core or "&" in core or core in SKIP_TEXT
				or core.startswith(("//", "<!--"))):
			return m.group(0)
		lead = text[: len(text) - len(text.lstrip())]
		trail = text[len(text.rstrip()):]
		return f">{lead}{{{{ _({jinja_str(core)}) }}}}{trail}<"

	# text nodes, but not inside <style> or the inline print template
	return re.sub(r">([^<>]+)<", node, html)


# ---------------------------------------------------------------- script part

def _regex_allowed(js, i):
	"""A '/' starts a regex literal when it follows an operator, '(' ',' etc., or a keyword."""
	k = i - 1
	while k >= 0 and js[k] in " \t\r\n":
		k -= 1
	if k < 0:
		return True
	if js[k] in "(,=:[!&|?{};+-*%<>~^":
		return True
	word = re.search(r"([A-Za-z_$]+)$", js[: k + 1])
	return bool(word and word.group(1) in ("return", "typeof", "case", "in", "of", "delete", "void", "throw"))


def tokenize(js):
	"""Yield (kind, text) where kind is 'code', "'", '"' or '`' (template, ${...} kept inside)."""
	i, n, start = 0, len(js), 0
	out = []
	while i < n:
		c = js[i]
		if c == "/" and i + 1 < n and js[i + 1] in "/*":
			end = js.find("\n", i) if js[i + 1] == "/" else js.find("*/", i) + 2
			end = n if end <= 0 else end
			i = end
			continue
		if c == "/" and _regex_allowed(js, i):
			j, in_class = i + 1, False
			while j < n and js[j] != "\n":
				d = js[j]
				if d == "\\":
					j += 2
					continue
				if d == "[":
					in_class = True
				elif d == "]":
					in_class = False
				elif d == "/" and not in_class:
					break
				j += 1
			i = j + 1
			continue
		if c in "'\"`":
			out.append(("code", js[start:i]))
			j, depth = i + 1, 0
			while j < n:
				d = js[j]
				if d == "\\":
					j += 2
					continue
				if c == "`" and d == "$" and j + 1 < n and js[j + 1] == "{":
					depth += 1
					j += 2
					continue
				if c == "`" and d == "}" and depth:
					depth -= 1
					j += 1
					continue
				if d == c and not depth:
					break
				j += 1
			out.append((c, js[i: j + 1]))
			i = start = j + 1
			continue
		i += 1
	out.append(("code", js[start:]))
	return out


TAG_TEXT = re.compile(r"(?<=[A-Za-z0-9'\"/-])>([^<>${}]*[A-Za-z]{2,}[^<>${}]*)<(?=[/A-Za-z!])")


def js_literal(text, q):
	return q + text.replace("\\", "\\\\").replace(q, "\\" + q) + q


def split_template(body):
	"""Split a template-literal body into ('text', s) and ('expr', s) pieces (expr without ${ })."""
	pieces, i, n, start = [], 0, len(body), 0
	while i < n:
		if body[i] == "\\":
			i += 2
			continue
		if body.startswith("${", i):
			pieces.append(("text", body[start:i]))
			j, depth = i + 2, 1
			while j < n and depth:
				if body[j] in "'\"`":
					q, j = body[j], j + 1
					while j < n and body[j] != q:
						j += 2 if body[j] == "\\" else 1
				elif body[j] == "{":
					depth += 1
				elif body[j] == "}":
					depth -= 1
				j += 1
			pieces.append(("expr", body[i + 2: j - 1]))
			i = start = j
			continue
		i += 1
	pieces.append(("text", body[start:]))
	return pieces


def wrap_string(kind, lit):
	body = lit[1:-1]
	if kind == "`":
		out = []
		for part, chunk in split_template(body):
			if part == "expr":
				out.append("${" + wrap_code(chunk) + "}")
			else:
				out.append(wrap_plain("`", chunk))
		return "`" + "".join(out) + "`"
	return kind + wrap_plain(kind, body) + kind


def wrap_code(js):
	return "".join(text if kind == "code" else wrap_string(kind, text) for kind, text in tokenize(js))


def wrap_plain(kind, body):
	if "__(" in body:
		return body

	def repl(m):
		text = m.group(1)
		core = text.strip()
		if not WORD.search(core) or "&" in core or core.startswith(("http", "/", "#")) or "=" in core:
			return m.group(0)
		lead = text[: len(text) - len(text.lstrip())]
		trail = text[len(text.rstrip()):]
		if kind == "`":
			return ">" + lead + "${__(" + js_literal(core, "'") + ")}" + trail + "<"
		return ">" + lead + kind + " + __(" + js_literal(core.replace("\\" + kind, kind), "'") + ") + " + kind + trail + "<"

	return TAG_TEXT.sub(repl, body)


def wrap_script(js):
	# screens table
	def screen(m):
		return f"{m.group(1)}: __({m.group(2)})"

	start = js.find("const screens = {")
	end = js.find("};", start)
	if start != -1 and "__(" not in js[start:end]:
		block = re.sub(r"\b(title|bread|btn)\s*:\s*('[^']*')", screen, js[start:end])
		js = js[:start] + block + js[end:]

	# messages shown to the user
	js = re.sub(r"\b(showToast|alert|confirm)\((\s*)('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")",
	            lambda m: f"{m.group(1)}({m.group(2)}__({m.group(3)})" if WORD.search(m.group(3)) else m.group(0), js)

	return wrap_code(js)


def main(path):
	src = open(path, encoding="utf-8").read()
	body = src.index("<body>")
	script = src.index("<script>", body)
	head, html, rest = src[:body], src[body:script], src[script:]
	open(path, "w", encoding="utf-8").write(head + wrap_html(html) + wrap_script(rest))


if __name__ == "__main__":
	main(sys.argv[1])
