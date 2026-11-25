"""Generated images and documents for the demo dataset. Everything is drawn here with Pillow, so the
dataset ships no third-party photographs and no real documents."""

import io
import math
import random

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 800

PALETTES = {
	"dusk": ((255, 183, 120), (92, 76, 148), (28, 33, 71)),
	"day": ((165, 214, 247), (222, 241, 252), (68, 96, 128)),
	"gold": ((255, 214, 150), (244, 160, 110), (74, 56, 94)),
	"night": ((18, 28, 58), (46, 64, 112), (10, 14, 30)),
	"teal": ((150, 224, 218), (214, 244, 240), (30, 84, 96)),
}


def _font(size, bold=False):
	for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
	             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
	             "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
		try:
			return ImageFont.truetype(path, size)
		except OSError:
			continue
	return ImageFont.load_default()


def _gradient(top, bottom, w=W, h=H):
	img = Image.new("RGB", (w, h))
	px = img.load()
	for y in range(h):
		t = y / (h - 1)
		row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
		for x in range(w):
			px[x, y] = row
	return img


def _png(img):
	buf = io.BytesIO()
	img.save(buf, "PNG", optimize=True)
	return buf.getvalue()


def _caption(draw, text, sub=None):
	draw.rectangle([0, H - 118, W, H], fill=(10, 20, 40))
	draw.text((44, H - 100), text, font=_font(40, True), fill=(255, 255, 255))
	if sub:
		draw.text((46, H - 52), sub, font=_font(24), fill=(190, 205, 225))


def exterior(seed, title, sub, palette="dusk", towers=5, low_rise=False):
	"""A stylised skyline or compound elevation."""
	rnd = random.Random(seed)
	top, mid, ground = PALETTES[palette]
	img = _gradient(top, mid)
	d = ImageDraw.Draw(img)
	# sun
	d.ellipse([W * 0.72, 90, W * 0.72 + 120, 210], fill=(255, 236, 190))
	base = H - 118
	# background skyline
	x = -20
	while x < W:
		bw = rnd.randint(70, 130)
		bh = rnd.randint(120, 300)
		shade = tuple(int(c * 0.72 + 40) for c in mid)
		d.rectangle([x, base - bh, x + bw, base], fill=shade)
		x += bw + rnd.randint(4, 18)
	# hero buildings
	n = towers
	span = W - 240
	for i in range(n):
		bw = int(span / n) - 24
		bx = 120 + i * (bw + 24)
		bh = rnd.randint(190, 300) if low_rise else rnd.randint(330, 560)
		col = tuple(int(c * 0.62) for c in ground) if palette != "night" else (22, 30, 56)
		d.rectangle([bx, base - bh, bx + bw, base], fill=col)
		d.rectangle([bx + bw // 2 - 6, base - bh - 36, bx + bw // 2 + 6, base - bh], fill=col)
		cols, rows = max(bw // 26, 2), max(bh // 34, 3)
		for r in range(rows):
			for c in range(cols):
				if rnd.random() < 0.68:
					wx = bx + 12 + c * ((bw - 24) // cols)
					wy = base - bh + 18 + r * ((bh - 30) // rows)
					lit = (255, 226, 150) if rnd.random() < 0.7 else (180, 214, 240)
					d.rectangle([wx, wy, wx + 11, wy + 16], fill=lit)
	# ground / water line
	d.rectangle([0, base - 10, W, base], fill=(26, 40, 66))
	_caption(d, title, sub)
	return _png(img)


def interior(seed, title, sub, wall=(236, 228, 214), accent=(31, 122, 140)):
	"""A stylised living-room elevation."""
	rnd = random.Random(seed)
	img = _gradient(wall, tuple(max(c - 22, 0) for c in wall))
	d = ImageDraw.Draw(img)
	floor_y = 520
	d.rectangle([0, floor_y, W, H - 118], fill=(172, 140, 108))
	for i in range(0, W, 120):
		d.line([i, floor_y, i - 60, H - 118], fill=(150, 120, 92), width=2)
	# window with skyline
	d.rectangle([760, 90, 1190, 430], fill=(226, 236, 244), outline=(90, 96, 108), width=10)
	d.rectangle([770, 100, 1180, 420], fill=_pick(rnd, [(180, 212, 240), (255, 205, 150)]))
	for i in range(7):
		bw = rnd.randint(34, 62)
		bx = 780 + i * 58
		bh = rnd.randint(70, 230)
		d.rectangle([bx, 420 - bh, bx + bw, 420], fill=(70, 86, 120))
	d.line([975, 100, 975, 420], fill=(90, 96, 108), width=8)
	# sofa
	d.rounded_rectangle([140, 380, 660, 560], radius=36, fill=accent)
	d.rounded_rectangle([120, 330, 220, 560], radius=30, fill=tuple(max(c - 20, 0) for c in accent))
	d.rounded_rectangle([580, 330, 680, 560], radius=30, fill=tuple(max(c - 20, 0) for c in accent))
	for i in range(3):
		d.rounded_rectangle([230 + i * 120, 360, 330 + i * 120, 450], radius=18,
		                    fill=tuple(min(c + 28, 255) for c in accent))
	# table & lamp
	d.rounded_rectangle([280, 620, 540, 660], radius=10, fill=(96, 70, 52))
	d.line([880, 300, 880, 560], fill=(60, 60, 60), width=8)
	d.ellipse([836, 250, 924, 320], fill=(255, 238, 190))
	# art
	d.rectangle([180, 120, 420, 290], fill=(246, 246, 246), outline=(60, 60, 60), width=8)
	d.ellipse([240, 160, 340, 260], fill=_pick(rnd, [(224, 112, 82), (240, 190, 90)]))
	_caption(d, title, sub)
	return _png(img)


def amenity(seed, title, sub, kind="pool"):
	"""A stylised amenity scene: pool, gym, lobby."""
	rnd = random.Random(seed)
	top, mid, _g = PALETTES["teal" if kind == "pool" else "day"]
	img = _gradient(top, mid)
	d = ImageDraw.Draw(img)
	if kind == "pool":
		d.rectangle([0, 360, W, H - 118], fill=(244, 230, 204))
		d.rounded_rectangle([140, 430, W - 140, H - 160], radius=60, fill=(66, 178, 214))
		for i in range(9):
			y = 470 + i * 14
			d.arc([180, y, W - 180, y + 40], 0, 180, fill=(150, 220, 240), width=3)
		for i in range(4):
			x = 200 + i * 260
			d.rectangle([x, 330, x + 18, 430], fill=(120, 90, 60))
			d.polygon([(x - 70, 335), (x + 88, 335), (x + 9, 270)], fill=_pick(rnd, [(226, 96, 80), (250, 200, 80)]))
		d.ellipse([W - 260, 70, W - 150, 180], fill=(255, 240, 190))
	elif kind == "gym":
		d.rectangle([0, 460, W, H - 118], fill=(68, 72, 82))
		for i in range(5):
			x = 120 + i * 230
			d.rounded_rectangle([x, 330, x + 150, 470], radius=14, fill=(40, 44, 54))
			d.rectangle([x + 20, 270, x + 130, 335], fill=(120, 190, 220))
			d.rectangle([x + 60, 470, x + 90, 560], fill=(30, 30, 38))
		d.rectangle([60, 130, W - 60, 300], fill=(190, 220, 236), outline=(60, 70, 80), width=8)
	else:
		d.rectangle([0, 520, W, H - 118], fill=(210, 196, 172))
		d.rectangle([420, 250, 860, 520], fill=(86, 70, 58))
		d.rectangle([450, 290, 830, 500], fill=(240, 232, 214))
		d.ellipse([560, 130, 720, 250], fill=(255, 238, 190))
		for i in range(3):
			d.rounded_rectangle([140 + i * 40, 420, 330 + i * 40, 520], radius=24, fill=(190, 150, 90))
	_caption(d, title, sub)
	return _png(img)


def avatar_pdf(title, lines):
	"""A one-page PDF used for property documents: a clearly fictional certificate."""
	img = Image.new("RGB", (1240, 1754), (252, 250, 245))
	d = ImageDraw.Draw(img)
	d.rectangle([40, 40, 1200, 1714], outline=(24, 56, 86), width=6)
	d.rectangle([70, 70, 1170, 1684], outline=(190, 160, 90), width=2)
	d.text((120, 150), title, font=_font(56, True), fill=(24, 56, 86))
	d.line([120, 240, 1120, 240], fill=(190, 160, 90), width=4)
	y = 320
	for line in lines:
		d.text((120, y), line, font=_font(34), fill=(40, 40, 40))
		y += 70
	d.text((120, 1560), "SAMPLE DOCUMENT - FICTIONAL DEMO DATA - NOT A REAL RECORD",
	       font=_font(28, True), fill=(160, 40, 40))
	buf = io.BytesIO()
	img.save(buf, "PDF", resolution=150)
	return buf.getvalue()


def _pick(rnd, options):
	return options[rnd.randrange(len(options))]
