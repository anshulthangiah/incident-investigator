/*
 * Small pure text helpers for the guide kit. No DOM, so Node can unit test them (demo/tests/guide-kit.test.js).
 *   range(ns)                    [1,2,3,5] -> "1 to 3 and 5"
 *   legendHint(items, B)         the sentence list under the Builder legend: where each number is on THIS screen
 *   fillFacts(text, data)        replaces {{scenarios}}, {{tests}}, {{score_passed}}, {{score_total}}, {{runs}} and {{real_model_name}}, {{real_scenarios}}, {{real_passed}}, {{real_total}}, {{real_all}} from window.RECORDINGS
 *   fillDeep(obj, data)          the same, over every string inside an object (used on the guide content)
 */
(function (root) {
  function list(a) { return a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]; }

  // Runs of three or more become "a to b". Two in a row stay separate ("1, 2"), so "1 to 2" never appears.
  function range(ns) {
    ns = ns.slice().sort((a, b) => a - b);
    const out = []; let i = 0;
    while (i < ns.length) {
      let j = i; while (j + 1 < ns.length && ns[j + 1] === ns[j] + 1) j++;
      if (j - i >= 2) out.push(ns[i] + " to " + ns[j]); else for (let k = i; k <= j; k++) out.push(String(ns[k]));
      i = j + 1;
    }
    return list(out);
  }

  // items: [{ s: { n, label? }, kind: "live" | "slot" | "corner" | "badge", label }]; B: the BUILDER settings ({ cornerHint, slot }).
  function legendHint(items, B) {
    const SLOT = B.slot, by = (k) => items.filter((it) => it.kind === k), one = (a) => a.length === 1;
    const nums = (a) => range(a.map((i) => i.s.n));
    const parts = ["Tap a number for the detail."];
    const live = by("live"), slot = by("slot"), corner = by("corner"), badgeAll = by("badge");
    // a stop whose number sits on the tab that is already open has no card on screen yet: it appears as the replay moves on
    const here = B.reveal ? badgeAll.filter((it) => it.active) : [], badge = badgeAll.filter((it) => !here.includes(it));
    if (here.length) parts.push(`Stop${one(here) ? "" : "s"} ${nums(here)} ${one(here) ? "appears" : "appear"} on this screen ${B.reveal}.`);
    if (live.length) {
      const places = live.slice().sort((p, q) => p.s.n - q.s.n).map((i) => i.s.label).filter(Boolean);
      parts.push(places.length === live.length
        ? `Stop${one(live) ? "" : "s"} ${nums(live)} ${one(live) ? "is" : "are"} pinned on the page: ${list(places)}.`
        : `Stop${one(live) ? "" : "s"} ${nums(live)} ${one(live) ? "is" : "are"} marked on the feature itself.`);
    }
    if (corner.length) parts.push(`Stop${one(corner) ? "" : "s"} ${nums(corner)} ${one(corner) ? "appears" : "appear"} ${B.cornerHint}.`);
    if (slot.length && SLOT) parts.push(`Stop${one(slot) ? "" : "s"} ${nums(slot)} ${one(slot) ? "is" : "are"} on ${SLOT.where}, so open ${SLOT.open} to see ${one(slot) ? "it" : "them"}.`);
    const tabs = new Map();   // one sentence per tab label, not one per stop
    badge.forEach((it) => { const k = it.label || "same"; if (!tabs.has(k)) tabs.set(k, []); tabs.get(k).push(it); });
    tabs.forEach((g, k) => parts.push(`Stop${one(g) ? "" : "s"} ${nums(g)} ${one(g) ? "is" : "are"} on ${k === "same" ? "a tab" : "the " + k + " tab"}.`));
    return parts.join(" ");
  }

  const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  function fillFacts(text, data) {
    const f = (data && data.facts) || {}, rm = f.real_model || {}, recs = (data && data.recordings) || [];
    const vals = { scenarios: f.scenarios, tests: f.tests, score_passed: f.stand_in_checks_passed, score_total: f.stand_in_checks_total,
      real_model_name: rm.model, real_scenarios: rm.scenarios, real_passed: rm.checks_passed, real_total: rm.checks_total, real_all: rm.scenarios_all_passed,
      runs: recs.length ? (WORDS[recs.length] || String(recs.length)) : undefined };
    return String(text).replace(/\{\{(\w+)\}\}/g, (m, k) => (vals[k] === undefined ? "(not recorded)" : String(vals[k])));
  }
  function fillDeep(o, data) {
    if (typeof o === "string") return fillFacts(o, data);
    if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) o[i] = fillDeep(o[i], data); return o; }
    if (o && typeof o === "object") { Object.keys(o).forEach((k) => { o[k] = fillDeep(o[k], data); }); return o; }
    return o;
  }

  const api = { range, legendHint, fillFacts, fillDeep };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.GuideText = api;
})(typeof self !== "undefined" ? self : this);
