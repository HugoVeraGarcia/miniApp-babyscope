#!/usr/bin/env python3
"""SpecVersus static site generator.

Reads data/products.json + data/site.json and writes the whole site to dist/.
Every product page, card, category, guide and comparison row is generated
from the data — adding a model means adding a record and re-running:

    python tools/build.py

No third-party dependencies (Python 3.9+).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "src"
DIST = ROOT / "dist"

VER = dt.datetime.now().strftime("%Y%m%d%H%M")  # cache-buster, bumped every build

SITE = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
DB = json.loads((DATA / "products.json").read_text(encoding="utf-8"))
PRODUCTS = DB["products"]
BY_ID = {p["id"]: p for p in PRODUCTS}
_MU = DATA / "matchups.json"
MATCHUPS = [m for m in (json.loads(_MU.read_text(encoding="utf-8"))["matchups"] if _MU.exists() else [])
            if m["a"] in BY_ID and m["b"] in BY_ID]

E = lambda s: html.escape("" if s is None else str(s), quote=True)  # noqa: E731

# --------------------------------------------------------------------------
# Schema metadata: labels, units and which direction is "better".
# The comparator and the ficha spec table both read from this list.
# --------------------------------------------------------------------------
SCORE_AXES = [
    ("portability", "Weight & fold"),
    ("ride", "Smooth ride"),
    ("comfort", "Baby comfort"),
    ("storage", "Storage"),
    ("safety", "Safety"),
    ("build", "Build"),
    ("value", "Value"),
]

SPEC_GROUPS = [
    ("Weight & fold", [
        ("weight_lb", "Stroller weight", "lb", "min"),
        ("folded_size", "Folded size", None, None),
        ("one_hand_fold", "One-hand fold", "bool", "true"),
        ("self_standing", "Stands when folded", "bool", "true"),
        ("carry_on", "Fits airline overhead bin (brand claim)", "bool", "true"),
    ]),
    ("Seat & baby", [
        ("from_birth", "Use from birth", None, None),
        ("max_child_lb", "Max child weight (per seat)", "lb", "max"),
        ("recline", "Seat recline", None, None),
        ("reversible_seat", "Parent-facing seat", "bool", "true"),
        ("canopy", "Canopy", None, None),
        ("seats", "Seats", None, "max"),
    ]),
    ("Wheels & ride", [
        ("wheels", "Wheels", None, None),
        ("suspension", "Suspension", None, None),
        ("jogging", "Jogging-rated", "bool", "true"),
        ("handbrake", "Hand brake", "bool", "true"),
    ]),
    ("Car seat", [
        ("car_seat", "Infant car seat", None, None),
        ("car_seat_fit", "Car seat compatibility", None, None),
    ]),
    ("Storage & handle", [
        ("basket_lb", "Basket capacity", "lb", "max"),
        ("adjustable_handle", "Adjustable handlebar", "bool", "true"),
        ("cup_holder", "Parent cup holder / tray", "bool", "true"),
    ]),
    ("Safety & support", [
        ("harness", "Harness", None, None),
        ("jpma", "JPMA certified", "bool", "true"),
        ("warranty", "Warranty", None, None),
    ]),
]

TYPES = ("Travel system", "Full-size", "Travel stroller", "Jogging", "Double")

PRICE_BANDS = [(200, "Under $200"), (350, "$200–$350"), (550, "$350–$550"), (10**9, "$550+")]


def band_index(p) -> int | None:
    if p.get("price") is None:
        return None
    return next(i for i, (cap, _) in enumerate(PRICE_BANDS) if p["price"] < cap)


def band(p) -> str:
    i = band_index(p)
    return "" if i is None else PRICE_BANDS[i][1]


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------
def img(image_id: str, size: int = 1500) -> str:
    return f"https://m.media-amazon.com/images/I/{image_id}._AC_SL{size}_.jpg"


def money(v) -> str:
    if v is None:
        return ""
    return f"${v:,.2f}"


def nice_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.strftime("%b %-d, %Y")


def fmt_num(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def fmt_spec(v, unit) -> str:
    if v is None:
        return '<span class="na" title="Not published by the manufacturer">—</span>'
    if unit == "bool":
        return '<span class="yes">Yes</span>' if v else '<span class="no">No</span>'
    if unit:
        return f"{fmt_num(v)}&nbsp;{unit}"
    return E(v)


def display_name(p) -> str:
    return p["name"] + (f" ({p['variant']})" if p.get("variant") else "")


def url_of(p) -> str:
    return f"/strollers/{p['id']}/"


def editor_score(p) -> float:
    # Weighted overall score. Missing axes count as 0 (unverified data is never rewarded).
    g = lambda k: p["scores"].get(k) or 0  # noqa: E731
    w = {"portability": .15, "ride": .15, "comfort": .15, "storage": .10, "safety": .15, "build": .10, "value": .20}
    total = sum(w.values())
    return round(sum(g(k) * v for k, v in w.items()) / total, 1)


def stars(rating, count=None, small=False) -> str:
    if rating is None:
        return '<span class="stars stars--none">No Amazon reviews yet</span>'
    pct = max(0, min(100, rating / 5 * 100))
    cnt = f' <span class="stars__count">({count:,})</span>' if count is not None else ""
    cls = "stars stars--sm" if small else "stars"
    return (f'<span class="{cls}" aria-label="{rating} out of 5 stars on Amazon">'
            f'<span class="stars__bar" style="--pct:{pct:.0f}%"></span>'
            f'<b>{rating:.1f}</b>{cnt}</span>')


def buy_button(p, label="Check price on Amazon", cls="btn btn--amazon") -> str:
    # The affiliate link is used verbatim — never rewritten.
    return (f'<a class="{cls}" href="{E(p["affiliate_url"])}" target="_blank" '
            f'rel="sponsored nofollow noopener" data-asin="{E(p["asin"])}">'
            f'{E(label)}<svg class="ico" aria-hidden="true"><use href="#i-ext"/></svg></a>')


def price_block(p, big=False) -> str:
    # Exact prices are never shown (Amazon only allows them via its API); a broad band helps shoppers filter.
    b = band(p)
    cls = "price price--band price--big" if big else "price price--band"
    inner = f'<span class="price__band" title="Typical price range on Amazon, checked {nice_date(p["price_date"])}. Click through for today\'s exact price.">{E(b)}</span>' if b else ""
    return f'<div class="{cls}">{inner}<span class="price__note">See today\'s price on Amazon</span></div>'


def compare_toggle(p, compact=False) -> str:
    label = "" if compact else '<span class="cmp-toggle__txt">Compare</span>'
    return (f'<button type="button" class="cmp-toggle" data-compare="{E(p["id"])}" aria-pressed="false" '
            f'title="Add to comparison"><svg class="ico" aria-hidden="true"><use href="#i-plus"/></svg>{label}</button>')


# --------------------------------------------------------------------------
# Category / guide rules (derived from data, so pages fill themselves)
# --------------------------------------------------------------------------
def matches(p, rule: str | None) -> bool:
    if not rule:
        return True
    s = p["specs"]
    if rule.startswith("tag:"):
        return rule[4:] in p.get("tags", [])
    if rule.startswith("spec:"):
        return bool(s.get(rule[5:]))
    for op in ("<=", ">="):
        if op in rule:
            key, val = rule.split(op)
            v = p.get("price") if key == "price" else s.get(key)
            if v is None:
                return False
            return v <= float(val) if op == "<=" else v >= float(val)
    raise ValueError(f"Unknown rule {rule}")


def models_label(c) -> str:
    n = sum(matches(p, c["rule"]) for p in PRODUCTS)
    return "Coming soon" if n == 0 else f"{n} model{'s' if n != 1 else ''}"


def sc(p, k):
    v = p["scores"].get(k)
    return 0 if v is None else v


def guide_score(p, kind: str) -> float:
    W = {
        "value":    {"value": .40, "safety": .15, "comfort": .15, "build": .15, "ride": .15},
        "travel":   {"portability": .45, "value": .20, "comfort": .15, "build": .10, "safety": .10},
        "system":   {"safety": .25, "comfort": .20, "value": .20, "ride": .15, "build": .10, "storage": .10},
        "jogging":  {"ride": .40, "safety": .20, "build": .15, "comfort": .10, "value": .15},
        "double":   {"storage": .15, "ride": .20, "comfort": .20, "value": .25, "build": .10, "portability": .10},
        "newborn":  {"comfort": .30, "ride": .20, "safety": .20, "value": .20, "build": .10},
    }.get(kind)
    if not W:
        return editor_score(p)
    return round(sum(sc(p, k) * w for k, w in W.items()), 2)


# --------------------------------------------------------------------------
# SVG radar (static, so product pages chart without JavaScript)
# --------------------------------------------------------------------------
SERIES_COLORS = ["#3656F5", "#F2622E", "#0FA37F", "#B8288C"]


def radar_svg(series, size=320, labels=True, cls="radar") -> str:
    """series: list of (scores_dict, color)."""
    n = len(SCORE_AXES)
    cx = cy = size / 2
    r = size * 0.34
    pt = lambda i, val: (cx + r * (val / 10) * math.sin(2 * math.pi * i / n),  # noqa: E731
                         cy - r * (val / 10) * math.cos(2 * math.pi * i / n))
    parts = [f'<svg class="{cls}" viewBox="0 0 {size} {size}" role="img" aria-label="Editor scores radar chart">']
    for ring in (2, 4, 6, 8, 10):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ring) for i in range(n)))
        parts.append(f'<polygon class="radar__ring" points="{pts}"/>')
    for i in range(n):
        x, y = pt(i, 10)
        parts.append(f'<line class="radar__spoke" x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"/>')
    for scores, color in series:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                       (pt(i, scores.get(k) or 0) for i, (k, _) in enumerate(SCORE_AXES)))
        parts.append(f'<polygon class="radar__area" points="{pts}" style="--c:{color}"/>')
        for i, (k, _) in enumerate(SCORE_AXES):
            x, y = pt(i, scores.get(k) or 0)
            hollow = " radar__dot--na" if scores.get(k) is None else ""
            parts.append(f'<circle class="radar__dot{hollow}" cx="{x:.1f}" cy="{y:.1f}" r="3.2" style="--c:{color}"/>')
    if labels:
        for i, (k, lab) in enumerate(SCORE_AXES):
            x, y = pt(i, 12.6)
            anchor = "middle" if abs(x - cx) < 4 else ("start" if x > cx else "end")
            val = ""
            if len(series) == 1:
                v = series[0][0].get(k)
                val = f'<tspan class="radar__val" x="{x:.1f}" dy="1.25em">{"n/a" if v is None else v}</tspan>'
            parts.append(f'<text class="radar__label" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{E(lab)}{val}</text>')
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# Layout partials
# --------------------------------------------------------------------------
ICONS = """<svg width="0" height="0" style="position:absolute" aria-hidden="true">
<symbol id="i-ext" viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></symbol>
<symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></symbol>
<symbol id="i-city" viewBox="0 0 24 24"><path d="M3 21h18M5 21V8l6-3v16M11 21V3l8 4v14M8 10h0M8 14h0M15 10h0M15 14h0M15 18h0" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-fold" viewBox="0 0 24 24"><path d="M6 20h9M15 20l3-16M18 4h2M6 20a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM19 20a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-mountain" viewBox="0 0 24 24"><path d="m2 20 7-12 4 6 3-4 6 10H2Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></symbol>
<symbol id="i-user" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></symbol>
<symbol id="i-feather" viewBox="0 0 24 24"><path d="M20 4c-7 0-13 5-13 12v4M7 16h7M20 4c0 7-4 12-9 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-tag" viewBox="0 0 24 24"><path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="8" cy="8" r="1.6" fill="currentColor"/></symbol>
<symbol id="i-kid" viewBox="0 0 24 24"><circle cx="12" cy="6" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 9v6M8 12h8M12 15l-3 6M12 15l3 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></symbol>
<symbol id="i-drop" viewBox="0 0 24 24"><path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></symbol>
<symbol id="i-paw" viewBox="0 0 24 24"><circle cx="7" cy="9" r="2" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="6.5" r="2" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="17" cy="9" r="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 12c-3 0-5 3.5-5 5.5 0 1.7 1.5 2.5 3 2l2-.6 2 .6c1.5.5 3-.3 3-2 0-2-2-5.5-5-5.5Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></symbol>
<symbol id="i-layers" viewBox="0 0 24 24"><path d="M3 16h18M5 12h14M8 8h8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></symbol>
<symbol id="i-dock" viewBox="0 0 24 24"><rect x="7" y="3" width="10" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M4 21h16M10 8h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></symbol>
<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
</svg>"""

NAV = [
    ("/strollers/", "Strollers"),
    ("/category/", "Categories"),
    ("/compare/", "Compare"),
    ("/fit-finder/", "Fit finder"),
    ("/guides/", "Buying guides"),
    ("/vs/", "Head to head"),
]


def header(active: str) -> str:
    links = "".join(
        f'<a href="{h}" class="nav__link{" is-active" if active == h else ""}"'
        f'{" aria-current=page" if active == h else ""}>{t}'
        f'{"<span class=cmp-count data-cmp-count hidden>0</span>" if h == "/compare/" else ""}</a>'
        for h, t in NAV)
    return f"""<aside class="topbar" aria-label="Affiliate disclosure">Reader-supported: we may earn a commission when you buy through our links. <a href="/affiliate-disclosure/">Learn more</a></aside>
<header class="site-header">
  <div class="wrap site-header__in">
    <a class="logo" href="/" aria-label="{E(SITE['name'])} home"><span class="logo__mark" aria-hidden="true"><svg viewBox="0 0 32 32"><circle cx="11" cy="26" r="3"/><circle cx="23" cy="26" r="3"/><path d="M3 6h3l2.5 6M8.5 12H27a9 9 0 0 1-9 9h-1a9 9 0 0 1-8.5-9ZM17 12V4a9 9 0 0 1 9 8"/></svg></span><span class="logo__txt">{SITE['logo'][0]}<b>{SITE['logo'][1]}</b></span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu"><svg class="ico"><use href="#i-menu"/></svg></button>
    <nav id="site-nav" class="nav" aria-label="Main">{links}</nav>
  </div>
</header>"""


def footer() -> str:
    cats = "".join(f'<li><a href="/category/{c["slug"]}/">{E(c["name"])}</a></li>' for c in SITE["categories"])
    guides = "".join(f'<li><a href="/guides/{g["slug"]}/">{E(g["title"])}</a></li>' for g in SITE["guides"])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="site-footer__grid">
      <div>
        <a class="logo logo--light" href="/"><span class="logo__mark" aria-hidden="true"><svg viewBox="0 0 32 32"><circle cx="11" cy="26" r="3"/><circle cx="23" cy="26" r="3"/><path d="M3 6h3l2.5 6M8.5 12H27a9 9 0 0 1-9 9h-1a9 9 0 0 1-8.5-9ZM17 12V4a9 9 0 0 1 9 8"/></svg></span><span class="logo__txt">{SITE['logo'][0]}<b>{SITE['logo'][1]}</b></span></a>
        <p class="muted">{E(SITE["footer_blurb"])}</p>
      </div>
      <div><h2>Categories</h2><ul>{cats}</ul></div>
      <div><h2>Guides</h2><ul>{guides}</ul></div>
      <div><h2>Site</h2><ul><li><a href="/compare/">Compare strollers</a></li><li><a href="/vs/">Head-to-head comparisons</a></li><li><a href="/fit-finder/">Fit finder</a></li><li><a href="/how-we-rate/">How we rate</a></li><li><a href="/about/">About &amp; contact</a></li><li><a href="/affiliate-disclosure/">Affiliate disclosure</a></li><li><a href="/privacy/">Privacy &amp; cookies</a></li></ul></div>
    </div>
    <div class="site-footer__legal">
      <p><strong>Affiliate disclosure:</strong> {E(SITE['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. As an Amazon Associate we earn from qualifying purchases, at no extra cost to you.</p>
      <p>Amazon and the Amazon logo are trademarks of Amazon.com, Inc. or its affiliates. Price ranges are approximate; the price displayed on Amazon at the time of purchase applies. Product images are served by Amazon.</p>
      <p>© {SITE['year']} {E(SITE['name'])}</p>
    </div>
  </div>
</footer>
<div class="cmp-tray" data-cmp-tray hidden>
  <div class="wrap cmp-tray__in">
    <div class="cmp-tray__items" data-cmp-items></div>
    <div class="cmp-tray__actions"><button type="button" class="btn btn--ghost btn--sm" data-cmp-clear>Clear</button><a class="btn btn--volt btn--sm" href="/compare/" data-cmp-go>Compare now<svg class="ico"><use href="#i-arrow"/></svg></a></div>
  </div>
</div>"""


def page(path: str, title: str, description: str, body: str, active: str = "",
         jsonld: list | None = None, og_image: str | None = None, body_class: str = "", extra_head: str = "") -> None:
    canonical = SITE["base_url"].rstrip("/") + path
    full_title = title if SITE["name"] in title else f"{title} | {SITE['name']}"
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (jsonld or []))
    og = f'<meta property="og:image" content="{E(og_image)}">' if og_image else ""
    doc = f"""<!doctype html>
<html lang="{SITE['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full_title)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{E(full_title)}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{E(canonical)}">
{og}
<meta name="theme-color" content="#0B0D12">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://m.media-amazon.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css?v={VER}">
<script defer src="/assets/js/db.js?v={VER}"></script>
<script defer src="/assets/js/app.js?v={VER}"></script>
{extra_head}
{ld}
</head>
<body class="{body_class}">
{ICONS}
<a class="skip" href="#main">Skip to content</a>
{header(active)}
<main id="main">
{body}
</main>
{footer()}
</body>
</html>
"""
    out = DIST / path.lstrip("/")
    if path.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    SITEMAP.append(path)


SITEMAP: list[str] = []


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
def from_birth_short(s) -> str:
    return s.get("from_birth") or "—"


def key_specs(p) -> str:
    s = p["specs"]
    items = [
        ("Weight", fmt_spec(s.get("weight_lb"), "lb")),
        ("Child up to", fmt_spec(s.get("max_child_lb"), "lb")),
        ("Basket", fmt_spec(s.get("basket_lb"), "lb")),
        ("Wheels", fmt_spec(s.get("wheels"), None)),
    ]
    return '<dl class="kspecs">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in items) + "</dl>"


def card(p, rank: int | None = None) -> str:
    s = p["specs"]
    badge = f'<span class="card__badge">{E(p["badge"])}</span>' if p.get("badge") else ""
    rk = f'<span class="card__rank">#{rank}</span>' if rank else ""
    data = (f'data-price="{(band_index(p) or 0) + 1}" data-speed="{s.get("basket_lb") or 0}" '
            f'data-range="{s.get("max_child_lb") or 0}" data-weight="{s.get("weight_lb") or 999}" '
            f'data-rating="{p.get("rating") or 0}" data-score="{editor_score(p)}" data-name="{E(display_name(p)).lower()}"')
    return f"""<article class="card" {data}>
  <a class="card__media" href="{url_of(p)}" tabindex="-1" aria-hidden="true">{rk}{badge}<img src="{img(p['images'][0], 500)}" alt="" loading="lazy" decoding="async" width="500" height="500"></a>
  <div class="card__body">
    <div class="card__meta"><span class="card__brand">{E(p['brand'])}</span><span class="score-pill" title="Editor score">{editor_score(p)}</span></div>
    <h3 class="card__title"><a href="{url_of(p)}">{E(display_name(p))}</a></h3>
    {stars(p.get('rating'), p.get('reviews_count'), small=True)}
    <p class="card__tag">{E(p['editorial']['tagline'])}</p>
    {key_specs(p)}
    {price_block(p)}
    <div class="card__actions">{buy_button(p, 'View on Amazon', 'btn btn--amazon btn--sm')}<a class="btn btn--ghost btn--sm" href="{url_of(p)}">Full review</a>{compare_toggle(p, compact=True)}</div>
  </div>
</article>"""


def cards_grid(items, ranked=False, attrs="") -> str:
    return f'<div class="grid" {attrs}>' + "".join(card(p, i + 1 if ranked else None) for i, p in enumerate(items)) + "</div>"


def disclosure_box() -> str:
    return ('<div class="disclosure" role="note"><strong>Heads-up:</strong> links to Amazon on this page are affiliate links. '
            'If you buy through them we may earn a commission, at no extra cost to you. It never changes our scores. '
            '<a href="/affiliate-disclosure/">How this works</a></div>')


def breadcrumbs(items) -> tuple[str, dict]:
    html_ = '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + "".join(
        f'<li><a href="{h}">{E(t)}</a></li>' if h else f'<li aria-current="page">{E(t)}</li>' for h, t in items) + "</ol></nav>"
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, **({"item": SITE["base_url"].rstrip("/") + h} if h else {})}
        for i, (h, t) in enumerate(items)]}
    return html_, ld


def sort_bar(total: int) -> str:
    return f"""<div class="toolbar" data-sort-bar>
  <p class="toolbar__count"><b>{total}</b> model{'s' if total != 1 else ''}</p>
  <label class="select"><span>Sort by</span><select data-sort>
    <option value="score">Editor score</option><option value="price-asc">Price range: low to high</option>
    <option value="price-desc">Price range: high to low</option><option value="speed">Biggest basket</option>
    <option value="range">Highest child weight limit</option><option value="weight">Lightest</option><option value="rating">Amazon rating</option>
  </select></label>
</div>"""


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def build_home():
    featured = [p for p in PRODUCTS if p.get("featured")] or PRODUCTS[:3]
    top2 = sorted(PRODUCTS, key=editor_score, reverse=True)[:2]
    cats = "".join(
        f'<a class="cat" href="/category/{c["slug"]}/"><span class="cat__ico"><svg class="ico"><use href="#i-{c["icon"]}"/></svg></span>'
        f'<span class="cat__name">{E(c["name"])}</span><span class="cat__n">{models_label(c)}</span></a>'
        for c in SITE["categories"])
    guides = "".join(
        f'<a class="guide-tile" href="/guides/{g["slug"]}/"><span class="eyebrow">Buying guide</span><h3>{E(g["title"])}</h3><p>{E(g["description"])}</p><span class="link-arrow">Read the guide<svg class="ico"><use href="#i-arrow"/></svg></span></a>'
        for g in SITE["guides"])
    legend = "".join(f'<li><i style="--c:{SERIES_COLORS[i]}"></i>{E(short_name(p))}</li>' for i, p in enumerate(top2))
    lightest = min((p["specs"].get("weight_lb") or 99) for p in PRODUCTS)
    from_birth = sum(1 for p in PRODUCTS if (p["specs"].get("from_birth") or "").startswith("Yes"))
    body = f"""
<section class="hero">
  <div class="wrap hero__in">
    <div class="hero__copy">
      <p class="eyebrow eyebrow--volt">Stroller reviews · {SITE['year']}</p>
      <h1>Stop guessing.<br><span class="hl">Compare strollers</span> spec by spec.</h1>
      <p class="lead">Amazon's best-selling strollers and travel systems in one format: real weight, fold, newborn readiness, child weight limits, basket size, wheels and car seat fit. Check which ones fit your family, then stack any four side by side.</p>
      <div class="hero__cta"><a class="btn btn--volt btn--lg" href="/fit-finder/">Find the one that fits you<svg class="ico"><use href="#i-arrow"/></svg></a><a class="btn btn--line btn--lg" href="/compare/">Open the comparator</a></div>
      <ul class="hero__stats">
        <li><b>{len(PRODUCTS)}</b><span>models compared</span></li>
        <li><b>{sum(len(g[1]) for g in SPEC_GROUPS)}</b><span>specs per model</span></li>
        <li><b>{fmt_num(lightest)} lb</b><span>lightest stroller</span></li>
        <li><b>{from_birth}</b><span>usable from birth</span></li>
      </ul>
    </div>
    <div class="hero__viz" aria-hidden="false">
      <div class="viz-card">
        <p class="viz-card__title">Head to head · editor scores</p>
        {radar_svg([(p['scores'], SERIES_COLORS[i]) for i, p in enumerate(top2)], size=340, cls='radar radar--dark')}
        <ul class="legend legend--dark">{legend}</ul>
        <a class="viz-card__link" href="/compare/#ids={','.join(p['id'] for p in top2)}">Compare these two<svg class="ico"><use href="#i-arrow"/></svg></a>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section__head"><div><p class="eyebrow">Featured</p><h2>Models worth a close look</h2></div><a class="link-arrow" href="/strollers/">All strollers<svg class="ico"><use href="#i-arrow"/></svg></a></div>
    {cards_grid(featured)}
  </div>
</section>

<section class="section section--tint">
  <div class="wrap">
    <div class="section__head"><div><p class="eyebrow">Browse</p><h2>Find the right stroller for how you live</h2></div></div>
    <div class="cats">{cats}</div>
  </div>
</section>

<section class="section">
  <div class="wrap split">
    <div>
      <p class="eyebrow">How we rate</p>
      <h2>Seven scores. Same rules for every model.</h2>
      <p>Every stroller gets a 0–10 score on weight and fold, smooth ride, baby comfort, storage, safety, build, and value. Weight and fold starts from the spec sheet on a fixed scale, so a 7 means the same thing on every page. The rest are editorial calls based on wheels, seat, canopy, certifications, warranty and what parents report after months of daily use.</p>
      <p>Where Amazon's listing is missing a spec, we check the manufacturer or a reputable retailer. If we can't verify it, we show a dash. We never guess.</p>
      <a class="link-arrow" href="/how-we-rate/">Read our full methodology<svg class="ico"><use href="#i-arrow"/></svg></a>
    </div>
    <ol class="steps">
      <li><b>Spec sheet, normalized.</b> Every listing is converted to the same units: pounds, inches, child weight limits, basket capacity.</li>
      <li><b>Owner reviews, read.</b> We summarize what verified buyers say, the good and the bad.</li>
      <li><b>Claims, checked.</b> "Lightweight", "one-hand fold" and "from birth" get a reality check — including which car seats actually click in.</li>
      <li><b>Side by side.</b> The comparator highlights the best value in every row.</li>
    </ol>
  </div>
</section>

<section class="section section--tint">
  <div class="wrap">
    <div class="section__head"><div><p class="eyebrow">Buying guides</p><h2>Shortlists for every kind of family</h2></div><a class="link-arrow" href="/guides/">All guides<svg class="ico"><use href="#i-arrow"/></svg></a></div>
    <div class="guide-tiles">{guides}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">{disclosure_box()}</div>
</section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": SITE["base_url"]}]
    page("/", f"{SITE['name']}: {SITE['tagline']}",
         "Compare strollers and travel systems side by side: real weight, fold, newborn readiness, child limits, basket, wheels, car seat fit, owner review summaries and buying guides for Amazon's best strollers.",
         body, active="/", jsonld=ld, og_image=img(featured[0]["images"][0], 1000), body_class="home")


def build_all_models():
    items = sorted(PRODUCTS, key=editor_score, reverse=True)
    crumbs, ld = breadcrumbs([("/", "Home"), (None, "All strollers")])
    body = f"""<section class="page-head"><div class="wrap">{crumbs}<h1>All strollers</h1>
<p class="lead">Every stroller and travel system we've reviewed, with the specs that matter. Add up to four to the comparator with the + button.</p></div></section>
<section class="section section--flush"><div class="wrap"><h2 class="sr-only">All models</h2>{sort_bar(len(items))}{cards_grid(items, attrs='data-sortable')}{disclosure_box()}</div></section>"""
    page("/strollers/", "All strollers: specs & reviews",
         "Browse every stroller and travel system we cover with weight, fold, newborn readiness, child weight limit, basket, car seat fit, Amazon rating and editor scores.",
         body, active="/strollers/", jsonld=[ld])


def spec_table(p) -> str:
    s = p["specs"]
    out = ['<div class="spec-table">']
    for gname, rows in SPEC_GROUPS:
        out.append(f'<div class="spec-group"><h3>{E(gname)}</h3><table><tbody>')
        for key, label, unit, _ in rows:
            out.append(f'<tr><th scope="row">{E(label)}</th><td>{fmt_spec(s.get(key), unit)}</td></tr>')
        out.append("</tbody></table></div>")
    if p.get("specs_extra"):
        out.append('<div class="spec-group"><h3>Other details</h3><table><tbody>')
        for k, v in p["specs_extra"].items():
            out.append(f'<tr><th scope="row">{E(k)}</th><td>{E(v)}</td></tr>')
        out.append("</tbody></table></div>")
    out.append("</div>")
    if p.get("data_note"):
        out.append(f'<p class="note"><strong>Listing check:</strong> {E(p["data_note"])}</p>')
    out.append(f'<a class="range-link" href="/fit-finder/?ids={p["id"]}"><span class="range-link__ico" aria-hidden="true"></span><span><b>Is it right for you?</b><small>Check {E(display_name(p))} against your baby&#39;s age, trunk, travel plans and budget</small></span><svg class="ico"><use href="#i-arrow"/></svg></a>')
    out.append(f'<p class="note note--muted">Sources: {E(p.get("spec_sources"))} A dash (—) means the value isn\'t published anywhere we could verify.</p>')
    return "".join(out)


def score_bars(p) -> str:
    rows = []
    for k, lab in SCORE_AXES:
        v = p["scores"].get(k)
        w = 0 if v is None else v * 10
        rows.append(f'<li><span>{lab}</span><span class="bar"><i style="width:{w}%"></i></span><b>{"n/a" if v is None else v}</b></li>')
    return '<ul class="score-bars">' + "".join(rows) + "</ul>"


def reviews_block(p) -> str:
    ed = p["editorial"]
    dist = ""
    if p.get("rating_breakdown"):
        dist = '<ul class="dist">' + "".join(
            f'<li><span>{k}★</span><span class="bar"><i style="width:{v}%"></i></span><b>{v}%</b></li>'
            for k, v in sorted(p["rating_breakdown"].items(), reverse=True)) + "</ul>"
    def one(r):
        top = f'<div class="review__top">{stars(r["stars"], small=True)}<span class="review__date">{nice_date(r["date"])}</span></div>'
        if r.get("paraphrase"):
            body = f'<p class="review__para">{E(r["excerpt"])}</p>'
        else:
            body = f'<figcaption class="review__title">{E(r["title"])}</figcaption><blockquote>“{E(r["excerpt"])}”</blockquote>'
        return f'<figure class="review">{top}{body}<p class="review__by">— {E(r["author"])}, Amazon.com</p></figure>'
    revs = ed.get("reviews", [])
    cards = "".join(one(r) for r in revs)
    para = any(r.get("paraphrase") for r in revs)
    foot = ("Owner reviews from Amazon.com, summarized in our words." if para else
            "Excerpts from Amazon.com customer reviews, shortened." if revs else "Rating summary from Amazon.com.")
    if not cards:
        cards = (f'<p class="muted">{E(p["review_note"])}</p>' if p.get("review_note") else
                 '<p class="muted">No customer reviews on this Amazon listing yet. We\'ll add a summary once owners start posting.</p>')
    return f"""<div class="reviews">
  <div class="reviews__summary">
    <div class="reviews__score">{stars(p.get('rating'), p.get('reviews_count'))}</div>
    {dist}
    <p>{E(ed['review_summary'])}</p>
  </div>
  <div class="reviews__list">{cards}</div>
</div>
<p class="note note--muted">{foot} Ratings as of {nice_date(p['price_date'])}.{(' ' + E(p['review_note'])) if p.get('review_note') and revs else ''}</p>"""


def build_product(p):
    ed = p["editorial"]
    s = p["specs"]
    name = display_name(p)
    thumbs = "".join(
        f'<button type="button" class="gallery__thumb{" is-active" if i == 0 else ""}" data-src="{img(im, 1500)}" aria-label="Show image {i + 1}"><img src="{img(im, 160)}" alt="" loading="lazy" width="80" height="80"></button>'
        for i, im in enumerate(p["images"]))
    similar = [q for q in PRODUCTS if q["id"] != p["id"]]
    same_kind = lambda q: q.get("type") == p.get("type")  # noqa: E731
    similar.sort(key=lambda q: (not same_kind(q), abs((q.get("price") or 0) - (p.get("price") or 0))))
    cats = [c for c in SITE["categories"] if matches(p, c["rule"])]
    cat_chips = "".join(f'<a class="chip" href="/category/{c["slug"]}/">{E(c["short"])}</a>' for c in cats)
    pros = "".join(f"<li>{E(x)}</li>" for x in ed["pros"])
    cons = "".join(f"<li>{E(x)}</li>" for x in ed["cons"])
    body_paras = "".join(f"<p>{E(x)}</p>" for x in ed["body"])
    crumb_cat = cats[0] if cats else None
    crumbs, bld = breadcrumbs([("/", "Home"), ("/strollers/", "Strollers")] +
                              ([(f"/category/{crumb_cat['slug']}/", crumb_cat["name"])] if crumb_cat else []) + [(None, name)])
    quick = [
        ("Type", E(p.get("type") or "—")),
        ("Weighs", fmt_spec(s.get("weight_lb"), "lb")),
        ("From birth", E(from_birth_short(s))),
        ("Child up to", fmt_spec(s.get("max_child_lb"), "lb")),
        ("Basket", fmt_spec(s.get("basket_lb"), "lb")),
        ("Wheels", fmt_spec(s.get("wheels"), None)),
    ]
    quick_html = '<dl class="quick">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in quick) + "</dl>"
    sim_html = ""
    if similar:
        sim_html = f'<section class="section section--tint"><div class="wrap"><div class="section__head"><div><p class="eyebrow">Alternatives</p><h2>Similar models</h2></div><a class="link-arrow" href="/compare/#ids={p["id"]},{",".join(q["id"] for q in similar[:3])}">Compare them all<svg class="ico"><use href="#i-arrow"/></svg></a></div>{cards_grid(similar[:3])}</div></section>'

    my_vs = [m for m in MATCHUPS if p["id"] in (m["a"], m["b"])]
    if my_vs:
        vs_links = "".join(f'<a class="vs-chip" href="{vs_url(m)}"><span>{E(display_name(BY_ID[m["a"]]))}</span><b>vs</b><span>{E(display_name(BY_ID[m["b"]]))}</span></a>' for m in my_vs)
        sim_html = f'<section class="section section--flush"><div class="wrap"><p class="eyebrow">Head to head</p><div class="vs-chips">{vs_links}</div></div></section>' + sim_html
    body = f"""
<section class="pdp">
  <div class="wrap">
    {crumbs}
    <div class="pdp__top">
      <div class="gallery" data-gallery>
        <div class="gallery__main"><img src="{img(p['images'][0], 1500)}" alt="{E(name)}" width="800" height="800" fetchpriority="high" data-gallery-main></div>
        <div class="gallery__thumbs">{thumbs}</div>
      </div>
      <div class="pdp__info">
        <div class="pdp__chips">{f'<span class="chip chip--volt">{E(p["badge"])}</span>' if p.get('badge') else ''}{cat_chips}</div>
        <p class="pdp__brand">{E(p['brand'])}</p>
        <h1>{E(name)}</h1>
        <p class="pdp__tag">{E(ed['tagline'])}</p>
        <div class="pdp__rating">{stars(p.get('rating'), p.get('reviews_count'))}<span class="score-pill score-pill--lg" title="Editor score (weighted, see How we rate)">{editor_score(p)}<small>/10</small></span></div>
        {quick_html}
        <div class="buybox">
          {price_block(p, big=True)}
          <p class="buybox__stock">{E(p.get('availability') or '')} · Sold by {E(p.get('seller') or 'Amazon seller')}</p>
          <div class="buybox__actions">{buy_button(p, 'Check price on Amazon', 'btn btn--amazon btn--lg btn--block')}{compare_toggle(p)}</div>
        </div>
      </div>
    </div>
  </div>
</section>

<nav class="subnav" aria-label="On this page"><div class="wrap"><a href="#verdict">Verdict</a><a href="#scores">Scores</a><a href="#specs">Specs</a><a href="#review">Review</a><a href="#owners">Owner reviews</a></div></nav>

<section class="section" id="verdict">
  <div class="wrap verdict">
    <div class="verdict__main">
      <p class="eyebrow">Our verdict</p>
      <h2>{E(ed['verdict'])}</h2>
      <p class="lead">{E(ed['summary'])}</p>
    </div>
    <div class="fit">
      <div class="fit__row fit__row--yes"><h3>Ideal for</h3><p>{E(ed['ideal_for'])}</p></div>
      <div class="fit__row fit__row--no"><h3>Skip it if</h3><p>{E(ed['not_for'])}</p></div>
    </div>
  </div>
</section>

<section class="section section--tint" id="scores">
  <div class="wrap scores">
    <div class="scores__chart">{radar_svg([(p['scores'], SERIES_COLORS[0])], size=360)}</div>
    <div>
      <p class="eyebrow">Editor scores</p>
      <h2>How it rates</h2>
      {score_bars(p)}
      <p class="note note--muted">Scores are our editorial ratings (0–10), not manufacturer specs. <a href="/how-we-rate/">How we score</a>.</p>
    </div>
  </div>
</section>

<section class="section" id="specs">
  <div class="wrap">
    <div class="section__head"><div><p class="eyebrow">Specifications</p><h2>Full spec sheet</h2></div>{compare_toggle(p)}</div>
    {spec_table(p)}
  </div>
</section>

<section class="section section--tint" id="review">
  <div class="wrap review-body">
    <article class="prose">
      <p class="eyebrow">In-depth review</p>
      <h2>What it's like to own</h2>
      {body_paras}
    </article>
    <div class="proscons">
      <div class="pc pc--pro"><h3>Pros</h3><ul>{pros}</ul></div>
      <div class="pc pc--con"><h3>Cons</h3><ul>{cons}</ul></div>
      {buy_button(p, 'See it on Amazon', 'btn btn--amazon btn--block')}
    </div>
  </div>
</section>

<section class="section" id="owners">
  <div class="wrap">
    <div class="section__head"><div><p class="eyebrow">Owner reviews</p><h2>What buyers say</h2></div></div>
    {reviews_block(p)}
    <div class="cta-band"><div><h3>Ready to decide?</h3><p>Check today's price and delivery date on Amazon, or stack it against the alternatives.</p></div><div class="cta-band__btns">{buy_button(p, 'Check price on Amazon')}<a class="btn btn--line" href="/compare/#ids={p['id']}{(',' + similar[0]['id']) if similar else ''}">Compare</a></div></div>
    {disclosure_box()}
  </div>
</section>
{sim_html}
<div class="sticky-buy" data-sticky-buy><div class="sticky-buy__name">{E(name)}</div>{buy_button(p, 'View on Amazon', 'btn btn--amazon btn--sm')}</div>
"""
    prod_ld = {
        "@context": "https://schema.org", "@type": "Product", "name": name, "brand": {"@type": "Brand", "name": p["brand"]},
        "image": [img(i, 1500) for i in p["images"][:4]], "sku": p["asin"], "description": ed["summary"],
    }
    if p.get("rating") and p.get("reviews_count"):
        prod_ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": p["rating"], "reviewCount": p["reviews_count"]}
    prod_ld["review"] = {"@type": "Review", "author": {"@type": "Organization", "name": SITE["name"]},
                         "reviewRating": {"@type": "Rating", "ratingValue": editor_score(p), "bestRating": 10, "worstRating": 0},
                         "reviewBody": ed["verdict"]}
    page(url_of(p), f"{name} review: specs, pros & cons",
         f"{name} review: {fmt_num(s.get('weight_lb')) + ' lb, ' if s.get('weight_lb') else ''}{'child up to ' + fmt_num(s.get('max_child_lb')) + ' lb, ' if s.get('max_child_lb') else ''}full specs, car seat fit, editor scores, pros and cons, and what Amazon buyers say.",
         body, active="/strollers/", jsonld=[prod_ld, bld], og_image=img(p["images"][0], 1000), body_class="is-pdp")


def build_categories():
    tiles = "".join(
        f'<a class="cat cat--lg" href="/category/{c["slug"]}/"><span class="cat__ico"><svg class="ico"><use href="#i-{c["icon"]}"/></svg></span><span class="cat__name">{E(c["name"])}</span><span class="cat__desc">{E(c["intro"][:120].rsplit(" ", 1)[0])}…</span><span class="cat__n">{models_label(c)}</span></a>'
        for c in SITE["categories"])
    crumbs, ld = breadcrumbs([("/", "Home"), (None, "Categories")])
    page("/category/", "Stroller categories",
         "Browse strollers by type: travel systems, lightweight travel strollers, jogging, double, single-to-double, from-birth, all-terrain and budget models.",
         f'<section class="page-head"><div class="wrap">{crumbs}<h1>Browse by category</h1><p class="lead">Pick what matters for your family. Every category page updates automatically as we add models.</p></div></section><section class="section section--flush"><div class="wrap"><div class="cats cats--lg">{tiles}</div></div></section>',
         active="/category/", jsonld=[ld])

    for c in SITE["categories"]:
        items = sorted([p for p in PRODUCTS if matches(p, c["rule"])], key=editor_score, reverse=True)
        crumbs, ld = breadcrumbs([("/", "Home"), ("/category/", "Categories"), (None, c["name"])])
        guide = next((g for g in SITE["guides"] if g["slug"] == c.get("guide")), None)
        guide_html = (f'<a class="guide-inline" href="/guides/{guide["slug"]}/"><span class="eyebrow">Buying guide</span><b>{E(guide["title"])}</b><svg class="ico"><use href="#i-arrow"/></svg></a>' if guide else "")
        if items:
            grid = sort_bar(len(items)) + cards_grid(items, attrs="data-sortable")
        else:
            grid = ('<div class="empty"><svg class="ico"><use href="#i-' + c["icon"] + '"/></svg><h2>No models here yet</h2>'
                    '<p>We haven\'t reviewed a model in this category yet. New models are added regularly — in the meantime, browse everything we cover.</p>'
                    '<a class="btn btn--dark" href="/strollers/">See all strollers</a></div>')
        others = "".join(f'<a class="chip" href="/category/{o["slug"]}/">{E(o["short"])}</a>' for o in SITE["categories"] if o["slug"] != c["slug"])
        body = f"""<section class="page-head"><div class="wrap">{crumbs}<p class="eyebrow">Category</p><h1>{E(c['h1'])}</h1><p class="lead">{E(c['intro'])}</p>{guide_html}</div></section>
<section class="section section--flush"><div class="wrap"><h2 class="sr-only">Models in this category</h2>{grid}<div class="chips-row"><span>Other categories:</span>{others}</div>{disclosure_box()}</div></section>"""
        item_ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": SITE["base_url"].rstrip("/") + url_of(p), "name": display_name(p)} for i, p in enumerate(items)]}
        page(f"/category/{c['slug']}/", f"{c['h1']} ({SITE['year']})",
             f"{c['h1']} compared: specs, owner reviews and editor scores. {c['intro'][:100]}",
             body, active="/category/", jsonld=[ld, item_ld])


def build_guides():
    tiles = "".join(
        f'<a class="guide-tile" href="/guides/{g["slug"]}/"><span class="eyebrow">Buying guide · {SITE["year"]}</span><h2>{E(g["title"])}</h2><p>{E(g["description"])}</p><span class="link-arrow">Read the guide<svg class="ico"><use href="#i-arrow"/></svg></span></a>'
        for g in SITE["guides"])
    crumbs, ld = breadcrumbs([("/", "Home"), (None, "Buying guides")])
    page("/guides/", "Stroller buying guides",
         "Buying guides and rankings for strollers: best overall, travel systems, lightweight travel strollers, jogging, double and budget picks.",
         f'<section class="page-head"><div class="wrap">{crumbs}<h1>Buying guides</h1><p class="lead">Shortlists built from our data and updated whenever we add a model.</p></div></section><section class="section section--flush"><div class="wrap"><div class="guide-tiles">{tiles}</div></div></section>',
         active="/guides/", jsonld=[ld])

    for g in SITE["guides"]:
        kind = g["rank_by"]
        pool = [p for p in PRODUCTS if matches(p, g.get("filter"))]
        # Listings with an open safety flag never take a top spot; they stay under "Also considered".
        ranked = sorted(pool, key=lambda p: ("safety-flag" not in p["tags"], guide_score(p, kind)), reverse=True)
        picks, also = ranked[: g["limit"]], ranked[g["limit"]:]
        crumbs, bld = breadcrumbs([("/", "Home"), ("/guides/", "Guides"), (None, g["title"])])
        intro = "".join(f"<p>{E(x)}</p>" for x in g["intro"])
        labels = {0: "Best overall", 1: "Runner-up", 2: "Also great"}
        quick_rows = "".join(
            f'<tr><td><span class="rank">#{i + 1}</span></td><td><a href="#pick-{p["id"]}">{E(display_name(p))}</a><small>{labels.get(i, "")}</small></td>'
            f'<td>{fmt_spec(p["specs"].get("weight_lb"), "lb")}</td><td>{fmt_spec(p["specs"].get("max_child_lb"), "lb")}</td>'
            f'<td><span class="score-pill">{editor_score(p)}</span></td><td>{buy_button(p, "Amazon", "btn btn--amazon btn--xs")}</td></tr>'
            for i, p in enumerate(picks))
        picks_html = ""
        for i, p in enumerate(picks):
            ed = p["editorial"]
            real = ""
            picks_html += f"""<article class="pick" id="pick-{p['id']}">
  <div class="pick__media"><span class="pick__rank">#{i + 1}</span><img src="{img(p['images'][0], 800)}" alt="{E(display_name(p))}" loading="lazy" width="600" height="600"></div>
  <div class="pick__body">
    <p class="eyebrow">{E(labels.get(i, f'Pick #{i + 1}'))}</p>
    <h2><a href="{url_of(p)}">{E(display_name(p))}</a></h2>
    <div class="pick__rating">{stars(p.get('rating'), p.get('reviews_count'), small=True)}<span class="score-pill">{editor_score(p)}</span></div>
    <p class="pick__why"><strong>Why it's here:</strong> {E(ed['verdict'])}</p>
    {key_specs(p)}
    <div class="pick__pc"><ul class="mini mini--pro">{''.join(f'<li>{E(x)}</li>' for x in ed['pros'][:3])}</ul><ul class="mini mini--con">{''.join(f'<li>{E(x)}</li>' for x in ed['cons'][:2])}</ul></div>
    {real}
    {price_block(p)}
    <div class="card__actions">{buy_button(p, 'Check price on Amazon', 'btn btn--amazon')}<a class="btn btn--ghost" href="{url_of(p)}">Full review</a>{compare_toggle(p, compact=True)}</div>
  </div>
</article>"""
        also_html = ""
        if also:
            reason = "Ranked lower on this guide's criteria."
            also_html = f'<section class="also"><h2>Also considered</h2><p class="muted">{E(reason)}</p><ul>' + "".join(
                f'<li><a href="{url_of(p)}">{E(display_name(p))}</a> — {E(p["editorial"]["tagline"])}</li>' for p in also) + "</ul></section>"
        crit = "".join(f"<div class='crit'><h3>{E(a)}</h3><p>{E(b)}</p></div>" for a, b in g["criteria"])
        faq = "".join(f"<details class='faq'><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in g["faq"])
        ids = ",".join(p["id"] for p in picks[:4])
        growing = ('<p class="note">Our catalog is growing: this ranking is generated from our data and updates automatically when we review new models.</p>'
                   if len(picks) < 3 else "")
        body = f"""<section class="page-head page-head--guide"><div class="wrap narrow">{crumbs}<p class="eyebrow">Buying guide · Updated {nice_date(DB['_meta']['updated'])}</p><h1>{E(g['h1'])}</h1><div class="prose">{intro}</div>{growing}</div></section>
<section class="section section--flush"><div class="wrap narrow">
  {disclosure_box()}
  <div class="quicktable"><h2>Quick picks</h2><div class="table-scroll"><table><thead><tr><th><span class="sr-only">Rank</span></th><th>Stroller</th><th>Weight</th><th>Child up to</th><th>Score</th><th><span class="sr-only">Amazon link</span></th></tr></thead><tbody>{quick_rows}</tbody></table></div>
  {f'<a class="link-arrow" href="/compare/#ids={ids}">Compare the picks side by side<svg class="ico"><use href="#i-arrow"/></svg></a>' if len(picks) > 1 else ''}</div>
  <div class="picks">{picks_html}</div>
  {also_html}
  <section class="criteria"><h2>How to choose</h2><div class="crit-grid">{crit}</div></section>
  <section class="faqs"><h2>Frequently asked questions</h2>{faq}</section>
</div></section>"""
        item_ld = {"@context": "https://schema.org", "@type": "ItemList", "name": g["title"], "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": SITE["base_url"].rstrip("/") + url_of(p), "name": display_name(p)} for i, p in enumerate(picks)]}
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faq"]]}
        art_ld = {"@context": "https://schema.org", "@type": "Article", "headline": g["h1"], "dateModified": DB["_meta"]["updated"],
                  "author": {"@type": "Organization", "name": SITE["name"]}}
        page(f"/guides/{g['slug']}/", g["title"], g["description"], body, active="/guides/",
             jsonld=[art_ld, item_ld, faq_ld, bld], og_image=img(picks[0]["images"][0], 1000) if picks else None)


def build_compare():
    # No-JS fallback: a full static comparison of the whole catalog (up to 6).
    items = sorted(PRODUCTS, key=editor_score, reverse=True)[:6]
    head = "".join(f'<th scope="col"><a href="{url_of(p)}">{E(display_name(p))}</a></th>' for p in items)
    rows = ""
    for gname, specs in SPEC_GROUPS:
        rows += f'<tr class="grp"><th colspan="{len(items) + 1}">{E(gname)}</th></tr>'
        for key, label, unit, _ in specs:
            rows += f'<tr><th scope="row">{E(label)}</th>' + "".join(f"<td>{fmt_spec(p['specs'].get(key), unit)}</td>" for p in items) + "</tr>"
    crumbs, ld = breadcrumbs([("/", "Home"), (None, "Compare")])
    body = f"""<section class="page-head page-head--dark"><div class="wrap">{crumbs}<p class="eyebrow eyebrow--volt">Comparator</p><h1>Compare strollers side by side</h1><p class="lead">Pick up to four strollers. Every row highlights the best value, and the radar chart stacks their editor scores on top of each other.</p></div></section>
<section class="section section--flush cmp" data-comparator>
  <div class="wrap">
    <div class="cmp-picker" data-cmp-picker hidden>
      <div class="cmp-picker__head"><h2>Choose models <span class="muted" data-cmp-picked>(0/4)</span></h2><label class="search"><span class="sr">Search models</span><input type="search" placeholder="Search by name or brand…" data-cmp-search></label></div>
      <div class="cmp-picker__list" data-cmp-options></div>
    </div>
    <div data-cmp-result></div>
    {('<div class="vs-strip"><h2>Popular head-to-heads</h2><div class="vs-chips">' + "".join(f'<a class="vs-chip" href="{vs_url(m)}"><span>{E(short_name(BY_ID[m["a"]]))}</span><b>vs</b><span>{E(short_name(BY_ID[m["b"]]))}</span></a>' for m in MATCHUPS) + '</div></div>') if MATCHUPS else ''}
    <noscript><div class="table-scroll"><table class="cmp-static"><thead><tr><th><span class="sr-only">Spec</span></th>{head}</tr></thead><tbody>{rows}</tbody></table></div></noscript>
    {disclosure_box()}
  </div>
</section>"""
    page("/compare/", "Compare strollers side by side",
         "Compare up to four strollers: weight, fold, from-birth use, child weight limit, recline, wheels, basket, car seat fit and editor scores in one table with an overlaid radar chart.",
         body, active="/compare/", jsonld=[ld], body_class="is-compare")


def vs_url(m) -> str:
    return f"/vs/{m['a']}-vs-{m['b']}/"


def short_name(p) -> str:
    return p.get("short") or display_name(p)


def vs_differences(a, b) -> list[str]:
    """Auto-generated, data-only difference bullets (only when both values exist and differ)."""
    na, nb = short_name(a), short_name(b)
    sa, sb = a["specs"], b["specs"]
    out = []

    def cmp(val_a, val_b, higher_better, fmt, word_hi, word_lo):
        if val_a is None or val_b is None or val_a == val_b:
            return
        a_wins = (val_a > val_b) == higher_better
        w, l = (na, nb) if a_wins else (nb, na)
        wv, lv = (val_a, val_b) if a_wins else (val_b, val_a)
        out.append(f"<li><b>{E(w)}</b> {word_hi if higher_better else word_lo}: {fmt(wv)} vs {fmt(lv)}</li>")

    n = lambda u: (lambda v: f"{fmt_num(v)} {u}")  # noqa: E731
    if band_index(a) is not None and band_index(b) is not None and band_index(a) != band_index(b):
        lo, hi = (a, b) if band_index(a) < band_index(b) else (b, a)
        out.append(f"<li><b>{E(short_name(lo))}</b> sits in a lower price range: {E(band(lo))} vs {E(band(hi))}</li>")
    cmp(sa.get("weight_lb"), sb.get("weight_lb"), False, n("lb"), "", "is lighter to lift")
    cmp(sa.get("max_child_lb"), sb.get("max_child_lb"), True, n("lb"), "takes a heavier child (per seat)", "")
    cmp(sa.get("basket_lb"), sb.get("basket_lb"), True, n("lb"), "has the bigger basket", "")
    for key, txt in (("one_hand_fold", "folds with one hand"), ("reversible_seat", "has a parent-facing seat"), ("jogging", "is rated for jogging")):
        if sa.get(key) is not None and sb.get(key) is not None and bool(sa.get(key)) != bool(sb.get(key)):
            w = a if sa.get(key) else b
            out.append(f"<li><b>{E(short_name(w))}</b> {txt}; the other doesn't</li>")
    if a.get("rating") and b.get("rating") and a["rating"] != b["rating"]:
        w, l = (a, b) if a["rating"] > b["rating"] else (b, a)
        out.append(f"<li><b>{E(short_name(w))}</b> is rated higher on Amazon: {w['rating']:.1f}★ ({w['reviews_count']:,} ratings) vs "
                   f"{l['rating']:.1f}★ ({l['reviews_count']:,})</li>")
    return out


def vs_table(a, b) -> str:
    rows = ""
    wins = [0, 0]
    for gname, specs in SPEC_GROUPS:
        rows += f'<tr class="grp"><th colspan="3">{E(gname)}</th></tr>'
        for key, label, unit, better in specs:
            va, vb = a["specs"].get(key), b["specs"].get(key)
            if va in (None, "") and vb in (None, ""):
                continue
            best = set()
            if better and va not in (None, "") and vb not in (None, "") and va != vb:
                if better == "true":
                    best = {0} if va is True else {1} if vb is True else set()
                elif better == "max":
                    best = {0} if va > vb else {1}
                elif better == "min":
                    best = {0} if va < vb else {1}
            for i in best:
                wins[i] += 1
            rows += (f'<tr><th scope="row">{E(label)}</th>' +
                     "".join(f'<td class="{"is-best" if i in best else ""}">{fmt_spec(v, unit)}</td>' for i, v in enumerate((va, vb))) + "</tr>")
    rows += '<tr class="grp"><th colspan="3">Editor scores (0–10)</th></tr>'
    for k, lab in SCORE_AXES:
        va, vb = a["scores"].get(k), b["scores"].get(k)
        best = set() if va is None or vb is None or va == vb else ({0} if va > vb else {1})
        rows += (f'<tr><th scope="row">{E(lab)}</th>' + "".join(
            f'<td class="{"is-best" if i in best else ""}">{"n/a" if v is None else v}</td>' for i, v in enumerate((va, vb))) + "</tr>")
    ea, eb = editor_score(a), editor_score(b)
    rows += (f'<tr><th scope="row"><b>Overall editor score</b></th><td class="{"is-best" if ea > eb else ""}">{ea}</td>'
             f'<td class="{"is-best" if eb > ea else ""}">{eb}</td></tr>')
    head = "".join(f'<th scope="col"><a href="{url_of(p)}">{E(short_name(p))}</a></th>' for p in (a, b))
    return (f'<div class="table-scroll"><table class="cmp-table vs-table"><colgroup><col class="c-label"><col><col></colgroup>'
            f'<thead><tr><th scope="col"><span class="sr">Spec</span></th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'), wins


def build_vs():
    if not MATCHUPS:
        return
    def tile(m):
        a, b = BY_ID[m["a"]], BY_ID[m["b"]]
        return (f'<a class="vs-tile" href="{vs_url(m)}"><div class="vs-tile__imgs"><img src="{img(a["images"][0], 300)}" alt="" loading="lazy">'
                f'<span class="vs-badge">VS</span><img src="{img(b["images"][0], 300)}" alt="" loading="lazy"></div>'
                f'<h3>{E(short_name(a))} <span>vs</span> {E(short_name(b))}</h3><span class="link-arrow">See the comparison<svg class="ico"><use href="#i-arrow"/></svg></span></a>')
    crumbs, ld = breadcrumbs([("/", "Home"), ("/compare/", "Compare"), (None, "Head to head")])
    page("/vs/", "Stroller head-to-head comparisons",
         "Side-by-side comparisons of popular strollers: specs, editor scores and which one to buy.",
         f'<section class="page-head page-head--dark"><div class="wrap">{crumbs}<p class="eyebrow eyebrow--volt">Head to head</p><h1>Stroller vs stroller</h1><p class="lead">The matchups shoppers ask about most, compared spec by spec with a clear recommendation. Want a different pair? Build it in the <a href="/compare/" style="color:#fff">comparator</a>.</p></div></section>'
         f'<section class="section section--flush"><div class="wrap"><h2 class="sr-only">All head-to-head comparisons</h2><div class="vs-tiles">{"".join(tile(m) for m in MATCHUPS)}</div></div></section>',
         active="/compare/", jsonld=[ld])

    for m in MATCHUPS:
        a, b = BY_ID[m["a"]], BY_ID[m["b"]]
        na, nb = short_name(a), short_name(b)
        title = f"{na} vs {nb}: Which to Buy? ({SITE['year']})"
        desc = f"{na} vs {nb} compared: weight, fold, from-birth use, child limits, basket, wheels, car seat fit and owner reviews, plus which one we'd buy and why."
        crumbs, bld = breadcrumbs([("/", "Home"), ("/vs/", "Head to head"), (None, f"{na} vs {nb}")])
        table, wins = vs_table(a, b)
        diffs = vs_differences(a, b)

        def side(p, i):
            return f"""<div class="vs-side" style="--c:{SERIES_COLORS[i]}">
  <a class="vs-side__img" href="{url_of(p)}"><img src="{img(p['images'][0], 600)}" alt="{E(display_name(p))}" width="400" height="400" {'fetchpriority="high"' if i == 0 else 'loading="lazy"'}></a>
  <p class="vs-side__brand">{E(p['brand'])}</p>
  <h2><a href="{url_of(p)}">{E(display_name(p))}</a></h2>
  <div class="vs-side__rating">{stars(p.get('rating'), p.get('reviews_count'), small=True)}<span class="score-pill" title="Editor score">{editor_score(p)}</span></div>
  {key_specs(p)}
  {price_block(p)}
  <div class="vs-side__actions">{buy_button(p, 'Check price on Amazon', 'btn btn--amazon btn--block')}<a class="btn btn--ghost btn--block" href="{url_of(p)}">Full review</a></div>
</div>"""

        def pc(p):
            ed = p["editorial"]
            return (f'<div class="vs-pc"><h3>{E(short_name(p))}</h3><ul class="mini mini--pro">{"".join(f"<li>{E(x)}</li>" for x in ed["pros"][:4])}</ul>'
                    f'<ul class="mini mini--con">{"".join(f"<li>{E(x)}</li>" for x in ed["cons"][:3])}</ul></div>')

        radar = radar_svg([(a["scores"], SERIES_COLORS[0]), (b["scores"], SERIES_COLORS[1])], 360)
        legend = f'<ul class="legend"><li><i style="--c:{SERIES_COLORS[0]}"></i>{E(na)}</li><li><i style="--c:{SERIES_COLORS[1]}"></i>{E(nb)}</li></ul>'
        links = f'<a class="link-arrow" href="/compare/#ids={a["id"]},{b["id"]}">Open in the interactive comparator<svg class="ico"><use href="#i-arrow"/></svg></a>'
        links += f'<a class="link-arrow" href="/fit-finder/?ids={a["id"]},{b["id"]}">Check both in the fit finder<svg class="ico"><use href="#i-arrow"/></svg></a>'
        others = [o for o in MATCHUPS if o is not m][:6]
        others_html = "".join(f'<li><a href="{vs_url(o)}">{E(short_name(BY_ID[o["a"]]))} vs {E(short_name(BY_ID[o["b"]]))}</a></li>' for o in others)
        faq = "".join(f"<details class='faq'><summary>{E(q)}</summary><p>{E(ans)}</p></details>" for q, ans in m.get("faq", []))
        body = f"""<section class="page-head page-head--dark vs-head"><div class="wrap">{crumbs}<p class="eyebrow eyebrow--volt">Head to head · Updated {nice_date(DB['_meta']['updated'])}</p><h1>{E(na)} <span class="vs-head__vs">vs</span> {E(nb)}</h1><p class="lead">{E(m['intro'])}</p></div></section>
<section class="section section--flush"><div class="wrap">
  <div class="vs-sides">{side(a, 0)}<span class="vs-badge vs-badge--lg" aria-hidden="true">VS</span>{side(b, 1)}</div>
  {disclosure_box()}
</div></section>
<section class="section"><div class="wrap narrow">
  <p class="eyebrow">Quick verdict</p>
  <h2>Which one should you buy?</h2>
  <p class="lead vs-bottom">{E(m['bottom_line'])}</p>
  <div class="vs-choose">
    <div class="vs-choose__box" style="--c:{SERIES_COLORS[0]}"><h3>Choose the {E(na)} if…</h3><p>{E(m['choose_a'])}</p>{buy_button(a, 'Check price', 'btn btn--amazon btn--sm')}</div>
    <div class="vs-choose__box" style="--c:{SERIES_COLORS[1]}"><h3>Choose the {E(nb)} if…</h3><p>{E(m['choose_b'])}</p>{buy_button(b, 'Check price', 'btn btn--amazon btn--sm')}</div>
  </div>
</div></section>
<section class="section section--tint"><div class="wrap vs-scores">
  <div class="vs-scores__chart"><p class="eyebrow">Editor scores</p><h2>How they stack up</h2>{radar}{legend}</div>
  <div class="vs-scores__diffs"><p class="eyebrow">Key differences</p><h2>By the numbers</h2><ul class="vs-diffs">{"".join(diffs)}</ul><div class="vs-links">{links}</div></div>
</div></section>
<section class="section"><div class="wrap narrow">
  <p class="eyebrow">Full specs</p><h2>Spec by spec</h2>
  <div class="cmp-table-wrap">{table}</div>
  <p class="note note--muted">“Best” marks the stronger value in each row. A dash means the value isn’t published. {E(na)} wins {wins[0]} spec row{'s' if wins[0] != 1 else ''}, {E(nb)} wins {wins[1]}. Scores follow our <a href="/how-we-rate/">rating rules</a>.</p>
</div></section>
<section class="section section--tint"><div class="wrap narrow">
  <p class="eyebrow">Pros &amp; cons</p><h2>What owners and specs say</h2>
  <div class="vs-pcs">{pc(a)}{pc(b)}</div>
</div></section>
<section class="section"><div class="wrap narrow">
  {f'<section class="faqs"><h2>Frequently asked questions</h2>{faq}</section>' if faq else ''}
  <div class="vs-more"><h2>More head-to-heads</h2><ul>{others_html}</ul><a class="link-arrow" href="/vs/">All comparisons<svg class="ico"><use href="#i-arrow"/></svg></a></div>
</div></section>"""
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in m.get("faq", [])]}
        art_ld = {"@context": "https://schema.org", "@type": "Article", "headline": f"{na} vs {nb}",
                  "dateModified": DB["_meta"]["updated"], "author": {"@type": "Organization", "name": SITE["name"]}}
        page(vs_url(m), title, desc, body, active="/compare/", jsonld=[art_ld, faq_ld, bld], og_image=img(a["images"][0], 1000), body_class="is-vs")


def build_fit_finder():
    cfg = {"liftDefault": 25}
    crumbs, ld = breadcrumbs([("/", "Home"), (None, "Fit finder")])
    q = lambda name, label, opts, checked=0: (f'<fieldset class="ff-q"><legend>{label}</legend><div class="ff-opts">' + "".join(  # noqa: E731
        f'<label class="ff-opt"><input type="radio" name="{name}" value="{v}"{" checked" if i == checked else ""}><span>{t}</span></label>' for i, (v, t) in enumerate(opts)) + "</div></fieldset>")
    form = "".join([
        q("use", "1. Where will you use it most?", [("city", "Sidewalks, stores & errands"), ("travel", "Flights & travel"), ("trails", "Parks, gravel & trails"), ("jog", "Jogging & running")]),
        q("kids", "2. How many kids will ride?", [("one", "One child"), ("two", "Two kids now"), ("grow", "One now, maybe a second later")]),
        q("age", "3. How old is your baby when you start?", [("newborn", "Newborn (0–3 months)"), ("infant", "3–6 months"), ("sitter", "6 months+ (sits up well)")]),
        q("seat", "4. Infant car seat", [("need", "I want one included"), ("have", "I'll use my own car seat — it must click in"), ("no", "Not needed")], 2),
        """<fieldset class="ff-q ff-q--wide"><legend>5. Most you want to lift into the trunk</legend>
<div class="ff-clear"><input type="range" min="10" max="40" step="1" value="25" data-ff-lift aria-label="Maximum stroller weight in pounds"><output data-ff-lift-out>25 lb</output></div>
<p class="ff-hint">Weight without a car seat. For reference, a gallon of water weighs about 8 lb.</p>
<div class="ff-viz" data-ff-viz aria-hidden="true"></div></fieldset>""",
        q("tall", "6. Tallest person who will push it", [("no", "Under 6 ft"), ("yes", "6 ft or taller")]),
        q("budget", "7. Budget", [("0", "Under $200"), ("1", "Up to $350"), ("2", "Up to $550"), ("99", "Any budget")], 3),
    ])
    body = f"""<section class="page-head page-head--dark"><div class="wrap">{crumbs}<p class="eyebrow eyebrow--volt">Fit finder</p><h1>Which stroller fits your family?</h1><p class="lead">Answer seven quick questions. We check every stroller against how you'll use it, how many kids ride, your baby's age, car seat plans, what you can lift and your budget — and tell you exactly why each one fits or doesn't.</p></div></section>
<section class="section section--flush ff" data-ff>
  <div class="wrap ff-grid">
    <form class="ff-form" data-ff-form onsubmit="return false">{form}</form>
    <div class="ff-results"><div class="ff-summary" data-ff-summary aria-live="polite"></div><h2 class="sr-only">Results</h2><div data-ff-list></div>
    <noscript><p class="note">The fit finder needs JavaScript. You can still compare every model in the <a href="/compare/">comparator</a>.</p></noscript></div>
  </div>
  <div class="wrap">
    <div class="rm-notes">
      <div><h2>Newborns need to lie flat</h2><p>Babies who can't hold their head up should ride lying flat or nearly flat: in a bassinet, a seat that reclines fully, or an infant car seat clicked onto the stroller. Many lightweight strollers are only for babies from about 6 months unless you add a car seat.</p></div>
      <div><h2>Car seat compatibility</h2><p>"Travel system" means the stroller comes with an infant car seat that clicks in. If you already own a car seat, check the brand: most strollers accept their own brand directly and others only with a separate adapter.</p></div>
      <div><h2>Jogging is a different job</h2><p>Only run with a stroller its maker rates for jogging — usually three wheels with a front wheel that locks straight, a hand brake and a wrist strap. Most pediatricians and makers say to wait until about 6–8 months before jogging with a baby.</p></div>
    </div>
    {disclosure_box()}
  </div>
</section>"""
    head = f'<script>window.__FF__={json.dumps(cfg, separators=(",", ":"))};</script><script defer src="/assets/js/fit-finder.js?v={VER}"></script>'
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{SITE['name']} Stroller Fit Finder",
              "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
              "url": SITE["base_url"].rstrip("/") + "/fit-finder/"}
    page("/fit-finder/", "Stroller fit finder: which stroller fits your family?",
         "Check which strollers match how you'll use them, how many kids ride, your baby's age, car seat plans, lifting weight and budget — with a reason for every result.",
         body, active="/fit-finder/", jsonld=[ld, app_ld], body_class="is-ff", extra_head=head)


def simple_page(path, title, desc, h1, html_body, crumb):
    crumbs, ld = breadcrumbs([("/", "Home"), (None, crumb)])
    page(path, title, desc, f'<section class="page-head"><div class="wrap narrow">{crumbs}<h1>{E(h1)}</h1></div></section><section class="section section--flush"><div class="wrap narrow prose">{html_body}</div></section>', jsonld=[ld])


def build_static_pages():
    axis_rules = """<table class="rules"><thead><tr><th>Score</th><th>How it's calculated</th></tr></thead><tbody>
<tr><td>Weight &amp; fold</td><td>Formula: stroller weight from 37 lb = 0 to 12 lb = 10 (one point per 2.5 lb), plus 1 point for a true one-hand fold, capped at 10. Shown as n/a when the weight isn't published.</td></tr>
<tr><td>Smooth ride</td><td>Editorial: wheel size and type (foam, rubber, air-filled), suspension, steering and how owners describe curbs, cracks and grass.</td></tr>
<tr><td>Baby comfort</td><td>Editorial: seat recline and padding, canopy coverage, leg rest, ventilation and how long a child can keep using it.</td></tr>
<tr><td>Storage</td><td>Editorial: basket capacity and access, parent tray or cup holder.</td></tr>
<tr><td>Safety</td><td>Editorial: harness, brakes, stability, JPMA certification, car seat fit, and any recall or safety notice we find.</td></tr>
<tr><td>Build</td><td>Editorial: frame and fabric quality, warranty length, seller, and how owners describe durability after months of use.</td></tr>
<tr><td>Value</td><td>Editorial: what you get for the price range relative to similar strollers.</td></tr>
</tbody></table>"""
    simple_page("/how-we-rate/", "How we rate strollers", "Our methodology: where the specs come from, how the seven editor scores are calculated, and how we treat owner reviews.",
                "How we rate strollers", f"""
<p class="lead">Every stroller on {E(SITE['name'])} is described with the same fields and rated with the same rules, so any two pages can be compared honestly.</p>
<h2>Where the specs come from</h2>
<p>We start from the Amazon listing and the manufacturer's own specs, and convert every value into the same units (pounds and inches). Stroller listings often mix up weights (with or without the car seat or bassinet), call a two-hand fold "one-hand", and say "from birth" when that only works with an infant car seat. When the listing contradicts itself we say so on the product page. If a value isn't published, we show a dash (—). We never estimate a spec to fill a chart.</p>
<h2>"From birth" — what we mean</h2>
<p>We mark a stroller as usable from birth only when a newborn can lie flat in it: a bassinet, a seat that reclines flat, or an infant car seat that clicks in. We always say which one it is, and whether that car seat is included or sold separately.</p>
<h2>The seven editor scores</h2>
<p>Scores run from 0 to 10. Weight &amp; fold is calculated from the spec sheet on a fixed scale that's the same across the whole site, so adding new strollers never changes existing scores. The rest are editorial judgments.</p>
{axis_rules}
<p>The <strong>editor score</strong> shown on cards is a weighted average: value 20%; weight &amp; fold, smooth ride, baby comfort and safety 15% each; storage and build 10% each. An axis we can't verify (n/a) counts as 0, so missing data never makes a stroller look better.</p>
<h2>Owner reviews</h2>
<p>We read the Amazon customer reviews for each listing and summarize the recurring themes, good and bad, in our own words. When a listing shares its reviews with other versions or colors, we say so.</p>
<h2>Safety information</h2>
<p>We're not a testing lab and we don't replace your car seat's manual or your pediatrician's advice. For recalls, check the U.S. Consumer Product Safety Commission at <a href="https://www.cpsc.gov/Recalls" rel="nofollow noopener" target="_blank">cpsc.gov/Recalls</a> and register your stroller and car seat with the maker.</p>
<h2>Prices</h2>
<p>We show a broad price range instead of an exact price, because prices on Amazon change daily and the price shown on Amazon at the time of purchase is the one that applies. Click through to see today's price.</p>
<h2>Money</h2>
<p>We earn a commission when you buy through our Amazon links. Commissions never affect scores or rankings. See our <a href="/affiliate-disclosure/">affiliate disclosure</a>.</p>""", "How we rate")

    simple_page("/affiliate-disclosure/", "Affiliate disclosure", f"How {SITE['name']} makes money: Amazon Associates affiliate links and what that means for you.",
                "Affiliate disclosure", f"""
<p class="lead">{E(SITE['name'])} is reader-supported. When you buy through links on our site, we may earn an affiliate commission.</p>
<p>{E(SITE['name'])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. <strong>As an Amazon Associate we earn from qualifying purchases.</strong></p>
<p>What this means for you:</p>
<ul><li>You pay the same price whether or not you use our links.</li><li>Commissions never influence our scores, rankings or verdicts. The rules behind our scores are public on our <a href="/how-we-rate/">methodology page</a>.</li><li>Every link to Amazon on this site is an affiliate link and is marked as sponsored.</li></ul>
<p>Price ranges shown on this site are approximate. Any price and availability information displayed on Amazon.com at the time of purchase will apply to the purchase of the product.</p>
<p>Amazon and the Amazon logo are trademarks of Amazon.com, Inc. or its affiliates. Product images are provided by and served from Amazon.</p>
<p>This disclosure follows the U.S. Federal Trade Commission's guidance on endorsements and testimonials.</p>""", "Affiliate disclosure")

    simple_page("/privacy/", "Privacy & cookies", f"{SITE['name']} privacy and cookie policy.", "Privacy & cookie policy", f"""
<p class="lead">Short version: we don't ask for your personal data, and we don't run ad trackers.</p>
<h2>What we store on your device</h2>
<p>The comparator remembers the models you've selected using your browser's local storage, so your list survives a page reload. That data never leaves your device and you can clear it with the "Clear" button or your browser settings.</p>
<h2>Amazon links</h2>
<p>When you click a link to Amazon, Amazon may set cookies to attribute your purchase to us. Those cookies are governed by <a href="https://www.amazon.com/gp/help/customer/display.html?nodeId=GX7NJQ4ZB8MHFRNJ" rel="nofollow noopener" target="_blank">Amazon's privacy notice</a>.</p>
<h2>Fit finder</h2>
<p>The <a href="/fit-finder/">fit finder</a> runs entirely in your browser. Your answers are never sent anywhere.</p>
<h2>Hosting, fonts and images</h2>
<p>This site is hosted on Netlify, which processes standard server logs (such as IP address and browser type) to deliver and secure the site. Fonts are loaded from Google Fonts and product images from Amazon's image servers; those providers receive your IP address when your browser requests the files.</p>
<h2>Contact</h2>
<p>Questions about privacy: <a href="mailto:{E(SITE['contact_email'])}">{E(SITE['contact_email'])}</a>.</p>
<p class="muted">Last updated {nice_date(DB['_meta']['updated'])}.</p>""", "Privacy")

    simple_page("/about/", "About & contact", f"Who we are and how to reach {SITE['name']}.", f"About {SITE['name']}", f"""
<p class="lead">{E(SITE['name'])} is a small, independent site that turns messy stroller listings into clean, comparable data. It's part of <a href="https://specversus.com">SpecVersus</a>, alongside <a href="https://scooters.specversus.com">ScooterScope</a>, <a href="https://homegym.specversus.com">GymScope</a>, <a href="https://ebikes.specversus.com">BikeScope</a> and <a href="https://powerstations.specversus.com">PowerScope</a>.</p>
<p>Shopping for a stroller on Amazon means decoding "lightweight" claims, travel systems that bundle different car seats, "from birth" fine print and reviews shared across colors and older versions. We normalize every spec, read the owner reviews, flag the claims that don't hold up, and put it all in a format you can compare in seconds.</p>
<h2>Contact</h2>
<p>Spotted a wrong spec, or want us to review a model? Email <a href="mailto:{E(SITE['contact_email'])}">{E(SITE['contact_email'])}</a>.</p>""", "About")

    page("/404.html", "Page not found", "This page doesn't exist.",
         '<section class="page-head"><div class="wrap narrow"><h1>This page took a wrong turn.</h1><p class="lead">The link may be old or mistyped.</p><p><a class="btn btn--dark" href="/">Back to home</a> <a class="btn btn--ghost" href="/strollers/">All strollers</a></p></div></section>')
    SITEMAP.remove("/404.html")


# --------------------------------------------------------------------------
# Data layer for JS + static extras
# --------------------------------------------------------------------------
def build_db_js():
    slim = []
    for p in PRODUCTS:
        slim.append({
            "id": p["id"], "name": short_name(p), "brand": p["brand"], "url": url_of(p),
            "aff": p["affiliate_url"], "img": img(p["images"][0], 300), "band": band(p), "tier": band_index(p),
            "rating": p.get("rating"), "reviews": p.get("reviews_count"),
            "score": editor_score(p), "scores": p["scores"], "specs": p["specs"],
            "tagline": p["editorial"]["tagline"], "verdict": p["editorial"]["verdict"], "tags": p["tags"],
        })
    meta = {
        "axes": [{"k": k, "label": l} for k, l in SCORE_AXES],
        "groups": [{"name": g, "rows": [{"k": k, "label": l, "unit": u, "better": b} for k, l, u, b in rows]} for g, rows in SPEC_GROUPS],
        "colors": SERIES_COLORS, "max": 4,
    }
    js = "/* generated by tools/build.py — do not edit */\nwindow.__DB__=" + json.dumps({"products": slim, "meta": meta}, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (DIST / "assets/js/db.js").write_text(js, encoding="utf-8")


def build_extras():
    base = SITE["base_url"].rstrip("/")
    today = DB["_meta"]["updated"]
    urls = "".join(f"<url><loc>{base}{u}</loc><lastmod>{today}</lastmod></url>" for u in SITEMAP)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC, DIST)
    validate()
    build_home()
    build_all_models()
    for p in PRODUCTS:
        build_product(p)
    build_categories()
    build_guides()
    build_compare()
    build_vs()
    build_fit_finder()
    build_static_pages()
    build_db_js()
    build_extras()
    print(f"Built {len(SITEMAP)} pages for {len(PRODUCTS)} products → {DIST} (v={VER})")


def validate():
    """Guardrails: affiliate links must carry the user's tag setup; ids unique; scores in range."""
    seen = set()
    for p in PRODUCTS:
        assert p["id"] not in seen, f"duplicate id {p['id']}"
        seen.add(p["id"])
        assert p["affiliate_url"] == f"https://www.amazon.com/dp/{p['asin']}?tag={SITE['affiliate_tag']}", f"{p['id']}: affiliate link must be /dp/ASIN?tag={SITE['affiliate_tag']}"
        assert p.get("affiliate_tag") == SITE["affiliate_tag"], f"{p['id']}: wrong affiliate_tag"
        for k, _ in SCORE_AXES:
            v = p["scores"].get(k)
            assert v is None or 0 <= v <= 10, f"{p['id']}: score {k}={v} out of range"
        assert p["images"], f"{p['id']}: no images"
        assert band(p), f"{p['id']}: missing price (needed for the price band)"
    for c in SITE["categories"]:
        assert any(matches(p, c["rule"]) for p in PRODUCTS), f"empty category {c['slug']}"
    for p in PRODUCTS:
        s = p["specs"]
        assert p.get("type") in TYPES, f"{p['id']}: unknown type {p.get('type')}"
        assert s.get("newborn") in ("flat", "carseat", None), f"{p['id']}: bad newborn flag"
        assert bool(s.get("newborn")) == (s.get("from_birth") or "").startswith("Yes"), f"{p['id']}: from_birth/newborn mismatch"
        if s.get("cs_included"):
            assert s.get("newborn") is not None, f"{p['id']}: travel system must be usable from birth"


if __name__ == "__main__":
    main()
