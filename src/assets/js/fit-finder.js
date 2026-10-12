/* BabyScope — stroller fit finder. Runs entirely in the browser.
   Needs window.__DB__ (db.js) and window.__FF__ (config inlined by build.py). */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function init() {
    var root = document.querySelector("[data-ff]");
    var DB = window.__DB__, CFG = window.__FF__;
    if (!root || !DB || !CFG) return;
    var form = root.querySelector("[data-ff-form]");
    var lift = root.querySelector("[data-ff-lift]"), liftOut = root.querySelector("[data-ff-lift-out]");
    var list = root.querySelector("[data-ff-list]"), summary = root.querySelector("[data-ff-summary]");
    var viz = root.querySelector("[data-ff-viz]");
    var focus = (new URLSearchParams(location.search).get("ids") || "").split(",").filter(Boolean);

    function val(name) { var el = form.querySelector('input[name="' + name + '"]:checked'); return el ? el.value : ""; }
    function has(p, t) { return p.tags.indexOf(t) > -1; }

    function evaluate(p, a) {
      var s = p.specs, checks = [];
      function add(st, t) { checks.push({ st: st, t: t }); }
      // 1. how it will be used
      if (a.use === "jog") {
        if (s.jogging) add("ok", "Rated for jogging" + (s.handbrake ? ", with a hand brake" : ""));
        else add("no", "Not rated for running");
      } else if (a.use === "travel") {
        if (s.carry_on) add("ok", "Brand says it fits most overhead bins");
        else if (s.weight_lb != null && s.weight_lb <= 18) add("warn", "Light, but too big for the overhead bin — plan to gate-check");
        else add("no", "Too big and heavy for easy air travel");
      } else if (a.use === "trails") {
        if (has(p, "all-terrain")) add("ok", "All-terrain wheels: " + s.wheels);
        else if (s.suspension && !/^none/i.test(s.suspension)) add("warn", "Suspension helps, but the wheels are small for gravel and grass");
        else add("no", "Small wheels struggle on gravel and grass");
      } else if (s.jogging && s.weight_lb != null && s.weight_lb >= 28) {
        add("warn", "Big jogging frame — more than you need for errands and stores");
      }
      // 2. number of kids
      if (a.kids === "two") {
        if ((s.seats || 1) >= 2) add("ok", "Carries two children");
        else if (has(p, "convertible")) add("warn", "Carries two with a second seat (sold separately)");
        else add("no", "Single stroller only");
      } else if (a.kids === "grow") {
        if (has(p, "convertible") || (s.seats || 1) >= 2) add("ok", "Converts to a double later");
        else add("warn", "Single only — you'd need a second stroller or a ride-on board");
      }
      // 3. baby's age
      if (a.age === "newborn" || a.age === "infant") {
        if (s.newborn === "flat") add("ok", "Newborn-ready: " + s.from_birth.replace(/^Yes — /, ""));
        else if (s.newborn === "carseat") {
          if (s.cs_included) add("ok", "Use the included infant car seat on the frame");
          else if (a.seat === "have") add("warn", "Works from birth only with a compatible car seat: " + (s.car_seat_fit || "check the brand"));
          else add("warn", "Needs a compatible infant car seat (sold separately) until about 6 months");
        } else add("no", "Not for babies who can't sit up yet");
        if (a.use === "jog") add("warn", "Wait until about 6–8 months before running with your baby");
      }
      // 4. car seat
      if (a.seat === "need") {
        if (s.cs_included) add("ok", s.car_seat);
        else add("no", "Car seat not included");
      } else if (a.seat === "have") {
        if (s.cs_included) add("warn", "Comes with its own car seat — you'd be paying for a second one");
        else if (s.car_seat_fit) add("ok", "Car seats: " + s.car_seat_fit);
        else add("no", "No infant car seat attaches to this stroller");
      }
      // 5. lifting weight
      var w = s.weight_lb;
      if (w == null) add("warn", "Stroller weight not clearly published");
      else if (w <= a.lift) add("ok", w + " lb — within what you want to lift");
      else if (w <= a.lift + 3) add("warn", w + " lb — a little over your " + a.lift + " lb limit");
      else add("no", w + " lb is heavier than you want to lift");
      // 6. tall parent
      if (a.tall === "yes") {
        if (s.adjustable_handle) add("ok", "Adjustable handlebar for tall parents");
        else add("warn", "Handlebar height isn't adjustable — try it if you're over 6 ft");
      }
      // 7. budget (price band only)
      if (a.budget < 99 && p.tier != null && p.tier > a.budget) add("no", "Above your budget (" + p.band + ")");
      var st = checks.some(function (c) { return c.st === "no"; }) ? "no" : checks.some(function (c) { return c.st === "warn"; }) ? "warn" : "ok";
      return { p: p, st: st, checks: checks };
    }

    function drawViz(a, results) {
      var rs = results.filter(function (x) { return x.p.specs.weight_lb != null; })
        .sort(function (x, y) { return x.p.specs.weight_lb - y.p.specs.weight_lb; });
      if (!rs.length) { viz.hidden = true; return; }
      viz.hidden = false;
      var maxLb = Math.max(a.lift, rs[rs.length - 1].p.specs.weight_lb) * 1.1;
      var W = 640, H = 190, base = 160, px = (base - 22) / maxLb, bw = Math.min(30, (W - 40) / rs.length - 6);
      var y = function (lb) { return base - lb * px; };
      var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Stroller weights compared with the most you want to lift">';
      svg += '<line x1="0" x2="' + W + '" y1="' + y(a.lift) + '" y2="' + y(a.lift) + '" class="ff-line"/>';
      svg += '<text x="8" y="' + (y(a.lift) - 7) + '" class="ff-sofa-t">Most you want to lift · ' + a.lift + ' lb</text>';
      svg += '<line x1="0" x2="' + W + '" y1="' + base + '" y2="' + base + '" class="ff-floor"/>';
      rs.forEach(function (x, i) {
        var lb = x.p.specs.weight_lb, X = 24 + i * (bw + 6);
        var cls = lb <= a.lift ? "ok" : lb <= a.lift + 3 ? "warn" : "no";
        svg += '<g class="ff-bar ff-bar--' + cls + '"><title>' + esc(x.p.name) + " — " + lb + ' lb</title><rect x="' + X + '" y="' + y(lb) + '" width="' + bw + '" height="' + (lb * px) + '" rx="4"/>' +
          '<text x="' + (X + bw / 2) + '" y="' + (base + 16) + '" text-anchor="middle">' + Math.round(lb) + "</text></g>";
      });
      svg += "</svg>";
      viz.innerHTML = svg + '<p class="ff-viz__cap">Each bar is one stroller\'s weight in pounds, without a car seat. Green is within your limit, amber is just over, red is too heavy.</p>';
    }

    function render() {
      var a = {
        use: val("use") || "city", kids: val("kids") || "one", age: val("age") || "newborn", seat: val("seat") || "no",
        lift: parseFloat(lift.value), tall: val("tall") || "no", budget: parseInt(val("budget") || "99", 10)
      };
      liftOut.textContent = a.lift + " lb";
      var results = DB.products.map(function (p) { return evaluate(p, a); });
      var rank = { ok: 0, warn: 1, no: 2 };
      results.sort(function (x, y) {
        var fx = focus.indexOf(x.p.id) > -1 ? 0 : 1, fy = focus.indexOf(y.p.id) > -1 ? 0 : 1;
        return fx - fy || rank[x.st] - rank[y.st] || y.p.score - x.p.score;
      });
      var nOk = results.filter(function (x) { return x.st === "ok"; }).length;
      var nWarn = results.filter(function (x) { return x.st === "warn"; }).length;
      summary.innerHTML = "<b>" + nOk + "</b> great fit" + (nOk === 1 ? "" : "s") + " · <b>" + nWarn + "</b> with caveats · <b>" + (results.length - nOk - nWarn) + "</b> not a fit";
      var labels = { ok: "Great fit", warn: "Fits, with caveats", no: "Not a fit" };
      list.innerHTML = results.map(function (x) {
        var p = x.p;
        return '<article class="ff-card ff-card--' + x.st + (focus.indexOf(p.id) > -1 ? " is-focus" : "") + '">' +
          '<a class="ff-card__img" href="' + esc(p.url) + '"><img src="' + esc(p.img) + '" alt="" loading="lazy"></a>' +
          '<div class="ff-card__body"><div class="ff-card__top"><span class="ff-status">' + labels[x.st] + '</span><span class="score-pill" title="Editor score">' + p.score + "</span></div>" +
          '<h3><a href="' + esc(p.url) + '">' + esc(p.name) + "</a></h3>" +
          '<ul class="ff-checks">' + x.checks.map(function (c) { return '<li class="is-' + c.st + '">' + esc(c.t) + "</li>"; }).join("") + "</ul>" +
          '<div class="ff-card__actions">' + (p.band ? '<span class="ff-price">' + esc(p.band) + "</span>" : "") +
          '<a class="btn btn--amazon btn--xs" href="' + esc(p.aff) + '" target="_blank" rel="sponsored nofollow noopener">Check price on Amazon<svg class="ico"><use href="#i-ext"/></svg></a>' +
          '<a class="btn btn--ghost btn--xs" href="' + esc(p.url) + '">Review</a></div></div></article>';
      }).join("") + '<p class="note note--muted">Price ranges are approximate; check Amazon for today\'s price. Specs are brand claims — see each review for sources. Always follow your stroller and car seat manuals.</p>';
      drawViz(a, results);
    }

    form.addEventListener("input", render);
    form.addEventListener("change", render);
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
