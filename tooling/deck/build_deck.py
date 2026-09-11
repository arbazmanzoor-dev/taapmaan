"""Build the Taapmaan SIH idea-submission deck (python-pptx), in the SIH template's format.

    python build_deck.py <scratch_dir> <out.pptx>

Every number comes from facts.json (computed from the project's own code and
data); every screenshot from shots/ (the running app). Text boxes are measured
against the real Calibri / Times New Roman / Arial metrics and any box whose
text would overflow is reported.
"""
import json, math, os, sys, glob
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image, ImageFont

P, OUT = sys.argv[1], sys.argv[2]
FX = json.load(open(f"{P}/facts.json"))
SH = f"{P}/shots"
LOGO = f"{P}/sih_logo_deck.png"
YEAR = "2026"
TEAM, TEAM_ID = "‹TEAM NAME›", "‹Team ID›"
WARN = []

# ---------------------------------------------------------------- palette ---
# Taapmaan "Civic Thermal Command" palette (matches the app); SIH template colours unchanged.
INK, INK2, MUTED, LINE, CARD = "1C1917", "57534E", "78716C", "E6E2DA", "F4F0EA"
SIH_BLUE, NAVY, OVAL = "006FC0", "1F497D", "8063A1"
BRAND, BRANDW = "C2410C", "FFF7ED"
R1, R2, R3, R4, R5 = "15803D", "B45309", "EA580C", "DC2626", "9333EA"
R1W, R2W, R3W, R4W, R5W = "F0FDF4", "FEF3C7", "FFEDD5", "FEF2F2", "FAF5FF"
D1, DB, D2, D3, D4, D5 = "15803D", "9A3412", "B45309", "C2410C", "DC2626", "9333EA"   # white-text-safe fills
rgb = RGBColor.from_string

# ------------------------------------------------------ text measurement ---
DF = "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts"
SUP = "/System/Library/Fonts/Supplemental"
def first(*c):
    return next((x for x in c if x and os.path.exists(x)), None)
gar_b = first(*[g for g in glob.glob(f"{DF}/*") if os.path.basename(g).lower().startswith(("garabd", "garamond bold"))])
FONTS = {("Calibri", False): f"{DF}/Calibri.ttf", ("Calibri", True): f"{DF}/Calibrib.ttf",
         ("Times New Roman", True): f"{SUP}/Times New Roman Bold.ttf", ("Times New Roman", False): f"{SUP}/Times New Roman.ttf",
         ("Arial", True): f"{SUP}/Arial Bold.ttf", ("Arial", False): f"{SUP}/Arial.ttf",
         ("Garamond", True): gar_b or f"{SUP}/Times New Roman Bold.ttf"}
if not gar_b:
    WARN.append("Garamond Bold metrics not found; measured with Times New Roman Bold (+ slack)")
_fc = {}
def _font(name, bold, size):
    k = (name, bool(bold), size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS.get((name, bool(bold))) or FONTS[("Calibri", bool(bold))], int(size * 10))
    return _fc[k]
def text_w(s, name, bold, size):
    return _font(name, bold, size).getlength(s) / 10 / 72
def n_lines(s, name, bold, size, width):
    total = 0
    for para in s.split("\n"):
        cur, n = "", 1
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if not cur or text_w(t, name, bold, size) <= width: cur = t
            else: n, cur = n + 1, w
        total += n
    return total

# --------------------------------------------------------------- helpers ---
def _bullet(p, spec):
    pPr = p._p.get_or_add_pPr()
    ind = int(Inches(spec.get("indent", 0.22)))
    pPr.set("marL", str(ind)); pPr.set("indent", str(-ind))
    if spec.get("color"):
        c = etree.SubElement(pPr, qn("a:buClr")); etree.SubElement(c, qn("a:srgbClr")).set("val", spec["color"])
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", spec.get("char", "•"))

def txt(sl, x, y, w, h, paras, size=14, color=INK, font="Calibri", bold=False, italic=False,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=0, line=1.0, bullet=None, spc=None, check=True):
    """paras: str | list of paragraphs; paragraph = str | (text, opts) | list of runs."""
    if isinstance(paras, (str, tuple)): paras = [paras]
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    est, label = 0.0, ""
    for i, pa in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = line
        runs = [pa] if isinstance(pa, (str, tuple)) else pa
        ptxt, psize, pbold, pfont = "", size, bold, font
        for j, r in enumerate(runs):
            t, o = (r, {}) if isinstance(r, str) else r
            run = p.add_run(); run.text = t
            f = run.font; f.name = o.get("font", font); f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold); f.italic = o.get("italic", italic); f.color.rgb = rgb(o.get("color", color))
            if spc or o.get("spc"): run._r.get_or_add_rPr().set("spc", str(o.get("spc", spc)))
            if o.get("link"): run.hyperlink.address = o["link"]
            ptxt += t
            if j == 0: psize, pfont = o.get("size", size), o.get("font", font)
            pbold = pbold or o.get("bold", bold)
        sa = space_after if i < len(paras) - 1 else 0
        p.space_after = Pt(sa)
        bw = w
        if bullet:
            _bullet(p, bullet); bw = w - bullet.get("indent", 0.22)
        est += n_lines(ptxt, pfont, pbold, psize, bw) * psize * 1.2 * line / 72 + sa / 72
        label = label or ptxt[:34]
    slack = 1.10 if font == "Garamond" else 1.02
    if check and est > h * slack:
        WARN.append(f"slide {CUR[0]}: '{label}' needs {est:.2f}in, box {h:.2f}in")
    return tb

def _shadow(shape, blur=5, dist=1.5, alpha=16):
    spPr = shape._element.spPr
    for e in spPr.findall(qn("a:effectLst")): spPr.remove(e)
    el = etree.SubElement(spPr, qn("a:effectLst"))
    sh = etree.SubElement(el, qn("a:outerShdw"))
    for k, v in (("blurRad", int(Pt(blur))), ("dist", int(Pt(dist))), ("dir", 5400000), ("algn", "t"), ("rotWithShape", 0)):
        sh.set(k, str(v))
    c = etree.SubElement(sh, qn("a:srgbClr")); c.set("val", "000000")
    etree.SubElement(c, qn("a:alpha")).set("val", str(alpha * 1000))

def box(sl, x, y, w, h, fill=None, line=None, lw=0.75, shape=MSO_SHAPE.RECTANGLE, radius=None, shadow=False):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius is not None: s.adjustments[0] = min(0.5, radius / min(w, h))
    if fill: s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    else: s.fill.background()
    if line: s.line.color.rgb = rgb(line); s.line.width = Pt(lw)
    else: s.line.fill.background()
    if shadow: _shadow(s)
    else: s.shadow.inherit = False
    return s

def shape_text(s, text, size, color, bold=True, font="Calibri", align=PP_ALIGN.CENTER,
               anchor=MSO_ANCHOR.MIDDLE, mx=0.06, my=0.03, italic=False):
    tf = s.text_frame; tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Inches(mx); tf.margin_top = tf.margin_bottom = Inches(my)
    tf.vertical_anchor = anchor
    paras = text.split("\n")
    for i, t in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
        r = p.add_run(); r.text = t
        f = r.font; f.size = Pt(size); f.bold = bold; f.italic = italic; f.name = font; f.color.rgb = rgb(color)

def hexagon(sl, cx, cy, r, fill, line=None, lw=1.0):
    pts = [(cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    fb = sl.shapes.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]), scale=1.0)
    fb.add_line_segments([(Inches(a), Inches(b)) for a, b in pts[1:]], close=True)
    s = fb.convert_to_shape()
    s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    if line: s.line.color.rgb = rgb(line); s.line.width = Pt(lw)
    else: s.line.fill.background()
    s.shadow.inherit = False
    return s

def arrow(sl, x1, y1, x2, y2, color="A8A29E", lw=1.25):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(lw)
    t = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")
    return c

def connector(sl, x1, y1, x2, y2, color=LINE, lw=1.25):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(lw)
    return c

def pic(sl, path, x, y, w=None, h=None, border="D6D1C7", shadow=True):
    im = Image.open(path); ar = im.width / im.height
    if w and not h: h = w / ar
    if h and not w: w = h * ar
    p = sl.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    if border: p.line.color.rgb = rgb(border); p.line.width = Pt(0.75)
    if shadow: _shadow(p)
    return p, w, h

def label(sl, x, y, text, color=INK2, hexc=None, w=6.0, size=11):
    hexagon(sl, x + 0.075, y + 0.105, 0.075, hexc or color)
    txt(sl, x + 0.21, y, w, 0.24, text.upper(), size=size, bold=True, color=color, spc=60, check=False)

CUR = [0]
def chrome(sl, n, title):
    CUR[0] = n
    ov = box(sl, 0.0, 0.05, 2.75, 0.62, fill="FFFFFF", line=OVAL, lw=1.75, shape=MSO_SHAPE.OVAL)
    shape_text(ov, TEAM, 16, "000000", bold=True, font="Times New Roman")
    size, W = 40, 7.9
    while text_w(title, "Times New Roman", True, size) > W - 0.1 and size > 30: size -= 1
    txt(sl, 2.85, 0.02, W, 0.8, (title, {}), size=size, font="Times New Roman", bold=True, color="000000",
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_logo(sl, right=13.22, y=0.03, h=0.78)
    box(sl, 0, 7.11, 13.333, 0.39, fill=SIH_BLUE)       # template footer (part of the SIH format)
    txt(sl, 3.0, 7.11, 7.333, 0.39, "@SIH Idea submission- Template", size=12, color="FFFFFF",
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, check=False)
    txt(sl, 12.33, 7.11, 0.7, 0.39, str(n), size=12, bold=True, color="FFFFFF",
        align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, check=False)

def add_logo(sl, right, y, h):
    if not os.path.exists(LOGO):
        WARN.append("SIH logo file missing -- logo slot left empty"); return
    im = Image.open(LOGO); w = h * im.width / im.height
    sl.shapes.add_picture(LOGO, Inches(right - w), Inches(y), Inches(w), Inches(h))

# ---------------------------------------------------------- image prep ---
os.makedirs(f"{P}/deckimg", exist_ok=True)
def prep(src, name, box_frac=None, square_top=False, maxw=2400):
    im = Image.open(f"{SH}/{src}").convert("RGB")
    if square_top: im = im.crop((0, 0, im.width, min(im.width, im.height)))
    if box_frac: im = im.crop((0, 0, im.width, int(im.height * box_frac)))
    if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    out = f"{P}/deckimg/{name}"; im.save(out, quality=88, optimize=True); return out
IMG_HERO = prep("hero_scenario.jpg", "hero.jpg")
IMG_CMD = prep("command_centre_drill.jpg", "command.jpg", box_frac=0.375)
IMG_BUL = prep("bulletin_top.jpg", "bulletin.jpg", square_top=True, maxw=1400)
IMG_BRD = prep("broadcast_gujarati.jpg", "broadcast.jpg", maxw=1400)

# ------------------------------------------------------------------ deck ---
pres = Presentation()
pres.slide_width, pres.slide_height = Inches(13.333), Inches(7.5)
BLANK = pres.slide_layouts[6]
pres.core_properties.title = "Taapmaan — SIH26083 idea submission"
pres.core_properties.author = "Taapmaan team"

# ===== 1. TITLE ============================================================
s = pres.slides.add_slide(BLANK); CUR[0] = 1
head = f"SMART INDIA HACKATHON {YEAR}"; hs = 40
while text_w(head, "Garamond", True, hs) * 1.06 > 9.6 and hs > 32: hs -= 1
txt(s, 0.35, 0.28, 10.0, 0.85, (head, {}), size=hs, font="Garamond", bold=True, color=NAVY,
    align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
add_logo(s, right=13.15, y=0.14, h=1.12)
items = [("Problem Statement ID – ", "SIH26083"),
         ("Problem Statement Title – ", "Extreme Heatwave Early Warning and Human Thermal Stress Index"),
         ("Theme – ", "Disaster Management"), ("PS Category – ", "Software"),
         ("Organisation – ", "Ministry of Earth Sciences (MoES)"),
         ("Team ID – ", TEAM_ID), ("Team Name – ", TEAM)]
txt(s, 0.5, 1.5, 6.95, 5.55, [[(a, {}), (b, {"font": "Calibri", "size": 23})] for a, b in items],
    size=21, font="Arial", bold=True, color="000000", space_after=15, bullet={"char": "•", "indent": 0.34})
# the product's own motif: a ward-level hex heat map
cx, cy, r = 10.28, 3.62, 0.5
ring1 = [R4, R5, R4, R4, R5, R4]
ring2 = [R3, R2, R3, R1, R2, R3, R2, R1, R3, R2, R3, R2]
cells = [(q, rr) for q in range(-2, 3) for rr in range(-2, 3) if (abs(q) + abs(q + rr) + abs(rr)) // 2 <= 2]
i1 = i2 = 0
for q, rr in sorted(cells, key=lambda c: (c[1], c[0])):
    d = (abs(q) + abs(q + rr) + abs(rr)) // 2
    x = cx + r * math.sqrt(3) * (q + rr / 2); y = cy + r * 1.5 * rr
    col = R5 if d == 0 else (ring1[i1 % 6] if d == 1 else ring2[i2 % 12])
    if d == 1: i1 += 1
    if d == 2: i2 += 1
    hx = hexagon(s, x, y, r * 0.93, col)
    if d == 0:
        shape_text(hx, "HTSI\n82", 15, "FFFFFF", bold=True)
txt(s, 7.7, 6.0, 5.2, 0.5, [[("Taapmaan", {"bold": True, "color": BRAND, "size": 24}),
                             ("  ·  Heat Action Console", {"color": INK2, "size": 16})]], size=16)
txt(s, 7.7, 6.5, 5.3, 0.4, "From what the weather will be — to what it will do to people.",
    size=13.5, italic=True, color=MUTED)
s.notes_slide.notes_text_frame.text = (
    "Problem SIH26083 from the Ministry of Earth Sciences: heat warnings in India key off air temperature, "
    "but humidity, wind and sun decide what heat does to a body. Taapmaan turns the forecast into ward-level "
    "thermal stress, projected deaths and hospital load, and into actions each department owns. "
    "Replace ‹Team Name› and ‹Team ID› (Find & Replace) before submitting.")

# ===== 2. IDEA =============================================================
s = pres.slides.add_slide(BLANK); chrome(s, 2, "IDEA: TAAPMAAN")
sm = FX["same40"]; a, b = sm["20"], sm["70"]
label(s, 0.3, 0.95, "The gap — same thermometer, different danger", color=D4)
txt(s, 0.3, 1.25, 6.2, 0.3, "Both cards: 40 °C air temperature, afternoon sun (800 W/m²), light breeze.",
    size=11.5, italic=True, color=MUTED)
def verdict(w): return ("Above 31 °C — suspend outdoor work", D4) if w >= 31 else ("Below 31 °C — work with rest breaks", D2)
for k, (rh, v, fill, col) in enumerate(((20, a, R2W, D2), (70, b, R4W, D4))):
    x = 0.3 + k * 3.15
    box(s, x, 1.62, 3.0, 1.95, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.09)
    txt(s, x + 0.18, 1.74, 2.7, 0.3, f"40 °C  ·  {rh} % humidity", size=13, bold=True, color=INK)
    txt(s, x + 0.18, 2.05, 2.7, 0.62, [[(f"{v['wbgt']:.1f}", {"size": 34, "bold": True, "color": col}),
                                        (" °C WBGT", {"size": 14, "bold": True, "color": col})]], size=14)
    txt(s, x + 0.18, 2.7, 2.7, 0.3, f"Heat Index {v['hi']:.0f} °C  ·  wet-bulb {v['wet_bulb']:.1f} °C",
        size=11, color=INK2)
    vt, vc = verdict(v["wbgt"])
    chip = box(s, x + 0.18, 3.07, 2.64, 0.34, fill=vc, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    shape_text(chip, vt, 10.5, "FFFFFF")
label(s, 0.3, 3.8, "Why today's warnings miss it", color=INK2, hexc=R4)
gaps = [("Air temperature only", " — humidity, wind and sun are ignored"),
        ("District-level", " — misses the heat-island gap between wards"),
        ("No health translation", " — '40 °C' does not say who ends up in hospital"),
        ("No trigger", " — nothing tells departments what to do, or checks they did")]
txt(s, 0.3, 4.12, 6.2, 1.05, [[(t, {"bold": True}), (d, {})] for t, d in gaps], size=12, color=INK,
    space_after=3, bullet={"char": "•", "indent": 0.2, "color": R4})
_, _, hh = pic(s, IMG_HERO, 6.72, 0.98, w=6.3)
txt(s, 6.72, 0.98 + hh + 0.06, 6.3, 0.25, "Taapmaan console · Ahmedabad, May-peak drill · 37 ward cells coloured by HTSI",
    size=10, italic=True, color=MUTED)
label(s, 0.3, 5.28, "How it works — end to end", color=INK2, hexc=BRAND)
stages = [("1  Sense", D1, "Open-Meteo hourly forecast, ERA5 history, Census 2011"),
          ("2  Compute", DB, "WBGT, UTCI and Heat Index at the peak-stress hour"),
          ("3  Localise", D2, "37 ward cells per city with heat-island downscaling"),
          ("4  Predict", D3, "HTSI, excess deaths, ED load; D+1…D+5 learned forecast"),
          ("5  Alert", D4, "Ward map, auto alerts, SMS/WhatsApp in EN · HI · GU"),
          ("6  Act", D5, "20 HAP actions with owners, deadlines, bulletin, audit")]
for k, (t, c, d) in enumerate(stages):
    x = 0.3 + k * 2.12
    sh = box(s, x, 5.6, 2.2, 0.46, fill=c, shape=MSO_SHAPE.PENTAGON if k == 0 else MSO_SHAPE.CHEVRON)
    shape_text(sh, t, 13, "FFFFFF", mx=0.28 if k else 0.12)
    txt(s, x + 0.14, 6.14, 1.95, 0.88, d, size=10.5, color=INK2)
s.notes_slide.notes_text_frame.text = (
    f"Same 40 °C: at 20 % humidity WBGT is {a['wbgt']:.1f} °C; at 70 % it is {b['wbgt']:.1f} °C, wet-bulb "
    f"{b['wet_bulb']:.1f} °C. That gap is the whole problem statement. Traditional warnings cannot see it. "
    "Taapmaan computes WBGT, UTCI and Heat Index for every ward, adds overnight non-recovery and multi-day "
    "accumulation into one Human Thermal Stress Index, links it to mortality, and hands departments actions.")

# ===== 3. TECHNICAL APPROACH ===============================================
s = pres.slides.add_slide(BLANK); chrome(s, 3, "TECHNICAL APPROACH")
label(s, 0.3, 0.95, "Tech stack", color=INK2, hexc=BRAND)
stack = [("Data", D1, "Open-Meteo forecast + ERA5 archive · Census 2011 · NDMA HAP structure"),
         ("Science", DB, "Stull wet-bulb · ISO 7243 WBGT · UTCI (Bröde 2012) · NWS Heat Index"),
         ("ML", D3, "scikit-learn gradient boosting · 13 years of ERA5 · temporal split"),
         ("Backend", D4, "Python · FastAPI · SQLite · APScheduler · httpx"),
         ("Frontend", D5, "HTML/CSS/JS · SVG hex map · light & dark · no framework"),
         ("Alerts", D2, "REST API + webhook · SMS/WhatsApp advisories as dry runs; gateway next"),
         ("Deploy", "57534E", "Docker · Render blueprint · one-command run.sh")]
for k, (t, c, d) in enumerate(stack):
    y = 1.3 + k * 0.78
    chip = box(s, 0.3, y + 0.02, 0.98, 0.3, fill=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
    shape_text(chip, t, 10.5, "FFFFFF")
    txt(s, 1.4, y, 2.85, 0.66, d, size=10.5, color=INK2)
label(s, 4.5, 0.95, "Architecture", color=INK2, hexc=BRAND)
arch = [("Sources", "Open-Meteo hourly · ERA5 archive · Census 2011", R1W),
        ("ingest.py", "peak-stress-hour picker · 10-day history · 30-min scheduler", CARD),
        ("thermal.py", "WBGT · UTCI · Heat Index · wet-bulb · HTSI", CARD),
        ("wards.py + census.py", "37 cells per city · heat-island downscaling · provenance", CARD),
        ("ml.py", "D+1/3/5 gradient boosting · 13-year climatology", CARD),
        ("FastAPI + SQLite", f"{FX['api_operations']} API operations · actions · audit · subscribers", BRANDW)]
AX, AW = 4.5, 4.4
for k, (t, d, fill) in enumerate(arch):
    y = 1.3 + k * 0.7
    box(s, AX, y, AW, 0.52, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
    txt(s, AX + 0.14, y + 0.05, AW - 0.28, 0.44, [[(t, {"bold": True, "color": INK}), ("   " + d, {"color": INK2, "size": 9.5})]],
        size=11, anchor=MSO_ANCHOR.MIDDLE)
    if k < len(arch) - 1:
        arrow(s, AX + AW / 2, y + 0.52, AX + AW / 2, y + 0.7)
outs = ["Dashboard", "Bulletin", "Broadcast", "Webhook"]
yo = 1.3 + len(arch) * 0.7 + 0.02
arrow(s, AX + AW / 2, yo - 0.2, AX + AW / 2, yo)
ow = (AW - 3 * 0.1) / 4
for k, t in enumerate(outs):
    o = box(s, AX + k * (ow + 0.1), yo, ow, 0.4, fill=[D1, DB, D4, D5][k], shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
    shape_text(o, t, 10.5, "FFFFFF")
fy = yo + 0.55
box(s, AX, fy, AW, 7.0 - fy, fill=R5W, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
txt(s, AX + 0.16, fy + 0.08, AW - 0.32, 7.0 - fy - 0.14,
    [[("HTSI (0–100) ", {"bold": True, "color": D5}),
      ("= 0.34·WBGT + 0.26·UTCI + 0.16·HI + 0.14·night minimum + 0.10·heat-run days, each normalised", {})],
     [("Excess deaths ", {"bold": True, "color": D5}),
      ("= baseline × (e^(0.10·(HTSI−45)/10) − 1) × ward vulnerability", {})]],
    size=10, color=INK2, space_after=4)
label(s, 9.1, 0.95, "What officials get", color=INK2, hexc=BRAND)
_, _, h1 = pic(s, IMG_CMD, 9.1, 1.3, w=3.93)
txt(s, 9.1, 1.3 + h1 + 0.05, 3.93, 0.22, "Command centre — actions, deadlines, resource gaps", size=9.5, italic=True, color=MUTED)
y2 = 1.3 + h1 + 0.42
_, _, hb = pic(s, IMG_BUL, 9.1, y2, w=1.9)
pic(s, IMG_BRD, 11.13, y2, w=1.9, h=hb)
txt(s, 9.1, y2 + hb + 0.05, 1.9, 0.22, "Daily bulletin (draft)", size=9.5, italic=True, color=MUTED)
txt(s, 11.13, y2 + hb + 0.05, 1.9, 0.22, "Gujarati WhatsApp advisory", size=9.5, italic=True, color=MUTED)
sy = y2 + hb + 0.38
box(s, 9.1, sy, 3.93, 7.0 - sy, fill=BRANDW, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
txt(s, 9.24, sy + 0.08, 3.65, 7.0 - sy - 0.14,
    [[("Safe by design: ", {"bold": True, "color": DB}),
      ("drills can't reach the public, broadcasts are dry runs only, and no endpoint can wipe live records.", {})]],
    size=10, color=INK2)
s.notes_slide.notes_text_frame.text = (
    "Every index is a published formula — Stull 2011 wet-bulb, ISO 7243 WBGT, UTCI per Bröde 2012, NWS Heat Index — "
    "so a reviewer can audit the arithmetic. The backend pulls Open-Meteo every 30 minutes, finds each day's "
    "peak-STRESS hour rather than the hottest hour, downscales to 37 ward cells with Census 2011 anchors, and "
    f"serves {FX['api_operations']} documented API operations. Officials get the command centre, a signed "
    "bulletin and vernacular advisories.")

# ===== 4. FEASIBILITY AND VIABILITY ========================================
s = pres.slides.add_slide(BLANK); chrome(s, 4, "FEASIBILITY AND VIABILITY")
label(s, 0.3, 0.95, "Feasibility — already built and running", color=INK2, hexc=D1)
tiles = [("5", "cities on live forecasts", D4), ("185", "ward cells with Census 2011 anchors", DB),
         (f"{FX['era5_days_total']:,}", "city-days of ERA5 training data", D3),
         (str(FX["api_operations"]), "API operations, documented at /docs", DB),
         ("20 × 11", "HAP actions × departments", D5), ("0", "paid APIs or licences", D1)]
for k, (n, t, c) in enumerate(tiles):
    x = 0.3 + (k % 3) * 2.13; y = 1.3 + (k // 3) * 1.33
    box(s, x, y, 1.98, 1.2, fill=CARD, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    txt(s, x + 0.15, y + 0.1, 1.7, 0.55, n, size=28, bold=True, color=c)
    txt(s, x + 0.15, y + 0.66, 1.72, 0.48, t, size=10.5, color=INK2)
M = FX["model"]
cd = CategoryChartData(); cd.categories = ["D+1", "D+3", "D+5"]
cd.add_series("Taapmaan model", [M[h]["model"]["mae"] for h in ("d1", "d3", "d5")])
cd.add_series("Persistence", [M[h]["baseline_persistence"]["mae"] for h in ("d1", "d3", "d5")])
cd.add_series("Climatology", [M[h]["baseline_climatology"]["mae"] for h in ("d1", "d3", "d5")])
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(6.75), Inches(0.92), Inches(6.28), Inches(2.95), cd)
ch = gf.chart
ch.has_title = True; ch.chart_title.text_frame.text = "Forecast error (MAE, °C) — lower is better"
tr = ch.chart_title.text_frame.paragraphs[0].runs[0].font; tr.size = Pt(12); tr.bold = True; tr.color.rgb = rgb(INK)
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(10); ch.legend.font.color.rgb = rgb(INK2)
pl = ch.plots[0]; pl.gap_width = 70; pl.overlap = -8
pl.has_data_labels = True; dl = pl.data_labels
dl.number_format = "0.00"; dl.number_format_is_linked = False; dl.position = XL_LABEL_POSITION.OUTSIDE_END
dl.font.size = Pt(9); dl.font.color.rgb = rgb(INK2)
for ser, c in zip(pl.series, (BRAND, "A8A29E", "D9B24C")):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(c)
va = ch.value_axis; va.minimum_scale = 0; va.maximum_scale = 1.8; va.major_unit = 0.5
va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = rgb("E6E2DA")
va.tick_labels.font.size = Pt(9); va.tick_labels.font.color.rgb = rgb(MUTED); va.format.line.fill.background()
va.tick_labels.number_format = "0.0"; va.tick_labels.number_format_is_linked = False
ca = ch.category_axis; ca.tick_labels.font.size = Pt(10); ca.tick_labels.font.color.rgb = rgb(INK2)
ca.format.line.color.rgb = rgb(LINE)
sk = [f"{M[h]['skill_vs_persistence'] * 100:+.1f}%" for h in ("d1", "d3", "d5")]
n_test = M["d3"]["n_test"]
hot = M["d3"]["hottest_10pct_days"]
txt(s, 6.75, 3.9, 6.28, 0.42,
    f"Tested on {n_test:,} held-out city-days (2023–25). Beats both baselines on average — but on each city's "
    f"hottest 10% of days it reads {abs(hot['model_bias']):.1f} °C low at D+3 and trails persistence "
    f"({hot['model_mae']:.2f} vs {hot['persistence_mae']:.2f} °C), so warnings use the physics forecast, not this model.",
    size=9, italic=True, color=MUTED)
label(s, 0.3, 4.3, "SWOT", color=INK2, hexc=D3)
swot = [("Strengths", D1, R1W, ["Physics-based, auditable indices", "Ward-level and mortality-linked", "Open data; runs on one small server"]),
        ("Weaknesses", D3, R3W, ["Ward splits and capacity partly modelled", "Mortality model parametric, not fitted", "No sign-in yet"]),
        ("Opportunities", DB, BRANDW, ["Any city = one config entry + Census join", "Bias-correct with IMD station data", "Link 108 and hospital feeds"]),
        ("Threats", D4, R4W, ["Daily mortality data not public", "Alert fatigue if thresholds untuned", "SOPs need official sign-off"])]
for k, (t, c, fill, pts) in enumerate(swot):
    x = 0.3 + (k % 2) * 3.17; y = 4.62 + (k // 2) * 1.2
    box(s, x, y, 3.07, 1.1, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    txt(s, x + 0.14, y + 0.07, 2.8, 0.24, t, size=11.5, bold=True, color=c)
    txt(s, x + 0.14, y + 0.33, 2.85, 0.74, pts, size=9.5, color=INK2, space_after=1,
        bullet={"char": "•", "indent": 0.16, "color": c})
label(s, 6.75, 4.3, "Viability — path to adoption", color=INK2, hexc=D5)
steps = [("Pilot", "One corporation's heat season, drills first"),
         ("Localise", "Ward boundaries, Census join, capacity register"),
         ("Harden", "Government SSO, state data-centre hosting"),
         ("Scale", "Every city with a Heat Action Plan")]
sw = 6.28 / 4
connector(s, 6.75 + sw / 2, 4.9, 6.75 + sw * 3.5, 4.9, color=LINE, lw=2)
for k, (t, d) in enumerate(steps):
    x = 6.75 + k * sw
    c = box(s, x + sw / 2 - 0.2, 4.7, 0.4, 0.4, fill=[D1, DB, D3, D5][k], shape=MSO_SHAPE.OVAL)
    shape_text(c, str(k + 1), 13, "FFFFFF", mx=0, my=0)
    txt(s, x + 0.06, 5.17, sw - 0.12, 0.26, t, size=12, bold=True, color=INK, align=PP_ALIGN.CENTER)
    txt(s, x + 0.06, 5.45, sw - 0.12, 0.62, d, size=10, color=INK2, align=PP_ALIGN.CENTER)
box(s, 6.75, 6.2, 6.28, 0.72, fill=CARD, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
txt(s, 6.9, 6.27, 6.0, 0.6, [[("Running cost: ", {"bold": True}),
    ("open data and an open-source stack in one container. The only per-use cost is the SMS/WhatsApp "
     "gateway, billed per message — and every broadcast is a dry run until a gateway is integrated.", {})]],
    size=10, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text = (
    "This is not a mock-up: five cities run on live forecasts today. The learned forecaster is trained on 13 years "
    "of ERA5 and tested on years it never saw; it beats both honest baselines on average at every horizon — but NOT on the hottest days, where it "
    "reads low and trails persistence; that is why warnings come from the physics forecast. Point at the "
    "shape, not the wins: skill over persistence grows with horizon, skill over climatology shrinks — "
    "predictability decays. The SWOT names our real gaps: modelled capacity data, a parametric mortality model, "
    "no sign-in yet.")

# ===== 5. IMPACT AND BENEFITS ==============================================
s = pres.slides.add_slide(BLANK); chrome(s, 5, "IMPACT AND BENEFITS")
label(s, 0.3, 0.95, "Why it matters — evidence", color=INK2, hexc=D4)
txt(s, 0.3, 1.25, 3.9, 0.82, "1,344", size=46, bold=True, color=D4)
txt(s, 0.3, 2.08, 3.9, 0.7, "excess deaths in Ahmedabad in the May 2010 heat wave — all-cause mortality up 43.1%",
    size=12, color=INK)
txt(s, 0.3, 2.78, 3.9, 0.25, "Azhar et al., PLOS ONE, 2014", size=9.5, italic=True, color=MUTED)
txt(s, 0.3, 3.2, 3.9, 0.82, "≈1,190", size=46, bold=True, color=D1)
txt(s, 0.3, 4.03, 3.9, 0.7, "deaths avoided per year after Ahmedabad's Heat Action Plan (2014–15 vs 2007–10)",
    size=12, color=INK)
txt(s, 0.3, 4.73, 3.9, 0.25, "Hess et al., J. Environ. Public Health, 2018", size=9.5, italic=True, color=MUTED)
box(s, 0.3, 5.2, 3.9, 1.72, fill=BRANDW, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.09)
txt(s, 0.48, 5.32, 3.55, 1.5, "Heat action plans save lives. Taapmaan makes them ward-level, forecast-led and accountable.",
    size=15, italic=True, bold=True, color=DB, anchor=MSO_ANCHOR.MIDDLE)
label(s, 4.5, 0.95, "Who benefits", color=INK2, hexc=BRAND)
hcx, hcy = 6.7, 4.05
nodes = [("Municipal\nCommissioner", R5W, D5), ("Health dept\n& hospitals", R4W, D4), ("Labour\ndepartment", R3W, D3),
         ("Power & water\nutilities", R3W, D3), ("Elderly &\nvulnerable", R1W, D1), ("Outdoor\nworkers", R1W, D1),
         ("ASHA & 108\nfield staff", R4W, D4), ("Disaster\nMgmt Cell", R5W, D5)]
pos = []
for k in range(8):
    th = math.radians(-90 + k * 45)
    pos.append((hcx + 1.55 * math.cos(th), hcy + 2.28 * math.sin(th)))
for (nx, ny) in pos: connector(s, hcx, hcy, nx, ny, color=LINE, lw=1.5)
hub = box(s, hcx - 0.82, hcy - 0.82, 1.64, 1.64, fill=DB, shape=MSO_SHAPE.OVAL, shadow=True)
shape_text(hub, "Taapmaan", 15, "FFFFFF", mx=0.02)
for (t, fill, c), (nx, ny) in zip(nodes, pos):
    nb = box(s, nx - 0.68, ny - 0.29, 1.36, 0.58, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    shape_text(nb, t, 10, c, mx=0.04, my=0.02)
ben = [("Earlier", " — acts on the 72-hour peak, not the day of"), ("Targeted", " — ward cells, not whole districts"),
       ("Accountable", " — every action owned, timed, audited"), ("Inclusive", " — advisories in English, Hindi, Gujarati"),
       ("Affordable", " — open data, open-source, one server")]
kpi = ["Heat-illness ED visits vs the modelled load", "HAP actions completed before their deadline",
       "Advisory reach per ward, per language", "Summer excess deaths vs the city baseline"]
fut = ["Bias-correct forecasts with IMD station data", "Real ward boundaries on an H3 grid",
       "Government SSO; state data-centre hosting", "Fit mortality to real daily deaths (DLNM)",
       "Tamil, Marathi and more advisory languages", "IVR and cell-broadcast delivery"]
for t, c, y, h, items, sz, sa in (
        ("Benefits", D1, 0.95, 1.95, [[(a, {"bold": True, "color": INK}), (b, {})] for a, b in ben], 11, 3),
        ("How a city measures it", D4, 3.02, 1.72, kpi, 11, 3),
        ("Future scope", D5, 4.86, 2.06, fut, 10.5, 2)):
    box(s, 9.1, y, 3.93, h, fill=CARD, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.09)
    label(s, 9.25, y + 0.1, t, color=INK2, hexc=c, w=3.5)
    txt(s, 9.25, y + 0.42, 3.65, h - 0.5, items, size=sz, color=INK2, space_after=sa,
        bullet={"char": "•", "indent": 0.18, "color": c})
s.notes_slide.notes_text_frame.text = (
    "The evidence is Indian and local: the 2010 Ahmedabad heat wave killed 1,344 more people than normal, and after "
    "the city's heat action plan an estimated 1,190 deaths a year were avoided. Plans work — but they are city-wide, "
    "temperature-triggered and paper-driven. Taapmaan makes them ward-level, forecast-led and accountable, for every "
    "department in this circle.")

# ===== 6. RESEARCH AND REFERENCES ==========================================
s = pres.slides.add_slide(BLANK); chrome(s, 6, "RESEARCH AND REFERENCES")
label(s, 0.3, 0.95, "References", color=INK2, hexc=BRAND)
refs = [("Azhar et al. (2014), PLOS ONE 9(3): e91831", "Ahmedabad 2010 excess deaths", "doi.org/10.1371/journal.pone.0091831"),
        ("Hess et al. (2018), J. Environ. Public Health", "Heat Action Plan impact", "doi.org/10.1155/2018/7973519"),
        ("Stull (2011), J. Appl. Meteor. Climatol. 50: 2267–69", "Wet-bulb formula", "doi.org/10.1175/JAMC-D-11-0143.1"),
        ("Bröde et al. (2012), Int. J. Biometeorol. 56: 481–94", "UTCI procedure", "doi.org/10.1007/s00484-011-0454-1"),
        ("ISO 7243:2017", "WBGT heat-stress index", ""),
        ("Rothfusz (1990), NWS Technical Attachment SR 90-23", "Heat Index regression", ""),
        ("NDMA heat-wave action plan guidelines (2016; rev. 2017, 2019)", "HAP department structure", "ndma.gov.in/images/guidelines/guidelines-heat-wave.pdf"),
        ("Open-Meteo forecast & historical (ERA5) APIs", "Live weather, 13-yr training data", "open-meteo.com"),
        ("Census of India 2011 city tables; PIB (PRID 1847436)", "Slum share; 7.7% urban 60+", "census2011.co.in · pib.gov.in")]
rows, cols = len(refs) + 1, 3
tb = s.shapes.add_table(rows, cols, Inches(0.3), Inches(1.28), Inches(7.3), Inches(0.46 * rows)).table
for c, wd in enumerate((3.05, 1.85, 2.4)): tb.columns[c].width = Inches(wd)
tb.first_row = True; tb.horz_banding = False
def cell(r, c, text, bold=False, color=INK2, fill="FFFFFF", size=9.5, link=None):
    ce = tb.cell(r, c); ce.fill.solid(); ce.fill.fore_color.rgb = rgb(fill)
    ce.margin_left = ce.margin_right = Inches(0.07); ce.margin_top = ce.margin_bottom = Inches(0.035)
    ce.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = ce.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]; p.text = ""
    run = p.add_run(); run.text = text; f = run.font; f.size = Pt(size); f.bold = bold; f.name = "Calibri"
    f.color.rgb = rgb(color)
    if link: run.hyperlink.address = link
for c, h in enumerate(("Source", "Used for", "Link")): cell(0, c, h, bold=True, color="FFFFFF", fill=SIH_BLUE, size=10)
for r, (a1, a2, a3) in enumerate(refs, start=1):
    fill = "FFFFFF" if r % 2 else "FAF8F5"
    cell(r, 0, a1, color=INK, fill=fill); cell(r, 1, a2, fill=fill)
    lk = ("https://" + a3.split(" · ")[0]) if a3 else None
    cell(r, 2, a3 or "standard (no public link)", color=(SIH_BLUE if a3 else MUTED), fill=fill, size=9, link=lk)
for r in range(rows): tb.rows[r].height = Inches(0.46)
txt(s, 0.3, 1.28 + 0.46 * rows + 0.1, 7.3, 0.5,
    "Every figure in this deck is computed by the Taapmaan code from these sources. Ward-level demography and "
    "capacity are partly modelled; the app labels each field's source (see /v1/census).",
    size=9.5, italic=True, color=MUTED)
E = FX["era5_wbgt"]
order = sorted(E, key=lambda c: E[c]["p5"])
cd = CategoryChartData(); cd.categories = [c.capitalize() for c in order]
cd.add_series("base", [E[c]["p5"] for c in order])
cd.add_series("5th–50th percentile", [round(E[c]["p50"] - E[c]["p5"], 1) for c in order])
cd.add_series("50th–95th percentile", [round(E[c]["p95"] - E[c]["p50"], 1) for c in order])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(7.85), Inches(0.92), Inches(5.18), Inches(2.55), cd)
ch = gf.chart; ch.has_legend = False
ch.has_title = True; ch.chart_title.text_frame.text = "Peak daily WBGT by city, °C — ERA5 2013–25"
tr = ch.chart_title.text_frame.paragraphs[0].runs[0].font; tr.size = Pt(11.5); tr.bold = True; tr.color.rgb = rgb(INK)
pl = ch.plots[0]; pl.gap_width = 55; pl.overlap = 100
base, lo, hi = pl.series
base.format.fill.background(); base.format.line.fill.background()
lo.format.fill.solid(); lo.format.fill.fore_color.rgb = rgb("F6C790")
hi.format.fill.solid(); hi.format.fill.fore_color.rgb = rgb(D3)
for i, c in enumerate(order):
    for ser, val, pos_, col in ((lo, E[c]["p5"], XL_LABEL_POSITION.INSIDE_BASE, INK), (hi, E[c]["p95"], XL_LABEL_POSITION.INSIDE_END, "FFFFFF")):
        d = ser.points[i].data_label; d.has_text_frame = True; d.text_frame.text = f"{val:.1f}"; d.position = pos_
        f = d.text_frame.paragraphs[0].runs[0].font; f.size = Pt(9); f.bold = True; f.color.rgb = rgb(col)
va = ch.value_axis; va.minimum_scale = 10; va.maximum_scale = 40; va.major_unit = 5
va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = rgb("E6E2DA")
va.tick_labels.font.size = Pt(9); va.tick_labels.font.color.rgb = rgb(MUTED); va.format.line.fill.background()
ca = ch.category_axis; ca.tick_labels.font.size = Pt(10); ca.tick_labels.font.color.rgb = rgb(INK2); ca.format.line.color.rgb = rgb(LINE)
ch_, dl_ = E["chennai"], E["delhi"]
cap = (f"Bars run 5th→95th percentile (median at the colour change). Chennai's 5th percentile ({ch_['p5']:.1f} °C) "
       f"sits above Delhi's median ({dl_['p50']:.1f} °C): one national threshold cannot fit both."
       if ch_["p5"] > dl_["p50"] else
       f"Bars run 5th→95th percentile (median at the colour change). Floors differ by "
       f"{max(e['p5'] for e in E.values()) - min(e['p5'] for e in E.values()):.1f} °C across cities: one national threshold cannot fit all.")
txt(s, 7.85, 3.5, 5.18, 0.45, cap, size=9, italic=True, color=MUTED)
label(s, 7.85, 4.05, "Existing approaches vs Taapmaan", color=INK2, hexc=D4, w=5)
cmp_rows = [("Approach", "Measures", "Scale", "Health link", "Acts"),
            ("IMD heat-wave warnings", "Air temperature vs thresholds", "District", "No", "Manual"),
            ("City Heat Action Plans", "Temperature triggers", "City", "Indirect", "Manual"),
            ("WBGT meters", "WBGT at one site", "Point", "No", "No"),
            ("Taapmaan", "WBGT + UTCI + HI + night + run → HTSI", "Ward", "Deaths & ED load", "Auto + audited")]
ct = s.shapes.add_table(5, 5, Inches(7.85), Inches(4.37), Inches(5.18), Inches(0.33 * 5)).table
for c, wd in enumerate((1.38, 1.62, 0.62, 0.84, 0.72)): ct.columns[c].width = Inches(wd)
ct.first_row = True; ct.horz_banding = False
for r, row in enumerate(cmp_rows):
    for c, v in enumerate(row):
        ce = ct.cell(r, c); last = r == 4; hdr = r == 0
        ce.fill.solid(); ce.fill.fore_color.rgb = rgb(SIH_BLUE if hdr else (BRANDW if last else ("FFFFFF" if r % 2 else "FAF8F5")))
        ce.margin_left = ce.margin_right = Inches(0.05); ce.margin_top = ce.margin_bottom = Inches(0.03)
        ce.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = ce.text_frame.paragraphs[0]; p.text = ""; ce.text_frame.word_wrap = True
        run = p.add_run(); run.text = v; f = run.font; f.name = "Calibri"; f.size = Pt(9)
        f.bold = hdr or last; f.color.rgb = rgb("FFFFFF" if hdr else (DB if last else INK2))
    ct.rows[r].height = Inches(0.33)
box(s, 7.85, 6.2, 5.18, 0.72, fill=BRANDW, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
txt(s, 8.0, 6.26, 4.9, 0.6, [[("See it live: ", {"bold": True, "color": DB}), ("./run.sh → localhost:8000 · API docs at /docs", {})],
                              [("Repo / demo video: ", {"bold": True, "color": DB}), ("‹add link›", {})]],
    size=10.5, color=INK2, space_after=2, anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text = (
    "Every formula comes from a peer-reviewed or standards source, and every number on these slides is computed by "
    "the code from these datasets. The chart is from our 13 years of ERA5 data: local climate defines what "
    "'extreme' means, which is why Taapmaan scores each city against its own climatology. Replace ‹add link› with "
    "your repo or demo video before submitting.")

pres.save(OUT)
print("saved", OUT, f"({os.path.getsize(OUT) / 1e6:.1f} MB)")
print("WARNINGS:" if WARN else "no overflow warnings", *WARN, sep="\n  ")
