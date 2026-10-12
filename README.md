# BabyScope — stroller comparison site (Amazon.com affiliate)

Part of SpecVersus: https://strollers.specversus.com (sister of scooters., robotvacuums., powerstations., homegym. and ebikes.specversus.com).
Static, data-driven site. Every page is generated from the data files.

```
data/products.json   ← stroller database (generated first by tools/make_products.py; edit directly afterwards)
data/site.json       ← brand, affiliate tag, categories, buying guides
data/matchups.json   ← head-to-head pages (/vs/)
tools/build.py       ← generator: python3 tools/build.py → dist/
src/assets/          ← CSS, JS (comparator, fit finder, compare tray), favicon, _headers
netlify.toml         ← Netlify build settings (Netlify runs the build on every push)
```

## Rules the data follows
- Affiliate links are always `https://www.amazon.com/dp/ASIN?tag=babyscope-20` (the build fails otherwise).
- **No exact prices are ever shown** (Amazon only allows prices obtained through its API). `price` is stored only to place
  each stroller in a price band (Under $200 … $550+). Budget filters and sorting use the band.
- `type` is one of: Travel system, Full-size, Travel stroller, Jogging, Double.
- `specs.newborn`: `flat` (bassinet / carry-cot / lie-flat seat), `carseat` (from birth only with an infant car seat) or null.
  `from_birth` must start with "Yes" exactly when `newborn` is set (the build checks it). Travel systems set `cs_included`.
- Weight is the stroller without a car seat. If the listing contradicts itself, weight stays `null` and the reason goes in `data_note`.
- Scores: weight & fold is formula-based (see /how-we-rate/); the rest are editorial.
- Fit finder: use (city/travel/trails/jog), kids (one/two/grow), baby's age, car seat plans, max lifting weight,
  tall parent (adjustable handlebar), price band.

## Batch 2 (pending)
Graco FastAction LX Jogger (B0861T7Z24), Graco Ready2Grow LX 2.0 (B08K2YFNDW), Baby Jogger City Mini GT2 Double (B07YGVFZFH),
Jeep Destination Ultralight Double (B07B7QC8DV), Baby Trend Expedition Double Jogger (B07BVMSHTZ) — then add a "best double stroller" guide.
