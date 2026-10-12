"""One-off generator for data/products.json (BabyScope batch 1, Oct 12 2026).
Kept in the repo as the record of how scores were set; edit products.json directly afterwards.

Data comes from each Amazon.com listing (title, bullets, spec table, reviews) captured on Oct 12 2026.
Prices are stored only to place each stroller in a broad price band — the site never shows an exact price.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = "2026-10-12"
TAG = "babyscope-20"


def clamp(x):
    return max(0, min(10, round(x)))


def portability(s):
    """Fixed scale: 37 lb = 0 … 12 lb = 10 (one point per 2.5 lb), +1 for a true one-hand fold, capped at 10."""
    w = s.get("weight_lb")
    if not w:
        return None
    return clamp((37 - w) / 2.5 + (1 if s.get("one_hand_fold") else 0))


BASE = dict(weight_lb=None, folded_size=None, one_hand_fold=None, self_standing=None, carry_on=False,
            from_birth=None, newborn=None, max_child_lb=None, recline=None, reversible_seat=None, canopy=None, seats=1,
            wheels=None, suspension=None, jogging=False, handbrake=False,
            car_seat="Not included", cs_included=False, car_seat_fit=None,
            basket_lb=None, adjustable_handle=None, cup_holder=None, harness=None, jpma=None, warranty=None)

FB = {"flat": "Yes — lies flat", "carseat": "Yes — with an infant car seat"}


def R(author, stars, date, text):
    return {"author": author, "stars": stars, "date": date, "title": None, "excerpt": text, "paraphrase": True}


def bd(a, b, c, d, e):
    return {"5": a, "4": b, "3": c, "2": d, "1": e}


P = []


def add(id, asin, name, short, brand, model, type_, images, tags, seller, price, list_price, avail, rating, count, breakdown,
        specs, extra, sources, edit, ed, featured=False, badge=None, data_note=None, review_note=None, from_birth=None):
    sp = dict(BASE)
    sp.update(specs)
    if type_ == "Travel system":
        sp["cs_included"] = True
    if sp["newborn"] == "carseat":
        sp["from_birth"] = from_birth or ("Yes — with the included car seat" if sp["cs_included"] else "Yes — with a compatible infant car seat (sold separately)")
    elif sp["newborn"]:
        sp["from_birth"] = from_birth or FB[sp["newborn"]]
    else:
        sp["from_birth"] = from_birth or "No — about 6 months+"
    tags = list(tags)
    if type_ == "Travel system":
        tags.append("travel-system")
        sp["cs_included"] = True
    if sp["newborn"] == "flat":
        tags.append("from-birth")
    if sp.get("jogging"):
        tags.append("jogging")
    if (sp.get("seats") or 1) >= 2 or "convertible" in tags:
        tags.append("double")
    sc = {"portability": portability(sp)}
    sc.update(edit)
    P.append({"id": id, "asin": asin, "name": name, "short": short, "brand": brand, "model": model, "variant": None, "type": type_,
              "affiliate_url": f"https://www.amazon.com/dp/{asin}?tag={TAG}", "affiliate_tag": TAG,
              "canonical_url": f"https://www.amazon.com/dp/{asin}", "images": images.split(), "tags": sorted(set(tags)),
              "featured": featured, "badge": badge, "seller": seller, "price": price, "list_price": list_price,
              "price_date": D, "availability": avail, "rating": rating, "reviews_count": count,
              "rating_breakdown": breakdown, "specs": sp, "specs_extra": extra, "spec_sources": sources,
              "data_note": data_note, "review_note": review_note, "scores": sc, "editorial": ed})


AMZ = "Amazon.com"
SRC = "Amazon listing (title, bullets and spec table), checked Oct 12 2026."
SRC_M = SRC + " Child weight limit from the manufacturer's spec sheet."

# ================================================================ travel systems
add("doona", "B07HML1BT5", "Doona Car Seat & Stroller (All-in-One Travel System)", "Doona", "Doona", "Doona+", "Travel system",
    "61+3noekzxL 818F5Qb457L 71yJPoxf3nL 71mDALJgX6L 61qxqQbTpEL 71EIrAnU6SL 81NTu0itr7L 811xXgAHb3L",
    [], "Huppins (third-party seller)", 550.00, None, "In stock · 1K+ bought last month", 4.8, 15318, bd(90, 5, 2, 0, 3),
    dict(weight_lb=17.2, folded_size="17.4 × 26 × 22.4 in (as a car seat)", one_hand_fold=False, newborn="carseat", max_child_lb=30,
         recline="Rear-facing car seat with near-flat newborn insert", reversible_seat=True, canopy="UPF 50+, water-repellent",
         wheels="4 small wheels that fold out from the seat", suspension="None", car_seat="Built in — the stroller is the car seat (LATCH base included)",
         car_seat_fit="It is the car seat", adjustable_handle=True, cup_holder=False, harness="5-point", carry_on=False),
    {"Child range": "4–30 lb, up to 32 in", "Base": "LATCH base included (9.7 lb)", "Aircraft": "FAA approved as a car seat"},
    SRC, dict(ride=3, comfort=7, storage=1, safety=9, build=9, value=6),
    {"tagline": "A rear-facing car seat with wheels that fold out — no stroller to carry.",
     "summary": "The original car-seat-stroller: click it out of the base, pop the wheels and go. Brilliant for the first year of errands and flights; outgrown at 30 lb.",
     "body": ["The Doona is an infant car seat with a built-in wheelbase. Unclip it from the LATCH base, pull the handle, and the wheels drop down; your baby never leaves the seat. Nothing else here gets you from car to sidewalk faster, and it's FAA approved, so it doubles as your baby's seat on the plane.",
              "The trade-off is lifespan and storage. It fits babies from 4 to 30 lb and up to 32 in, which most children reach between 12 and 18 months. There's no basket in the standard box, the small wheels don't like gravel or cracked sidewalks, and at 17.2 lb it's heavy to carry as a car seat.",
              "With 15,000+ ratings and 90% five stars, owners overwhelmingly love it for newborn days, travel and small cars. Most families still buy a regular stroller for the toddler years."],
     "pros": ["Car seat to stroller in seconds", "FAA approved for flights", "No stroller to fold or store", "4.8★ from 15K+ ratings"],
     "cons": ["Outgrown at 30 lb / 32 in", "No basket", "Small wheels, rough on bumpy ground", "Heavy to carry as a car seat"],
     "ideal_for": "City parents, frequent flyers and small cars in the first year.",
     "not_for": "A one-and-done stroller to use into the toddler years.",
     "verdict": "Unbeatable convenience for year one — plan on a second stroller after.",
     "review_summary": "4.8★ from 15,318 ratings (95% four or five stars). Parents love the instant car-to-stroller switch, especially for flights and errands; complaints focus on weight and the short lifespan.",
     "reviews": [R("JRM Graphics and Design", 5, "2026-07-24", "The most versatile option for flying: one seat that works in the car, on the plane and as a stroller."),
                 R("Olivia Kent", 5, "2026-09-28", "Their second Doona — nothing beats going from car seat to stroller in the early months, and they love the canopy."),
                 R("Jess", 5, "2022-04-22", "Used daily for nine months and still works great, though converting it takes some practice.")]},
    badge="Best car seat + stroller in one",
    from_birth="Yes — it is the infant car seat",
    data_note="The spec table lists 15.4 lb; Doona's own box contents give 17.2 lb for the seat-stroller, which we use. The table also mentions a rear basket, which isn't in the standard box.")

add("graco-modes-pramette", "B07Y5VQYFW", "Graco Modes Pramette 3-in-1 Travel System", "Graco Modes Pramette", "Graco", "Modes Pramette", "Travel system",
    "81kpc-E8trL 71bcAS5E34L 81A3AVv0imL 91lycCBocaL 71Jy0YZaWtL A1tmSsD0+EL 71+d2K2rYbL 81fGDArc0UL",
    [], AMZ, 359.99, None, "In stock · 3K+ bought last month", 4.6, 7163, bd(83, 9, 4, 1, 3),
    dict(weight_lb=20.9, one_hand_fold=True, newborn="flat", max_child_lb=50, recline="Multi-position; converts to a flat pramette",
         reversible_seat=True, canopy="Extra-large, mesh vent panel", wheels="4, rubber all-terrain (7.5 in rear)", suspension="Front & rear",
         car_seat="Included: Graco SnugRide 35 Lite DLX + base (4–35 lb)", car_seat_fit="Graco SnugRide (Click Connect)",
         cup_holder=True),
    {"Modes": "Car seat carrier, infant pramette, toddler seat"}, SRC_M, dict(ride=6, comfort=8, storage=7, safety=8, build=7, value=9),
    {"tagline": "Car seat, flat pramette and reversible toddler seat in one box.",
     "summary": "Amazon's best-selling travel system for good reason: a SnugRide 35 car seat, a seat that turns into a flat pramette for newborns, and a reversible toddler seat to 50 lb.",
     "body": ["The Modes Pramette covers every stage. In the newborn months you can click in the included SnugRide 35 Lite DLX car seat or convert the stroller seat into a flat, enclosed pramette for walks. Later, the same seat faces you or the world and carries a child up to 50 lb.",
              "It folds with one hand, rides on rubber tires with front and rear suspension, and has an extra-large canopy. At 20.9 lb it's a mid-weight stroller — fine for most trunks, not something you'll want to carry up long stairs.",
              "Sold and shipped by Amazon with 7,000+ ratings. Parents praise how easily the car seat clicks in and how smoothly it pushes; small gripes are the car seat canopy's Velcro and the overall size."],
     "pros": ["Includes SnugRide 35 car seat + base", "Flat pramette mode from birth", "Reversible seat", "Sold by Amazon, 7K+ ratings"],
     "cons": ["Bulky when folded", "Basket capacity not published", "Car seat canopy Velcro is weak"],
     "ideal_for": "First-time parents who want one box that works from birth to preschool.",
     "not_for": "Frequent flyers who need a compact fold.",
     "verdict": "The best all-round travel system for the money.",
     "review_summary": "4.6★ from 7,163 ratings (92% four or five stars). Owners love the versatility and how easily the car seat clicks in; the most common complaint is the car seat canopy's Velcro.",
     "reviews": [R("BritneyMcfield", 5, "2023-03-21", "After a long search, it meets every need and grows with the baby."),
                 R("katie", 5, "2026-09-21", "Only dislikes the car seat sun cover's Velcro; otherwise an amazing combo."),
                 R("Luke", 4, "2025-12-20", "A baby-shower gift that became a favorite — easy to assemble and switch between modes.")]},
    featured=True, badge="Best travel system",
    from_birth="Yes — flat pramette mode")

add("graco-modes-element", "B07Y5VH28M", "Graco Modes Element 3-in-1 Travel System", "Graco Modes Element", "Graco", "Modes Element", "Travel system",
    "81LKxM-5NhL 81eZoQFsVbL 915LUsaJsnL 911OgFZjxWL 81US6eqJ7jL 8140r0QqByL 91HuTumNluL 71-xDbwaraL",
    [], AMZ, 349.99, None, "In stock · 800+ bought last month", 4.7, 1368, bd(87, 8, 2, 1, 2),
    dict(weight_lb=26, one_hand_fold=True, self_standing=True, newborn="carseat", max_child_lb=50, recline="Multi-position",
         reversible_seat=True, canopy="Full coverage, peekaboo window", wheels="4, dual front wheels (7.5 in rear)",
         car_seat="Included: Graco SnugRide Lite LX + base (4–30 lb)", car_seat_fit="Graco SnugRide (Click Connect)", cup_holder=True),
    {"Trays": "Parent tray with cup holders + removable child tray"}, SRC_M, dict(ride=6, comfort=7, storage=7, safety=8, build=7, value=9),
    {"tagline": "A reversible-seat travel system with parent and child trays.",
     "summary": "The Modes Element is the Pramette's sibling without the pramette mode: a SnugRide Lite LX car seat, reversible seat, self-standing one-hand fold and trays for parent and child.",
     "body": ["You get the same Graco Modes frame and reversible seat, plus a parent tray with cup holders and a removable child tray. For newborns you click in the included SnugRide Lite LX car seat (4–30 lb); the stroller seat itself is for older babies.",
              "The fold is one-handed and stands on its own. The listing gives a stroller weight of 22.7 lb and an item weight of 26 lb; either way, it's a mid-size stroller.",
              "It has a 4.7★ rating with 95% four or five stars. Owners describe it as sturdy, quiet and easy to fold; one long-term owner wished the car seat headrest gave more support."],
     "pros": ["Includes SnugRide Lite LX + base", "Self-standing one-hand fold", "Parent and child trays", "95% four or five stars"],
     "cons": ["No flat newborn mode without the car seat", "Car seat outgrown at 30 lb", "Mid-weight"],
     "ideal_for": "Parents who want a dependable travel system with trays at a mid-range price.",
     "not_for": "Walks with a newborn without the car seat.",
     "verdict": "A highly rated, no-fuss travel system.",
     "review_summary": "4.7★ from 1,368 ratings (95% four or five stars). Parents praise easy assembly, a smooth quiet ride and the fold; a few want more head support in the car seat.",
     "reviews": [R("Caitlynn", 5, "2026-08-29", "Easy to assemble, very sturdy, folds and unfolds easily and fits in the trunk."),
                 R("Makayla", 5, "2026-09-11", "Rides very smoothly and quietly; makes getting out of the house easy."),
                 R("Silvia", 4, "2026-09-08", "Eleven months in, both pieces have been solid; the car seat headrest isn't very supportive.")]},
    data_note="The listing gives 22.7 lb for the stroller and 26 lb as item weight; we use the higher figure. The bullets say 4–30 lb for the car seat while the table says 35 lb; we use the bullet figure.")

add("maxi-cosi-zelia2-luxe", "B0CBQH9ZXC", "Maxi-Cosi Zelia² Luxe 5-in-1 Modular Travel System", "Maxi-Cosi Zelia² Luxe", "Maxi-Cosi", "Zelia² Luxe", "Travel system",
    "81VMo02DKoL 81Q7-bSnESL 71yQpx2hsGL 81jTV+EGRZL 81MxEwRoZIL 71fRMeOt-ZL 71rtnz6cOnL 81jeTl3c0LL",
    [], AMZ, 439.99, 549.99, "In stock · 400+ bought last month", 4.3, 1215, bd(75, 5, 5, 3, 12),
    dict(weight_lb=25, self_standing=True, newborn="flat", recline="Reversible carriage (flat) and reclining seat",
         reversible_seat=True, canopy="MaxShade, UPF 50, zip-out mesh", wheels="4, all-terrain tread", suspension="All-wheel",
         car_seat="Included: Maxi-Cosi Mico Pro + base (4–30 lb)", car_seat_fit="Maxi-Cosi infant seats", harness="5-point"),
    {"Modes": "Car seat caddy, reversible carriage, reversible stroller (5 ways)"}, SRC, dict(ride=7, comfort=8, storage=6, safety=8, build=6, value=7),
    {"tagline": "A modular travel system with a reversible carriage for newborns.",
     "summary": "Five ways to stroll, including a flat reversible carriage, plus the plush Mico Pro car seat. Stylish and comfortable, with a weaker rating spread than the Graco systems.",
     "body": ["The Zelia² Luxe is a modular stroller: use it as a car seat caddy with the included Mico Pro, as a flat carriage for a newborn, or as a seat facing either way. All-wheel suspension and treaded wheels make it comfortable on rough sidewalks, and the MaxShade canopy is one of the biggest here.",
              "The Mico Pro (4–30 lb) uses PureCosi fabric without added flame retardants and a ventilated shell. The stroller folds and stands upright; the listing gives 25 lb for the stroller seat and frame.",
              "Most parents love the look and the ride, but 12% of ratings are one-star, mostly about quality control and parts; Maxi-Cosi's customer service gets credit for fixing problems."],
     "pros": ["Flat carriage mode from birth", "Includes Mico Pro + base", "All-wheel suspension", "Big MaxShade canopy"],
     "cons": ["12% one-star ratings", "Heavy-ish at 25 lb", "Child limit not published on the listing"],
     "ideal_for": "Parents who want a stylish modular system with a true carriage mode.",
     "not_for": "Anyone who wants the most proven, lowest-risk option.",
     "verdict": "Comfortable and versatile, with more quality complaints than we'd like.",
     "review_summary": "4.3★ from 1,215 ratings (80% four or five stars). Owners praise the look, ride and 5-in-1 design; 12% one-star reviews cite quality issues, often resolved by customer service.",
     "reviews": [R("Nayla Gutiérrez", 5, "2026-10-10", "Feels sturdy yet easy to maneuver, and the 5-in-1 design adapts as the baby grows."),
                 R("Amazon Customer", 5, "2026-09-15", "As a first-time mom, the carriage mode is great for walking around events."),
                 R("Amazon Customer", 1, "2025-06-13", "Bought despite quality worries in the reviews and ran into the same problems.")]},
    data_note="The listing's 46 lb item weight includes the car seat and base; we use the 25 lb stroller figure.",
    from_birth="Yes — flat carriage mode")

add("graco-outpace-lx", "B0CLBCWTDG", "Graco Outpace LX All-Terrain Travel System", "Graco Outpace LX", "Graco", "Outpace LX", "Travel system",
    "71CN9ZAcpXL 71ajrXfT7TL 91BZyoLac-L 91404IjQSSL 917IUKXEtfL 81Fhwj5qsSL 810X2RYn1qL A1bw3Th4YOL",
    ["all-terrain"], AMZ, 359.99, None, "In stock · 300+ bought last month", 4.5, 831, bd(78, 10, 4, 3, 5),
    dict(one_hand_fold=True, self_standing=True, newborn="carseat", recline="Multi-position", canopy="Multi-panel, extendable",
         wheels="3, never-flat rubber", suspension="In-seat (ComfiTech)",
         car_seat="Included: Graco SnugRide Lite + base (4–30 lb)", car_seat_fit="Graco SnugRide (Click Connect)", cup_holder=True,
         harness="5-point, magnetic buckle"),
    {"Not for jogging": "All-terrain stroller, not rated for running"}, SRC, dict(ride=7, comfort=6, storage=6, safety=8, build=6, value=8),
    {"tagline": "A three-wheel all-terrain travel system with never-flat tires.",
     "summary": "Jogger looks without the jogging: three never-flat rubber tires, in-seat suspension and a SnugRide Lite car seat, with a one-hand standing fold.",
     "body": ["The Outpace LX is built for parks, gravel paths and broken sidewalks. Its three rubber tires never go flat, the seat has its own suspension, and it steers easily with one hand. It's an all-terrain stroller, not a running stroller — there's no locking front wheel or hand brake for jogging.",
              "The included SnugRide Lite (4–30 lb) clicks onto the frame for newborns, and the magnetic harness buckle makes toddler ins and outs quick. Graco's listing contradicts itself on weight (19 lb vs 34 lb), so we leave it blank.",
              "Owners like the easy fold and smooth steering; a few find the frame a bit wobbly for the price."],
     "pros": ["Never-flat all-terrain tires", "Includes SnugRide Lite + base", "One-hand standing fold", "Magnetic buckle"],
     "cons": ["Not for jogging", "Weight unclear", "Some find the frame wobbly"],
     "ideal_for": "Parents who walk parks and trails more than malls.",
     "not_for": "Runners — get a jogging-rated stroller.",
     "verdict": "A rugged everyday travel system for outdoorsy walks.",
     "review_summary": "4.5★ from 831 ratings (88% four or five stars). Parents praise the one-hand fold and smooth steering; some mention the car seat doesn't always latch first time.",
     "reviews": [R("NattyM21", 5, "2026-09-12", "Opens and closes easily, steers smoothly and the car seat snaps in and out effortlessly."),
                 R("Kay", 5, "2026-03-30", "Sturdy enough for a 25 lb eight-month-old after a long search."),
                 R("Morgan T", 4, "2026-03-11", "Likes it, but it feels a little flimsy and wobbles easily.")]},
    data_note="The listing gives two conflicting weights (19 lb and 34.1 lb). We show weight as unpublished until Graco confirms it.")

add("graco-verb", "B07B7QC71X", "Graco Verb Lightweight Travel System", "Graco Verb", "Graco", "Verb", "Travel system",
    "71rqETkF9pL 91uoFfTeINL 71dt+1PgFFL 91cAfwf8kNL 91mx72LUZiL 81w76HbI1wL 91sl1jvv93L 71-xDbwaraL",
    [], AMZ, 239.99, None, "Only 10 left in stock · 200+ bought last month", 4.6, 1832, bd(83, 9, 4, 1, 3),
    dict(one_hand_fold=True, self_standing=True, newborn="carseat", recline="Multi-position", canopy="Extendable",
         wheels="4, locking front swivel", suspension="Yes", car_seat="Included: Graco SnugRide Lite + base (4–30 lb)",
         car_seat_fit="Graco SnugRide (Click Connect)", cup_holder=True, harness="5-point"),
    {"Carry": "Carry strap on the fold"}, SRC, dict(ride=5, comfort=5, storage=5, safety=8, build=6, value=9),
    {"tagline": "The most affordable travel system here, with a self-standing fold.",
     "summary": "A lightweight, budget travel system: SnugRide Lite car seat and base, suspension and a one-hand standing fold with a carry strap.",
     "body": ["The Verb pairs a compact stroller with Graco's SnugRide Lite infant seat (4–30 lb) and base. The car seat clicks on in one step, the front wheels lock for straight-line pushing, and the fold is one-handed, self-standing and has a carry strap.",
              "It's simpler than the Modes systems: the seat faces forward only and there's no flat newborn mode without the car seat. The listing's weight figures don't add up, so we don't publish one; owners describe it as light and trunk-friendly.",
              "One owner reports five years of use with no issues. The most common wish is better head support in the car seat."],
     "pros": ["Lowest-priced travel system here", "Includes car seat + base", "One-hand standing fold", "Suspension"],
     "cons": ["Forward-facing seat only", "Basic canopy", "Weight not clearly published"],
     "ideal_for": "Budget-minded parents who want a car seat and stroller that fit a small trunk.",
     "not_for": "Parents who want a parent-facing seat.",
     "verdict": "The best budget travel system.",
     "review_summary": "4.6★ from 1,832 ratings (92% four or five stars). Parents praise the light weight, one-hand fold and small trunk footprint; a few wanted more infant head support.",
     "reviews": [R("SuperSuper", 5, "2026-08-15", "Light, maneuverable and folds with one hand — handy when juggling a baby and bags."),
                 R("RIPTON", 5, "2026-05-09", "Fits a non-SUV trunk without taking all the space, and the car seat is light."),
                 R("W.K 90", 5, "2026-05-07", "Five years of use with no problems, though a little heavy to carry.")]},
    data_note="The spec table lists 18.85 lb for the whole set, 8.1 lb for the stroller and 10.9 lb for the car seat; those figures don't match Graco's frame, so we don't publish a stroller weight.")

# ================================================================ full-size
add("uppababy-vista-v3", "B0D9XRK8RM", "UPPAbaby Vista V3 Convertible Single-to-Double Stroller", "UPPAbaby Vista V3", "UPPAbaby", "Vista V3", "Full-size",
    "71gMzLkyH-L 81pHXeWCjUL 713K-N5p-DL 71EHrleB1ML 91vfGFhAlUL 71XRiuiVx1L 71WBEavSf3L 918CtYgOx8L",
    ["convertible", "all-terrain"], AMZ, 899.99, None, "In stock · 100+ bought last month", 4.6, 583, bd(84, 7, 3, 2, 4),
    dict(weight_lb=27, folded_size="16.3 in wide × 33.8 in tall", self_standing=True, newborn="flat", max_child_lb=50,
         recline="Multi-position, one-hand", reversible_seat=True, canopy="UPF 50+, extendable, water-repellent", seats=1,
         wheels="4, never-flat (11.3 in rear, 8.1 in front)", suspension="All-wheel (FlexRide)",
         car_seat_fit="UPPAbaby Mesa and Aria without adapters; others with adapters", basket_lb=30, adjustable_handle=True,
         cup_holder=False, harness="5-point, magnetic buckle"),
    {"Grows to": "2–3 children with add-on seats (RumbleSeat, PiggyBack)", "In the box": "Toddler seat, bassinet, bug and rain shields",
     "Fabric": "GREENGUARD Gold certified"},
    SRC + " Bassinet included per UPPAbaby's U.S. box contents.", dict(ride=9, comfort=9, storage=10, safety=9, build=10, value=6),
    {"tagline": "The premium stroller that grows from one child to three.",
     "summary": "The benchmark full-size stroller: a bassinet from birth, a 50 lb toddler seat, a 30 lb basket and a frame that takes a second (and third) seat later.",
     "body": ["The Vista V3 is what most premium stroller shoppers end up comparing everything else to. It starts as a bassinet stroller for newborns, switches to a reversible toddler seat to 50 lb, and with add-on seats carries two or three children. UPPAbaby's own Mesa and Aria car seats click straight onto the frame.",
              "The ride is the smoothest here among non-joggers: big never-flat wheels and all-wheel suspension, a telescoping handlebar for tall parents, and a 30 lb basket that swallows a diaper bag and groceries. At 27 lb it's heavy, and it folds in one step and stands on its own.",
              "Owners call it a buy-once stroller and say it holds its value. The price is the obvious downside, along with the cost of the add-on seats."],
     "pros": ["Bassinet from birth, seat to 50 lb", "Converts to a double (or triple)", "Huge 30 lb basket", "Smooth all-wheel suspension"],
     "cons": ["$550+ price band", "27 lb and bulky", "Second seat and adapters cost extra"],
     "ideal_for": "Families planning a second child who want one stroller for years.",
     "not_for": "Small trunks, frequent flyers or tight budgets.",
     "verdict": "The best stroller money can buy for a growing family.",
     "review_summary": "4.6★ from 583 ratings (91% four or five stars). Owners praise the build quality, smooth ride and basket; the main complaint is price.",
     "reviews": [R("Calvin C.", 5, "2026-07-02", "Pricey, but a buy-once purchase that grows with the family and rides smoothly."),
                 R("jammers", 5, "2026-09-02", "Two years of daily use and it still drives smoothly and holds up well."),
                 R("Donna Outten", 5, "2025-04-14", "Chosen for the basket space and all-weather seat after a lot of research.")]},
    badge="Best premium stroller",
    from_birth="Yes — included bassinet")

add("city-mini-gt3", "B0DWYK1WVS", "Baby Jogger City Mini GT3 All-Terrain Stroller", "City Mini GT3", "Baby Jogger", "City Mini GT3", "Full-size",
    "71t44gLpjRL 819CUs34+vL 81-ozac5RzL 91k1XlKAvrL 91zbE6jvuIL 91XSPdtjNOL 916MhDJAfoL 81xLeo+UoQL",
    ["all-terrain"], AMZ, 479.99, None, "In stock · 50+ bought last month", 4.5, 465, bd(74, 14, 5, 2, 5),
    dict(weight_lb=21.8, one_hand_fold=True, newborn="carseat", max_child_lb=65, recline="Near-flat, multi-position",
         canopy="UV 50+, full coverage, 3 peekaboo windows", wheels="3, Forever Air rubber", suspension="All-wheel",
         car_seat_fit="Baby Jogger and Graco Click Connect (adapters included); Nuna with adapter", basket_lb=10,
         adjustable_handle=True, cup_holder=True, harness="5-point, magnetic buckle"),
    {"Not for jogging": "Brand says it isn't intended for running", "Disney": "Meets Disney park size rules"},
    SRC, dict(ride=8, comfort=7, storage=5, safety=8, build=8, value=7),
    {"tagline": "A one-hand-fold all-terrain stroller that carries kids to 65 lb.",
     "summary": "Baby Jogger's famous one-hand fold with rubber all-terrain tires, all-wheel suspension and the highest child limit here outside the joggers (65 lb).",
     "body": ["The City Mini GT3 folds by pulling one strap in the seat — still one of the quickest folds on any full-size stroller. Forever Air rubber tires and all-wheel suspension take it from city cracks to dirt paths, and the seat reclines near-flat with an adjustable calf rest.",
              "Infant car seat adapters for Baby Jogger and Graco Click Connect seats come in the box, so it's an easy travel system for newborns. The 65 lb child limit means it lasts into the preschool years. The basket is small (10 lb).",
              "Reviews on this listing are shared with the GT2 and the double version; owners consistently praise the fold and smooth push."],
     "pros": ["Famous one-hand fold", "Rubber all-terrain tires", "Child up to 65 lb", "Car seat adapters included"],
     "cons": ["Small 10 lb basket", "Not for jogging", "Reviews shared with other versions"],
     "ideal_for": "Parents who want an all-terrain stroller that folds in a second.",
     "not_for": "Families who haul a lot of gear.",
     "verdict": "The best one-hand-fold all-terrain stroller.",
     "review_summary": "4.5★ from 465 ratings (88% four or five stars). Owners love the fold, smooth push and premium feel; some reviews describe the GT2 or the double model.",
     "reviews": [R("Griselle", 5, "2026-06-04", "Looks and feels premium; fits her tall almost-two-year-old who outgrew a lighter stroller."),
                 R("Kathleen", 5, "2025-09-30", "Smooth to push and handles all kinds of terrain as a travel system."),
                 R("Brittney Weideman", 4, "2024-07-11", "The fold is amazing and compact, though some details could be better for the price.")]},
    review_note="This listing shares reviews with the City Mini GT2 and the GT2 Double.")

add("mompush-wiz", "B093GS5723", "Mompush Wiz 2-in-1 Bassinet Stroller with Reversible Seat", "Mompush Wiz", "Mompush", "Wiz", "Full-size",
    "71OP129uY3L 81onyr3jS9L 71aE0PjabNL 719ZfgTiUaL 71FG92vEedL 81jDpcHPM1L 81Bie5cOFyL 81disesvZEL",
    [], AMZ, 159.99, None, "In stock · 800+ bought last month", 4.6, 3707, bd(78, 11, 5, 2, 4),
    dict(weight_lb=23.1, one_hand_fold=True, newborn="flat", max_child_lb=50, recline="3 positions (100°, 145°, 175°) + pramette mode",
         reversible_seat=True, canopy="UPF 50+, zip-out, ventilation panels", wheels="4, 360° swivel (9.4 in rear)", suspension="Yes",
         car_seat_fit="Maxi-Cosi and Nuna with adapter (sold separately)", basket_lb=10, adjustable_handle=True, cup_holder=True,
         harness="5-point"),
    {"Extras": "Foot cover, cup holder, mattress pad"}, SRC, dict(ride=7, comfort=8, storage=5, safety=7, build=7, value=10),
    {"tagline": "A flat bassinet-mode stroller with a reversible seat, under $200.",
     "summary": "The value pick: a seat that converts to a flat bassinet for newborns, faces either way, reclines to 175° and folds with one hand — at a fraction of premium prices.",
     "body": ["The Wiz does what $500+ strollers do for newborns: its seat converts into a flat, enclosed pramette, so a newborn can lie flat on walks without a car seat. Later it becomes a reversible seat with three recline positions up to 175°, for children up to 50 lb.",
              "It folds with one hand, has a telescoping handlebar, a UPF 50+ zip-out canopy and suspension. At 23.1 lb it's no lightweight, and the basket holds 10 lb. Car seats from Maxi-Cosi and Nuna fit with a separate adapter.",
              "With 3,700+ ratings at 4.6★, owners repeatedly say it compares well with Chicco, Nuna and Cybex models costing far more."],
     "pros": ["Flat pramette mode from birth", "Reversible seat", "One-hand fold", "Under $200"],
     "cons": ["23 lb", "10 lb basket", "Car seat adapter sold separately"],
     "ideal_for": "Parents who want a newborn-ready full-size stroller on a budget.",
     "not_for": "Air travel or very small trunks.",
     "verdict": "The best value full-size stroller on Amazon.",
     "review_summary": "4.6★ from 3,707 ratings (89% four or five stars). Parents praise the bassinet mode, smooth push and value; a few find it bulky.",
     "reviews": [R("Jill Hanstine", 5, "2026-09-23", "After months comparing Chicco, Nuna and Cybex, this was the one they were happiest with."),
                 R("Allie", 5, "2026-08-23", "Daily 2–3 mile walks for eight weeks; the bassinet lets her newborn lie flat."),
                 R("Jody Riedinger", 5, "2025-03-20", "Easy brake, smooth wheels, easy conversion and a nice canopy.")]},
    featured=True, badge="Best value full-size",
    from_birth="Yes — flat pramette mode")

# ================================================================ travel strollers
add("gb-pockit-air", "B07S3XDZDV", "gb Pockit Air All-Terrain Compact Travel Stroller", "gb Pockit Air", "gb", "Pockit Air All-Terrain", "Travel stroller",
    "51Sji7ywJAL 71Gc26c+PbL 61gDEnCnp6L 61+kEwxcALL 61GuZJ+NZ-L 61C961R+E+L 51wyTQ6B+SL 712EpkuZ93L",
    [], AMZ, 189.99, None, "In stock · 300+ bought last month", 4.5, 2328, bd(77, 12, 5, 2, 4),
    dict(weight_lb=10.4, one_hand_fold=False, self_standing=True, carry_on=True, max_child_lb=55, recline=None,
         canopy="Small UPF 50+ sun visor", wheels="8 small double wheels (4.7 in)", basket_lb=11),
    {"Seat back": "Breathable mesh"}, SRC + " Recline and harness type aren't clearly stated, so we leave them blank.",
    dict(ride=4, comfort=4, storage=4, safety=6, build=6, value=8),
    {"tagline": "The lightest stroller here, folding to handbag size.",
     "summary": "At 10.4 lb with a tiny fold that fits overhead bins, the Pockit Air is the ultimate backup and travel stroller — for kids 6 months and up.",
     "body": ["The Pockit Air folds into a package about the size of a large handbag and weighs 10.4 lb, making it the easiest stroller here to carry through airports, onto trains and into small trunks. Double wheels help on cobblestones.",
              "It's a minimalist: a small sun visor rather than a full canopy, no newborn mode, and a simple seat for children from about 6 months to 55 lb. The fold takes two hands but locks automatically.",
              "Travel families love it — reviewers have taken it to Rome, England, Spain and Disney World. Some say it feels loose at first and improves once you get used to it."],
     "pros": ["Lightest here (10.4 lb)", "Tiny handbag-size fold", "Fits overhead bins", "Holds kids to 55 lb"],
     "cons": ["Not for newborns", "Small sun visor", "Bumpy on small wheels"],
     "ideal_for": "Flights, city breaks and a backup stroller in the car.",
     "not_for": "Everyday walks with a young baby.",
     "verdict": "The lightest, smallest travel stroller we cover.",
     "review_summary": "4.5★ from 2,328 ratings (89% four or five stars). Families love it for flights and theme parks; some find it flimsy until they get used to it.",
     "reviews": [R("Lauren Curry", 5, "2025-11-17", "Perfect for a week in Rome with a four-year-old: light and folds in seconds."),
                 R("KrisV", 5, "2023-02-06", "Saved their Disney World trip, carrying a 40 lb six-year-old."),
                 R("Ita", 4, "2025-06-04", "Felt like a loose suitcase at first, then she fell in love with it.")]},
    badge="Lightest stroller")

add("city-tour-2", "B07NZPT3TR", "Baby Jogger City Tour 2 Carry-On Travel Stroller", "City Tour 2", "Baby Jogger", "City Tour 2", "Travel stroller",
    "71BGwyf+XvL 718qiTWFjJL 71nUqn-dUJL 91lmczJPcqL 71lYuqTs5wL 71sCR1OtD1L 81voUrkmDUL 71yWWVxd-TL",
    [], AMZ, 299.99, None, "In stock · 100+ bought last month", 4.5, 1230, bd(76, 12, 6, 3, 3),
    dict(weight_lb=14.3, carry_on=True, newborn="carseat", recline="Near-flat, multi-position", canopy="UV 50+, extension panel, peekaboo",
         wheels="4, locking front swivel", car_seat_fit="Baby Jogger infant seats with adapters (sold separately)", basket_lb=15,
         cup_holder=True, harness="5-point", warranty="Limited lifetime on the frame"),
    {"Carry bag": "Included", "Calf support": "Adjustable"}, SRC, dict(ride=5, comfort=7, storage=6, safety=7, build=8, value=7),
    {"tagline": "A carry-on travel stroller with a near-flat recline and lifetime frame warranty.",
     "summary": "A briefcase-size fold, 15 lb basket, near-flat recline and adjustable calf rest — more comfortable than most ultra-compacts, with Baby Jogger's lifetime frame warranty.",
     "body": ["The City Tour 2 folds in one step to roughly briefcase size and is approved as airline carry-on by Baby Jogger. Unlike the barest travel strollers it keeps real comforts: a near-flat recline for naps, adjustable calf support and a 15 lb basket.",
              "With adapters (sold separately) it accepts Baby Jogger infant car seats, so it can work from birth. At 14.3 lb it's not the lightest here, but it's sturdier than most and backed by a limited lifetime warranty on the frame.",
              "Parents report overhead-bin success and smooth one-handed pushing through airports; a few wish the wheels were bigger."],
     "pros": ["Carry-on size fold", "Near-flat recline", "15 lb basket", "Lifetime frame warranty"],
     "cons": ["Car seat adapters extra", "Small wheels", "Higher price band for a travel stroller"],
     "ideal_for": "Frequent flyers who want a travel stroller that's comfortable for naps.",
     "not_for": "Rough paths or tight budgets.",
     "verdict": "The most comfortable carry-on stroller here.",
     "review_summary": "4.5★ from 1,230 ratings (88% four or five stars). Travelers praise the compact fold, overhead-bin fit and comfort.",
     "reviews": [R("Amazon Customer", 5, "2024-01-19", "Folds to briefcase size and fit the overhead bin, surprising the flight crew."),
                 R("Jenn Ginter", 5, "2025-02-17", "Took it on a cruise with an eight-month-old and it was perfect."),
                 R("Dan", 4, "2022-12-01", "Nearly perfect for travel; easy to steer one-handed through the airport.")]})

add("mamazing-ultra-air", "B0CX999YMH", "Mamazing Ultra Air Lightweight Travel Stroller (Carbon Fiber)", "Mamazing Ultra Air", "Mamazing", "Ultra Air", "Travel stroller",
    "71aWyYdDT8L 71jgiA9hUXL 715FcWuFjpL 71vsLi2EU6L 61U0O71b4vL 81KcAa2NOLL 71-ZkXB+JaL 719WnU5koWL",
    [], "Tukarla (ships from Amazon)", 199.99, 249.99, "In stock · 1K+ bought last month", 4.6, 2120, bd(82, 9, 4, 2, 3),
    dict(weight_lb=11.6, folded_size="20.6 × 18.5 × 11 in", one_hand_fold=True, carry_on=True, recline="Multi-position",
         canopy="UPF 50+, multi-panel, peekaboo", wheels="4, front suspension", suspension="Front", basket_lb=22, harness="5-point"),
    {"Frame": "Carbon fiber", "Extras": "Travel bag, zip pocket"}, SRC + " Minimum age isn't stated by the brand.",
    dict(ride=5, comfort=5, storage=6, safety=6, build=6, value=8),
    {"tagline": "An 11.6 lb carbon-fiber travel stroller with a one-hand fold.",
     "summary": "One of the lightest strollers here with a proper canopy, one-hand fold and a surprisingly big basket — popular as both a travel and daily stroller.",
     "body": ["The Ultra Air uses a carbon-fiber frame to hit 11.6 lb while keeping a full UPF 50+ canopy with a peekaboo window, a multi-position recline and a 22 lb basket claim. It folds with one hand to 20.6 × 18.5 × 11 in and owners report it fitting airplane overhead bins.",
              "Mamazing doesn't state a minimum age, so we treat it as a stroller for babies who can sit up (about 6 months). There's no car seat compatibility.",
              "With 1,000+ sold a month and 91% four or five stars, many parents say it became their everyday stroller after a trip."],
     "pros": ["11.6 lb", "One-hand fold", "Full canopy", "Big basket for the size"],
     "cons": ["No newborn option", "No car seat compatibility", "Third-party seller"],
     "ideal_for": "Families who fly often and want a light stroller that still has a real canopy.",
     "not_for": "Newborns.",
     "verdict": "A light, well-equipped travel stroller that doubles as a daily one.",
     "review_summary": "4.6★ from 2,120 ratings (91% four or five stars). Owners praise the weight, quick fold and overhead-bin fit.",
     "reviews": [R("Tyler", 5, "2026-07-17", "Fit in the airplane overhead bin with no issues from the crew."),
                 R("Suzy Larson", 5, "2026-07-07", "Six weeks in Europe, mostly Prague, and it handled everything."),
                 R("Kathy", 4, "2026-07-29", "Light enough to carry one-handed; likes the shade cover and zip pocket.")]},
    from_birth="Not stated — we'd use it from about 6 months")

add("mompush-lithe-v2", "B0B7MJN7JJ", "Mompush Lithe V2 Lightweight Travel Stroller", "Mompush Lithe V2", "Mompush", "Lithe V2", "Travel stroller",
    "7133sffkyNL 811WJtIFrpL 71kPf31QdhL 81Lin4Tei-L 81A6735VmAL 711FiOWFrAL 71mpyF212zL 61F+Jt3Pe+L",
    [], AMZ, 179.99, None, "In stock · 300+ bought last month", 4.5, 1985, bd(76, 12, 5, 2, 5),
    dict(weight_lb=17.4, folded_size="21.3 × 11 × 27 in", one_hand_fold=True, self_standing=True, carry_on=True, newborn="flat",
         recline="3 positions, near-flat 175°", canopy="UPF 50+, extendable, ventilated peekaboo", wheels="4, front suspension",
         suspension="Front", basket_lb=4.4, cup_holder=True, harness="5-point", jpma=True),
    {"Extras": "Snack tray, rain cover, foot cover, travel bag"}, SRC, dict(ride=6, comfort=7, storage=3, safety=7, build=7, value=9),
    {"tagline": "A JPMA-certified travel stroller that reclines flat enough for newborns.",
     "summary": "The rare travel stroller usable from birth: 175° recline, one-hand self-standing fold, snack tray and rain cover included.",
     "body": ["The Lithe V2 reclines to 175°, which Mompush says suits newborns, so you can travel without a separate bassinet or car seat. It folds with one hand in about a second, stands on its own, and Mompush says it meets most airline cabin size rules.",
              "You get a lot in the box: snack tray, cup holder, rain cover, a foot cover that tucks under the footrest and a travel bag. It's JPMA certified. The catch is the tiny 4.4 lb basket, and at 17.4 lb it's heavier than the ultralights.",
              "Parents recommend it widely for Disney trips and long European vacations."],
     "pros": ["Near-flat 175° recline from birth", "One-hand standing fold", "JPMA certified", "Rain cover and tray included"],
     "cons": ["Tiny 4.4 lb basket", "17.4 lb", "No car seat compatibility"],
     "ideal_for": "Traveling with a young baby who needs to nap flat.",
     "not_for": "Parents who carry a lot in the basket.",
     "verdict": "The best travel stroller for babies under 6 months.",
     "review_summary": "4.5★ from 1,985 ratings (88% four or five stars). Owners praise the smooth push, recline and included extras; the basket is the common complaint.",
     "reviews": [R("tiff", 5, "2026-09-14", "Bought for Disneyland; it maneuvers smoothly and the snack tray is a huge plus."),
                 R("babbs", 5, "2026-01-02", "After 2.5 weeks in Europe and bringing it on board, she rates it 10/10."),
                 R("Angie Quisay", 4, "2026-05-07", "Light and practical for trips, appointments and errands.")]},
    from_birth="Yes — reclines near-flat (175°)")

add("graco-ready2jet", "B0D2LXK44T", "Graco Ready2Jet Lightweight Compact Travel Stroller", "Graco Ready2Jet", "Graco", "Ready2Jet", "Travel stroller",
    "714WAYwO95L 71JPjM18qYL 91HcINqnbYL 71GvQPMZurL 91sQjY5eQ8L 71PdZ+mXoDL A1MFnhP8oSL 71-xDbwaraL",
    [], AMZ, 189.99, None, "In stock · 1K+ bought last month", 4.5, 858, bd(77, 11, 5, 3, 4),
    dict(weight_lb=13.2, one_hand_fold=True, self_standing=True, carry_on=True, newborn="carseat", max_child_lb=50,
         recline="Multi-position", canopy="UV 50, extended", wheels="4, all-wheel suspension", suspension="All-wheel",
         car_seat_fit="All Graco SnugRide infant seats (no adapter)", cup_holder=True, harness="Convertible 3- or 5-point"),
    {"Belly bar": "Removable, doubles as carry handle", "Calf support": "Adjustable"}, SRC, dict(ride=6, comfort=6, storage=5, safety=8, build=6, value=9),
    {"tagline": "A 13.2 lb auto-folding travel stroller that takes Graco car seats.",
     "summary": "The 'budget Doona' setup: an overhead-friendly travel stroller that folds itself and clicks onto any Graco SnugRide car seat — usable from birth with your car seat.",
     "body": ["The Ready2Jet folds automatically with one hand into a self-standing compact package and weighs 13.2 lb. Graco calls it overhead-bin friendly (check your airline). It's fully featured for its size: all-wheel suspension, multi-position recline, adjustable calf support and a parent cup holder.",
              "The big advantage is car seat compatibility: any Graco SnugRide infant seat clicks on without adapters, so it works from day one if you already own one. It carries children up to 50 lb.",
              "Owners love how easy travel becomes; one long-term owner reports the canopy wearing out after about 21 months and a seat dip some kids dislike."],
     "pros": ["13.2 lb auto fold", "Takes Graco SnugRide seats", "All-wheel suspension", "Under $200"],
     "cons": ["Canopy durability", "Seat has a dip", "Basket size not published"],
     "ideal_for": "Graco car seat owners who want a light stroller for trips and errands.",
     "not_for": "Parents with a non-Graco car seat.",
     "verdict": "The best travel stroller for Graco car seat families.",
     "review_summary": "4.5★ from 858 ratings (88% four or five stars). Parents praise the automatic fold and car seat fit; a few report canopy wear.",
     "reviews": [R("Rina_Stuff!", 5, "2026-02-27", "Wanted a Doona-like setup without the price; the Graco car seat clips in perfectly."),
                 R("Marni Baluta", 5, "2026-09-20", "Folds like a suitcase and takes their Graco car seat, so it goes everywhere."),
                 R("bryan", 4, "2026-08-16", "After 21 months the canopy is falling apart, though the frame has held up.")]},
    featured=True, badge="Best travel stroller")

add("munchkin-sparrow", "B0BF6X9TFN", "Munchkin Sparrow Ultra-Compact Travel Stroller", "Munchkin Sparrow", "Munchkin", "Sparrow", "Travel stroller",
    "91UjWVSeNpL 91+HomheX4L 71OG8HzDSFL 81p66zUg3PL 71V5eP+EuFL 71LLFaC2FvL 71QwU8mfpfL 81mTyq6bfCL",
    [], AMZ, 186.99, 204.99, "In stock · 50+ bought last month", 4.5, 792, bd(78, 10, 7, 1, 4),
    dict(weight_lb=12.8, folded_size="15 × 14 × 6.25 in", carry_on=True, max_child_lb=55, recline="Upright only",
         canopy="Extendable sun shade", wheels="4, dual front wheels", cup_holder=True, harness="5-point"),
    {"Rider": "Must sit upright unassisted; up to 41 in tall", "Carry bag": "Included"}, SRC,
    dict(ride=3, comfort=4, storage=3, safety=6, build=6, value=7),
    {"tagline": "The smallest fold here — 15 × 14 × 6.25 in.",
     "summary": "An ultra-compact stroller that fits under some airplane seats, for kids who sit up on their own. Tiny and simple, not plush.",
     "body": ["The Sparrow folds forward into a 15 × 14 × 6.25 in package with a zip carry bag — small enough for a backpack-size space and most overhead bins. At 12.8 lb it's among the lightest strollers we cover, and it needs no assembly.",
              "It's for toddlers who sit upright unassisted, up to 55 lb and 41 in. The seat doesn't recline, the basket is small and the wheels are tiny, so it's a travel tool rather than a daily stroller.",
              "Parents of several kids call it the most portable stroller they've owned; a few report the wheels not always folding in cleanly."],
     "pros": ["Smallest fold here", "12.8 lb", "Kids to 55 lb", "No assembly"],
     "cons": ["No recline", "Not for babies under ~6 months", "Small wheels and basket"],
     "ideal_for": "Flights and road trips with a toddler.",
     "not_for": "Naps on the go or daily walks.",
     "verdict": "The most packable stroller for toddler travel.",
     "review_summary": "4.5★ from 792 ratings (88% four or five stars). Families praise the tiny fold for flights; the main complaints are no recline and sticky wheels when folding.",
     "reviews": [R("Semra Ergun", 5, "2024-08-11", "Wishes she'd bought it before two earlier flights instead of a cheap umbrella stroller."),
                 R("Lacey M.", 5, "2024-07-27", "Mother of three; folds small with a bag and worked well for her two-year-old on a flight."),
                 R("Sundown Hunter", 4, "2023-07-10", "Folds really small, but the wheels sometimes don't tuck in correctly.")]},
    from_birth="No — child must sit up unassisted")

# ================================================================ double / convertible
add("momcozy-changego", "B0DJXX76MN", "Momcozy ChangeGo Single-to-Double-to-Wagon Stroller", "Momcozy ChangeGo", "Momcozy", "ChangeGo (ST01)", "Double",
    "71J598Y9fEL 71Tllkoc+KL 71078faADLL 719fjZMT7TL 81hlHvFIKfL 81agkxUPDrL 819jkpAyNsL 81t88aICzzL",
    ["convertible", "all-terrain"], "Momcozy Official Store", 559.99, 699.99, "In stock · 500+ bought last month", 4.4, 307, bd(72, 10, 7, 5, 6),
    dict(newborn="flat", max_child_lb=50, recline="Multi-position seat + flat carry-cot", reversible_seat=None,
         canopy="UPF 50+, extendable, peekaboo window", seats=2, wheels="4, rubber (10 in front, 12 in rear)", suspension="All-wheel (springs)",
         car_seat_fit="With adapter (sold separately)", basket_lb=19.8, adjustable_handle=True, harness="5-point"),
    {"In the box": "Carry-cot and toddler seat", "Configurations": "23 (wagon kit and adapters sold separately)",
     "Fabric": "OEKO-TEX certified"},
    SRC, dict(ride=8, comfort=8, storage=8, safety=7, build=7, value=7),
    {"tagline": "One frame that goes from carry-cot to double stroller to wagon.",
     "summary": "A carry-cot and toddler seat in the box, big rubber wheels with suspension, and the option to ride two kids — or turn it into a wagon — later.",
     "body": ["The ChangeGo is a modular single-to-double stroller: the included carry-cot gives a newborn a flat, enclosed bed, the included toddler seat takes up to 50 lb, and both can ride on the frame at once. Add the wagon kit (sold separately) and it becomes a wagon for kids up to about 6.",
              "Ten- and twelve-inch rubber wheels with spring suspension make it one of the smoother rides here, and the 19.8 lb basket is generous. The listing's 50.9 lb weight appears to include every part, so we don't publish a stroller weight; plan on a heavy, full-size frame.",
              "Owners with two kids under three call it a keeper after trying several doubles; 11% of ratings are one- or two-star."],
     "pros": ["Carry-cot + toddler seat included", "Rides two kids", "Big wheels, suspension", "19.8 lb basket"],
     "cons": ["Heavy", "Wagon kit and adapters extra", "Smaller review base"],
     "ideal_for": "Families expecting a second child soon who want one frame for years.",
     "not_for": "Small trunks or anyone who lifts the stroller often.",
     "verdict": "The most versatile double for the money.",
     "review_summary": "4.4★ from 307 ratings (82% four or five stars). Parents praise the ride, storage and versatility; complaints focus on weight and price.",
     "reviews": [R("Morgan", 5, "2025-12-31", "Six months of near-daily use with a baby and a tall 2.5-year-old; worth the cost."),
                 R("Serenity M.", 5, "2025-12-26", "After a Baby Trend, a Jeep double and a wagon, this is her favorite versatile stroller."),
                 R("Bailey Tappe", 4, "2026-06-16", "Sleek and versatile; the weight is acceptable for hauling two kids.")]},
    badge="Best single-to-double",
    data_note="The listing's 50.9 lb item weight appears to include the carry-cot, seat and accessories; Momcozy doesn't list the frame-and-seat weight separately.",
    from_birth="Yes — included carry-cot")

# ================================================================ jogging
add("bob-revolution-flex-3", "B0829PMJ8D", "BOB Gear Revolution Flex 3.0 Jogging Stroller", "BOB Revolution Flex 3.0", "BOB Gear", "Revolution Flex 3.0", "Jogging",
    "81Zca7wbEyL 817GaYmL4pL 81lUIto3ZQL 81DhfggNXHL 71rbcZw4FbL 71M+yZ3KwaL 711mRbrlRsL 81+A8569YGL",
    ["all-terrain"], AMZ, 519.99, 649.99, "In stock · 200+ bought last month", 4.7, 3220, bd(88, 5, 3, 1, 3),
    dict(weight_lb=28.5, newborn="carseat", recline="Strap-adjusted recline", canopy="Extra-large UPF 50+, magnetic peek window",
         wheels="3, air-filled (16 in rear, 12 in front), swivel-locking front", suspension="Adjustable, mountain-bike style", jogging=True,
         handbrake=None, car_seat_fit="Most major brands with a BOB adapter (sold separately)", adjustable_handle=True, cup_holder=True,
         harness="5-point, no-rethread"),
    {"Storage": "XL cargo basket + 6 pockets", "Handlebar": "9 positions", "Fold": "2-step"},
    SRC + " The spec table's 46.5 lb basket figure and hand-brake line aren't supported by BOB's bullets, so we leave both blank.",
    dict(ride=9, comfort=8, storage=8, safety=8, build=9, value=7),
    {"tagline": "The best-reviewed jogging stroller on Amazon.",
     "summary": "Air tires, adjustable suspension and a locking front wheel make the Revolution Flex the go-to stroller for runners and trail walkers.",
     "body": ["BOB's Revolution Flex 3.0 is the jogging stroller most others are measured against. Sixteen-inch air-filled rear tires, adjustable mountain-bike-style suspension and a front wheel that swivels for errands or locks straight for running give it a smooth, stable ride on pavement and trails.",
              "The handlebar has nine positions, the canopy is extra-large with a magnetic peek window, and there are six storage pockets plus an XL basket. It weighs 28.5 lb and the two-step fold is bulky, so it's not a trunk-friendly stroller.",
              "Car seats from most major brands fit with a BOB adapter. As with all joggers, BOB and pediatricians advise waiting until your baby is old enough before running. Reviews on this listing are shared with the Duallie double."],
     "pros": ["Smoothest jogging ride", "Adjustable suspension", "9-position handlebar", "4.7★ from 3K+ ratings"],
     "cons": ["28.5 lb, bulky fold", "Car seat adapter extra", "Reviews shared with the double"],
     "ideal_for": "Runners and parents who walk trails and gravel.",
     "not_for": "Small trunks or mostly indoor shopping.",
     "verdict": "The jogging stroller to beat.",
     "review_summary": "4.7★ from 3,220 ratings (93% four or five stars). Owners praise the ride, durability and handling; the common gripe is the awkward folded size. Many reviews describe the Duallie double.",
     "reviews": [R("Amazon Customer", 5, "2026-03-04", "Runs 3–12 miles a week for nearly two years and it still runs great."),
                 R("Lacy", 5, "2025-10-27", "Three years on the BOB and it's still in perfect condition."),
                 R("Britlyn Strauss", 5, "2026-06-24", "The best stroller she's owned, though it's awkward once folded.")]},
    badge="Best jogging stroller",
    review_note="Reviews on this listing are shared with the BOB Revolution Flex 3.0 Duallie (double).")

add("bob-alterrain-pro", "B07XV1WLSC", "BOB Gear Alterrain Pro Jogging Stroller", "BOB Alterrain Pro", "BOB Gear", "Alterrain Pro", "Jogging",
    "81qzFDryIPL 71+dqkra5eL 813PQ0FHjBL 81hEkIvRYhL 81BwxEUWapL 81UFUq1k+PL 71krSqYzVJL 91pSI1R1tLL",
    ["all-terrain"], AMZ, 663.99, 829.99, "In stock · 50+ bought last month", 4.5, 555, bd(78, 8, 6, 2, 6),
    dict(weight_lb=32.3, one_hand_fold=True, self_standing=True, newborn="carseat", recline="Infinite, near-flat",
         canopy="UPF 50+, 100% waterproof and windproof", wheels="3, air-filled (16 in rear, 12 in front), swivel-locking front",
         suspension="SmoothShox", jogging=True, handbrake=True, car_seat_fit="With BOB adapter (sold separately)",
         adjustable_handle=True, harness="5-point"),
    {"Storage": "XL zip-top basket + 5 pockets", "Tracking": "Adjustable front-wheel tracking"}, SRC,
    dict(ride=10, comfort=8, storage=8, safety=9, build=9, value=6),
    {"tagline": "BOB's top jogger, with a hand brake and waterproof canopy.",
     "summary": "Everything in the Revolution Flex plus a hand brake for downhills, SmoothShox suspension, a one-twist standing fold and a fully waterproof canopy.",
     "body": ["The Alterrain Pro is BOB's flagship. A handbrake on the handlebar controls speed on descents, SmoothShox suspension and air tires soak up trails, and the front wheel's tracking can be adjusted so it runs dead straight. The seat reclines infinitely to near-flat.",
              "The canopy is 100% waterproof and windproof with UPF 50+, the zip-top basket keeps gear dry, and the fold is a one-handed twist that stands on its own. At 32.3 lb it's the heaviest stroller here.",
              "Owners rate the ride and build highly; a few reported assembly problems with a wheel."],
     "pros": ["Hand brake for hills", "Best ride here", "Waterproof canopy", "One-hand standing fold"],
     "cons": ["Heaviest here (32.3 lb)", "$550+ price band", "Some assembly complaints"],
     "ideal_for": "Serious runners and hikers in hilly or wet places.",
     "not_for": "Flat-city walkers or anyone who lifts the stroller often.",
     "verdict": "The ultimate jogger if you run hills.",
     "review_summary": "4.5★ from 555 ratings (86% four or five stars). Owners praise the ride, quality and turning; a few report assembly issues.",
     "reviews": [R("Cheri", 5, "2025-09-15", "Used for jogging, walks and shopping — much smoother than any of their previous strollers."),
                 R("Sadie", 5, "2024-01-10", "Heavy, but she accepts it for the durability and quality."),
                 R("RawBeautyKristi", 4, "2021-04-26", "Assembly was a struggle because a wheel part was made incorrectly.")]})

add("summit-x3", "B09ZK14DQ6", "Baby Jogger Summit X3 Jogging Stroller", "Baby Jogger Summit X3", "Baby Jogger", "Summit X3", "Jogging",
    "61idPIIZoFL 91QnhkAkx-L 81s5U0nYOsL 81iqSi19zHL 81mK6mCizuL A1fzUR5gZzL 81hhm4pP8XL 81MBT3+BdxL",
    ["all-terrain"], AMZ, 439.99, 549.99, "In stock", 4.4, 355, bd(74, 12, 5, 3, 6),
    dict(weight_lb=28.6, one_hand_fold=True, newborn="carseat", max_child_lb=75, recline="Near-flat",
         canopy="UV 50+, peekaboo, magnetic side vents", wheels="3, air-filled", suspension="All-wheel", jogging=True, handbrake=True,
         car_seat_fit="Baby Jogger, Chicco, Graco, Peg Perego (adapters sold separately)", harness="5-point",
         warranty="Limited lifetime on the frame"),
    {"Jogging age": "Brand advises 6 months+ and asking your pediatrician", "Disney": "Meets Disney park size rules"}, SRC,
    dict(ride=9, comfort=7, storage=7, safety=9, build=8, value=8),
    {"tagline": "A hand-brake jogger with a 75 lb limit and lifetime frame warranty.",
     "summary": "Hand brake, all-wheel suspension, air tires and a one-hand fold for less than the BOBs — and it carries kids up to 75 lb.",
     "body": ["The Summit X3 is Baby Jogger's jogging stroller: three air-filled tires, all-wheel suspension and a hand brake for hills, plus a one-hand compact fold that's much easier than BOB's. It carries children to 75 lb, the highest limit here.",
              "The seat reclines near-flat with magnetic side vents for airflow, and car seats from Baby Jogger, Chicco, Graco and Peg Perego fit with adapters. The frame has a limited lifetime warranty. It weighs 28.6 lb.",
              "Owners praise the suspension and turning; some reviews on this listing describe the double version."],
     "pros": ["Hand brake", "One-hand fold", "Child to 75 lb", "Lifetime frame warranty"],
     "cons": ["28.6 lb", "Adapters extra", "Some reviews are for the double"],
     "ideal_for": "Runners who want hand-brake control without BOB pricing.",
     "not_for": "Parents who need a light stroller.",
     "verdict": "The best-value hand-brake jogger.",
     "review_summary": "4.4★ from 355 ratings (86% four or five stars). Owners praise the smooth suspension, hand brake and maneuverability.",
     "reviews": [R("Shawna Wipf", 5, "2026-09-08", "Great on paved and gravel roads and zoo trips, and folds to fit in her Tahoe."),
                 R("Michele Astemborski", 5, "2026-05-21", "Quick to assemble; the wrist strap and brakes feel reliable."),
                 R("Leslie", 4, "2023-10-01", "Rides very smoothly and she loves the 75 lb limit.")]},
    review_note="Some reviews on this listing are for the Summit X3 Double.")

add("baby-trend-expedition-jogger", "B0BYTK3JS5", "Baby Trend Expedition Jogger", "Baby Trend Expedition", "Baby Trend", "Expedition Jogger", "Jogging",
    "81Y8Duq21nL 819To6ejZyL 719gsc5qDoL 81d8LOS4dvL 81ccnkb7kfL 81y1f7zJt9L 91kFx7FNMPL 91B6IqJAuHL",
    ["all-terrain"], AMZ, 119.99, 149.99, "In stock · 600+ bought last month", 4.7, 5892, bd(83, 10, 3, 1, 3),
    dict(weight_lb=23.6, newborn="carseat", recline="Multi-position", canopy="Adjustable, covered sunroof, peekaboo",
         wheels="3, 16 in bicycle tires, lockable front swivel", suspension="None", jogging=True, handbrake=False,
         car_seat_fit="Baby Trend infant car seats (child tray mount)", cup_holder=True, harness="5-point"),
    {"Trays": "Parent tray (2 cups + covered storage) and child tray", "Jogging": "Wrist strap included"}, SRC,
    dict(ride=7, comfort=5, storage=7, safety=6, build=6, value=10),
    {"tagline": "A full jogging stroller under $150 with 5,800+ ratings.",
     "summary": "Big bicycle tires, a locking front wheel and trays for parent and child at a fraction of BOB prices. No suspension or hand brake.",
     "body": ["The Expedition is Amazon's best-selling budget jogger. Sixteen-inch bicycle tires roll easily over gravel, the front wheel locks for running, and it comes with a wrist strap, a parent tray with two cup holders and covered storage, and a child tray.",
              "There's no suspension and only a foot brake, so it's best on paths and moderate runs rather than steep trails. Baby Trend infant car seats mount on the child tray, making it a travel system from birth. It weighs 23.6 lb and folds with a trigger.",
              "With 4.7★ from 5,800+ ratings, owners call it excellent value; runners report 6-mile runs without problems."],
     "pros": ["Under $200", "16 in bicycle tires", "Parent and child trays", "4.7★ from 5.8K ratings"],
     "cons": ["No suspension", "No hand brake", "Only Baby Trend car seats fit"],
     "ideal_for": "Casual runners and walkers on a budget.",
     "not_for": "Steep trails or serious distance running.",
     "verdict": "The best budget jogger by a wide margin.",
     "review_summary": "4.7★ from 5,892 ratings (93% four or five stars). Owners praise the value, easy fold and handling on gravel; some reviews predate the current version.",
     "reviews": [R("Jay Cee", 5, "2026-07-22", "Handled the gravel trail at Horseshoe Bend on a road trip better than expected."),
                 R("Ethan Combs", 5, "2026-10-06", "Six-mile runs with no problems; his son gave up before the stroller did."),
                 R("Steven J.", 5, "2026-09-10", "Rolls like a more expensive stroller; comes with a jogging wrist strap.")]},
    badge="Best budget jogger")

DB = {"_meta": {"niche": "strollers", "marketplace": "amazon.com", "currency": "USD", "affiliate_tag": TAG,
                "updated": D, "notes": "Weight & fold score is formula-based (see /how-we-rate/); the rest are editorial. Null = not published/verified. "
                                       "Prices are stored only to assign a price band; the site never displays exact prices."},
      "products": P}
(ROOT / "data/products.json").write_text(json.dumps(DB, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(P), "products")
