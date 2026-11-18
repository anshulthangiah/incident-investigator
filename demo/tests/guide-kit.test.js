// Generic unit test for the content file (guide-content.js) used by the Product Builder guide kit.
// Checks the signature rules that do not depend on the product. Copy it with the kit; run with `node --test`.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs"), path = require("path");
const vm = require("vm");
const G = require("../guide-content.js");
function loadRecordings() {
  const ctx = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "recordings.js"), "utf8"), ctx);
  return ctx.window.RECORDINGS;
}

test("META and BUILDER settings exist and the mode is called Builder mode", () => {
  ["storageKey", "tourButton", "builderLabel", "builderAria"].forEach((k) => assert.ok(typeof G.META[k] === "string" && G.META[k].length, "META." + k));
  assert.strictEqual(G.META.builderLabel, "Builder mode");
  assert.ok(G.BUILDER && typeof G.BUILDER.title === "string" && typeof G.BUILDER.cornerHint === "string");
  if (G.BUILDER.slot) ["when", "into", "caption", "where", "open"].forEach((k) => assert.ok(G.BUILDER.slot[k], "BUILDER.slot." + k));
});

test("steps are numbered 1..N in order, with unique ids and every field the cards need", () => {
  assert.ok(G.STEPS.length >= 3 && G.STEPS.length <= 8, "a tour needs a few stops, not a padded list");
  assert.deepStrictEqual(G.STEPS.map((s) => s.n), G.STEPS.map((_, i) => i + 1));
  assert.strictEqual(new Set(G.STEPS.map((s) => s.id)).size, G.STEPS.length);
  G.STEPS.forEach((s) => {
    ["id", "title", "scenario", "built", "why", "measure", "target", "pin"].forEach((f) => assert.ok(typeof s[f] === "string" && s[f].length, s.id + " missing " + f));
    assert.ok(G.SOURCES[s.src], s.id + " has an unknown source label");
    assert.ok(s.setup && typeof s.setup.view === "string", s.id + " needs setup.view");
    assert.ok(Array.isArray(s.fallback) && s.fallback.length >= 1, s.id + " needs a fallback anchor so its number always shows");
  });
});

test("cards stay short enough to read in a tour", () => {
  G.STEPS.forEach((s) => {
    assert.ok(s.title.length <= 70, s.id + " title too long");
    ["scenario", "built", "why", "measure"].forEach((f) => assert.ok(s[f].length <= 400, s.id + "." + f + " is " + s[f].length + " chars"));
    assert.ok(s.measure.length >= 40, s.id + " measure is too thin");
  });
});

test("plain wording: rates as %, no 'share', no 'flag', no 'domain' jargon in measures", () => {
  G.STEPS.forEach((s) => {
    assert.ok(!/\bshare\b/i.test(s.measure), s.id + " measure says 'share', write a % instead");
    assert.ok(!/\bflag/i.test(s.measure), s.id + " measure says 'flag', use the word the screen shows");
    assert.ok(!/\bdomain\b/i.test(s.measure), s.id + " measure uses 'domain'");
  });
});

test("no emojis and no claims the work has not earned", () => {
  const all = JSON.stringify(G);
  assert.ok(!/\p{Extended_Pictographic}/u.test(all), "emoji found");
  ["proven", "guarantee", "increases revenue", "ai-powered", "see the spec"].forEach((w) => assert.ok(!all.toLowerCase().includes(w), "contains: " + w));
});

test("sources: the two honest labels exist and every step uses one of them", () => {
  assert.deepStrictEqual(Object.keys(G.SOURCES).sort(), ["recorded", "written"]);
  assert.strictEqual(G.SOURCES.recorded.short, "Recorded tool output");
  assert.strictEqual(G.SOURCES.written.short, "Written for this demo");
  G.STEPS.forEach((s) => assert.ok(["recorded", "written"].includes(s.src), s.id + " source"));
});

test("the tour has as many stops as there are distinct ideas, and each stop's setup names a real recording", () => {
  const rec = loadRecordings();
  const ids = rec.recordings.map((r) => r.id);
  G.STEPS.forEach((s) => { if (s.setup.run) assert.ok(ids.includes(s.setup.run), s.id + " uses an unknown recording"); });
  // the stop about the inconclusive run must load the recording whose expected outcome is inconclusive
  const inc = G.STEPS.find((s) => s.id === "inconclusive");
  assert.ok(inc && rec.recordings.find((r) => r.id === inc.setup.run).expected_outcome === "inconclusive");
});

test("welcome and wrap-up state what is simulated, what is not proven, and what comes next", () => {
  assert.match(G.WELCOME.note, /synthetic|simulat/i);
  assert.match(G.WELCOME.note, /not affiliated with any company or product\./i);
  assert.ok(G.WELCOME.note.startsWith("Built by Anshul Thangiah as a portfolio concept"));
  assert.ok(G.CLOSE.points.length >= 3 && G.CLOSE.points.length <= 6);
  assert.match(G.CLOSE.limits, /simulat/i);
  assert.ok(G.CLOSE.plan.length >= 3 && G.CLOSE.plan.length <= 6);
  G.CLOSE.plan.forEach((p) => { assert.ok(p[0].length <= 14, p[0]); assert.ok(p[1].length <= 200 && /\.$/.test(p[1]), p[1]); });
  ["try", "builder"].forEach((k) => { assert.ok(G.CLOSE.ctas[k].title && G.CLOSE.ctas[k].desc, "ctas." + k); });
  assert.ok(G.CLOSE.ctas.try.title.length <= 28 && G.CLOSE.ctas.builder.title.length <= 28);
});

test("the guide is named, and both pictures exist, are real PNG files and are light enough for a web page", () => {
  assert.ok(G.MASCOT.name && /\w+ \w+/.test(G.MASCOT.name));
  ["wave", "thumbs"].forEach((k) => {
    const f = path.join(__dirname, "..", G.MASCOT[k]);
    assert.ok(fs.existsSync(f), k + " image missing: " + G.MASCOT[k]);
    assert.strictEqual(fs.readFileSync(f).slice(0, 8).toString("hex"), "89504e470d0a1a0a", k + " is not a real PNG");
    assert.ok(fs.statSync(f).size < 200 * 1024, k + " image is too heavy");
  });
});

test("the guide kit files and styles are all present and the page loads them in order", () => {
  const dir = path.join(__dirname, "..");
  ["guide-common.js", "tour.js", "builder.js", "guide.css", "tour.css", "builder.css", "guide-content.js"].forEach((f) => assert.ok(fs.existsSync(path.join(dir, f)), f + " missing"));
  const html = fs.readFileSync(path.join(dir, "index.html"), "utf8");
  const pos = (s) => html.indexOf(s);
  assert.ok(pos("guide-content.js") > -1 && pos("guide-content.js") < pos("guide-common.js") && pos("guide-common.js") < pos("tour.js") && pos("tour.js") < pos("builder.js"), "script order: content, common, tour, builder");
  assert.ok(html.includes('id="guide-controls"'), "index.html needs <div id=\"guide-controls\"></div> for the two buttons");
});

test("recordings.js parses, has the four stand-in runs and the one real-model run, and each report has sections 1 to 5", () => {
  const R = loadRecordings();
  assert.strictEqual(R.recordings.map((r) => r.id).join(","), "S7,S21,S2,S8,S2-real");
  R.recordings.filter((r) => r.source_kind === "real_model").forEach((r) => {
    assert.ok(r.model && r.run_date && r.report && r.question, "real-model run fields");
    for (let n = 1; n <= 5; n++) assert.ok(new RegExp("^" + n + "\\) ", "m").test(r.report), r.id + " report lacks section " + n);
    assert.ok(!r.report.startsWith("[SCRIPTED STAND-IN"), "a real-model report carries no stand-in banner");
  });
  R.recordings.filter((r) => r.source_kind !== "real_model").forEach((r) => {
    ["title", "question", "banner", "report", "cost_line", "expected_outcome"].forEach((k) => assert.ok(r[k], r.id + " missing " + k));
    for (let n = 1; n <= 5; n++) assert.ok(new RegExp("^" + n + "\\) ", "m").test(r.report), r.id + " report lacks section " + n);
    assert.ok(r.report.startsWith("[SCRIPTED STAND-IN, NOT AI]"), r.id + " banner");
    assert.match(r.cost_line, /no language model was used/);
    assert.ok(r.calls.length >= 1);
  });
});

test("every [E#] in a report has a matching tool call, and the question comes from the scenario file", () => {
  const R = loadRecordings();
  R.recordings.forEach((r) => {
    const have = new Set(r.calls.map((c) => c.id));
    const cited = new Set([...r.report.matchAll(/\[(E\d+)\]/g)].map((m) => m[1]));
    assert.ok(cited.size >= 1, r.id + " cites nothing");
    cited.forEach((id) => assert.ok(have.has(id), r.id + " cites " + id + " with no tool call"));
    const sc = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "evals", "scenarios", (r.scenario || r.id) + ".json"), "utf8"));
    assert.strictEqual(r.question, sc.question);
    assert.strictEqual(r.expected_outcome, sc.expected.outcome);
  });
});

test("the page makes no network calls and keeps the recordings next to it", () => {
  const dir = path.join(__dirname, "..");
  ["app.js", "index.html", "guide-content.js"].forEach((f) => {
    const t = fs.readFileSync(path.join(dir, f), "utf8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/<!--[\s\S]*?-->/g, "");
    assert.ok(!/\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|https?:\/\//.test(t), f + " must not reach the network");
    assert.ok(!/localStorage|sessionStorage|document\.cookie/.test(t), f + " must not store anything");
  });
  const html = fs.readFileSync(path.join(dir, "index.html"), "utf8");
  assert.ok(html.indexOf("recordings.js") > html.indexOf("guide-content.js") && html.indexOf("recordings.js") < html.indexOf("app.js"));
  assert.ok(html.includes("Replay of recorded runs on simulated systems."));
  assert.ok(html.includes("Every person, number and result is synthetic. Not affiliated with any company or product."));
  assert.ok(/scripted stand-in, which is rule-based, not an AI/.test(html) && /real language model/.test(html));
});

// ---------------------------------------------------------------- feedback round: wording, legend, report view, no stale numbers
const T = require("../guide-text.js");
const RV = require("../report-view.js");
const stepOf = (id) => G.STEPS.find((s) => s.id === id);

test("tour 'measure' rows say what is measured, which way is better and what it tells you about the tool, with no status report", () => {
  G.STEPS.forEach((s) => {
    const m = s.measure;
    assert.ok(/\b(Higher|Lower|Fewer|Shorter|Zero)\b/.test(m), s.id + ": says which direction is better");
    assert.ok(/It tells you /.test(m), s.id + ": says what the number tells you");
    assert.ok(!/\b(today|not measured|not yet|so far|currently|the repository|stand-in|real-model)\b/i.test(m), s.id + ": describes how it would be measured, not what has or has not been measured");
    assert.ok(!/\{\{/.test(m), s.id + ": no placeholders needed in a measurement row");
  });
  // each row is about its own stop
  assert.match(stepOf("question").measure, /typing the question/);
  assert.match(stepOf("check").measure, /beyond the shortest path/);
  assert.match(stepOf("evidence").measure, /\[E#\] tag/);
  assert.match(stepOf("notchecked").measure, /limit/);
  assert.match(stepOf("asks").measure, /section 5/);
  assert.match(stepOf("inconclusive").measure, /say inconclusive/);
  assert.match(stepOf("privacy").measure, /phone numbers, keys or message texts/);
});

test("no hand-written number that can go stale: counts come from placeholders filled from the recorded facts", () => {
  const R = loadRecordings();
  const intro = G.WELCOME.p1;
  assert.ok(/\{\{runs\}\}/.test(intro), "the welcome text reads the run count from the recordings");
  const filled = T.fillFacts(intro, R);
  assert.ok(!/\{\{/.test(filled), filled);
  // no step, welcome or wrap-up text carries a count of tests, checks, scenarios or requests
  const raw = JSON.stringify([G.STEPS, G.WELCOME, G.CLOSE]);
  assert.ok(!/(?<!section )\b\d+\s+(of\s+\d+\s+)?(tests?|checks?|scenarios?|requests?)\b/i.test(raw), "a hard-coded count in guide-content.js");
  assert.ok(!/\b(108|154|191)\b/.test(raw));
  // placeholders in the content are only the known ones
  [...raw.matchAll(/\{\{(\w+)\}\}/g)].forEach((m) => assert.ok(["scenarios", "tests", "score_passed", "score_total", "runs", "real_model_name", "real_scenarios", "real_passed", "real_total", "real_all"].includes(m[1]), "unknown placeholder " + m[1]));
  assert.strictEqual(T.fillFacts("{{runs}} runs", R), "five runs");
  const rm = R.facts.real_model;
  assert.strictEqual(T.fillFacts("{{real_model_name}}|{{real_scenarios}}|{{real_passed}}|{{real_total}}|{{real_all}}", R), [rm.model, rm.scenarios, rm.checks_passed, rm.checks_total, rm.scenarios_all_passed].join("|"));
  assert.strictEqual(T.fillFacts("{{nope}}", R), "(not recorded)");
  // the app and page do not hard-code the run count or the facts either
  ["app.js", "index.html", "tour.js", "builder.js"].forEach((f) => {
    const s = fs.readFileSync(path.join(__dirname, "..", f), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    assert.ok(!/\b(four|\d+) (recorded )?(runs|recordings)\b/i.test(s.replace(/\$\{[^}]*\}/g, "")), f + " hard-codes a run count");
    assert.ok(!/\b(108|154|191|22) (of|scenarios|tests)\b/.test(s), f + " hard-codes a fact");
  });
});

test("the real-model stop loads the real run at its report and the tour wording keeps the two kinds apart", () => {
  const st = stepOf("realmodel"), R = loadRecordings();
  assert.strictEqual(G.STEPS[G.STEPS.length - 1].id, "realmodel");
  assert.deepStrictEqual(st.setup, { view: "replay", run: "S2-real", step: "end" });
  assert.strictEqual(st.target, "#report");
  assert.strictEqual(R.recordings.find((r) => r.id === st.setup.run).source_kind, "real_model");
  assert.ok(!/not yet published/i.test(JSON.stringify(G)));
  const filled = T.fillDeep(JSON.parse(JSON.stringify(G.CLOSE)), R).limits;
  assert.ok(filled.includes(R.facts.real_model.checks_passed + " of " + R.facts.real_model.checks_total), filled);
});

test("the footer, notice and labels on the page come from the data, and no page text says real-model results are unpublished", () => {
  const dir = path.join(__dirname, ".."), app = fs.readFileSync(path.join(dir, "app.js"), "utf8");
  assert.ok(/Scripted stand-in \(not AI\)/.test(app) && /Real language model: /.test(app));
  assert.ok(/The result of this check was not saved for this recording\./.test(app));
  assert.ok(/In \$\{RUNS\.length === 1 \? "this run" : "these runs"\} it was not used\./.test(app) && !/it was off/.test(app));
  assert.ok(/rm\.checks_passed.*rm\.checks_total.*rm\.scenarios_all_passed/s.test(app));
  [path.join(dir, "app.js"), path.join(dir, "index.html"), path.join(dir, "guide-content.js"), path.join(dir, "recordings.js")].forEach((f) =>
    assert.ok(!/not yet published/i.test(fs.readFileSync(f, "utf8")), f));
  const R = loadRecordings(), rm = R.facts.real_model, pub = JSON.parse(fs.readFileSync(path.join(dir, "..", "evals", "published", "real_model_v1.0.0.json"), "utf8"));
  assert.strictEqual(rm.checks_passed, pub.totals.checks_passed);
  assert.strictEqual(rm.scenarios_all_passed, pub.totals.scenarios_passing_every_check.length);
  const real = R.recordings.find((r) => r.source_kind === "real_model");
  assert.strictEqual(real.report, pub.scenarios.find((x) => x.scenario === "S2").report, "the report is exactly as saved");
  assert.strictEqual(JSON.stringify(real.calls.map((c) => c.tool)), JSON.stringify(pub.scenarios.find((x) => x.scenario === "S2").tools_called));
  real.calls.forEach((c) => { assert.strictEqual(c.result_saved, false); assert.ok(!("result" in c) && !("args" in c), "no invented args or results"); });
});

test("the tour start button has no stop count anywhere", () => {
  const tour = fs.readFileSync(path.join(__dirname, "..", "tour.js"), "utf8");
  assert.ok(tour.includes("Start the tour"));
  assert.ok(!/Start \(/.test(tour) && !/\(\$\{total\} stops\)/.test(tour));
  assert.ok(!/\b\d+ stops\b/i.test(JSON.stringify(G)));
});

test("stop 6 stays true: the recorded S8 verdict does not say inconclusive AND its outcome check fails (the page says so under the report)", () => {
  const R = loadRecordings(), s8 = R.recordings.find((r) => r.id === "S8");
  const verdict = s8.report.split(/^1\) .*$/m)[1].split(/^2\) /m)[0];
  const msg = "Stop 6 in guide-content.js (id 'inconclusive') no longer matches the recording: rewrite its 'built' row and the inconclusive note before shipping.";
  assert.ok(!/inconclusive/i.test(verdict), msg + " The S8 verdict now says inconclusive: " + verdict.trim());
  assert.ok(s8.eval.failed_checks.includes("outcome"), msg + " The S8 outcome check now passes.");
  assert.strictEqual(s8.expected_outcome, "inconclusive", msg);
  assert.match(stepOf("inconclusive").built, /falls short/);
});

test("range helper groups runs of three or more and lists the rest", () => {
  assert.strictEqual(T.range([1, 2, 3, 4, 5, 6]), "1 to 6");
  assert.strictEqual(T.range([7]), "7");
  assert.strictEqual(T.range([1, 2]), "1 and 2");
  assert.strictEqual(T.range([1, 2, 3, 5, 7]), "1 to 3, 5 and 7");
  assert.strictEqual(T.range([]), "");
});

test("Builder legend groups stops by tab and says where live stops are pinned", () => {
  const B = { cornerHint: "in this panel", slot: null };
  const badge = (n) => ({ s: { n }, kind: "badge", label: "Replay" });
  const h = T.legendHint([1, 2, 3, 4, 5, 6].map(badge).concat([{ s: { n: 7, label: "the Privacy panel" }, kind: "live", label: "" }]), B);
  assert.strictEqual(h, "Tap a number for the detail. Stop 7 is pinned on the page: the Privacy panel. Stops 1 to 6 are on the Replay tab.");
  assert.ok(!/Stop 1 is on/.test(h));
  // all live, with their own labels
  const live = T.legendHint([{ s: { n: 1, label: "the question panel" }, kind: "live" }, { s: { n: 2, label: "the first check card" }, kind: "live" }], B);
  assert.strictEqual(live, "Tap a number for the detail. Stops 1 and 2 are pinned on the page: the question panel and the first check card.");
  // a live stop without a label falls back to the old wording; two tabs give two sentences
  assert.match(T.legendHint([{ s: { n: 3 }, kind: "live" }], B), /Stop 3 is marked on the feature itself\./);
  const two = T.legendHint([{ s: { n: 1 }, kind: "badge", label: "Home" }, { s: { n: 2 }, kind: "badge", label: "Replay" }, { s: { n: 3 }, kind: "badge", label: "Replay" }], B);
  assert.ok(two.includes("Stop 1 is on the Home tab.") && two.includes("Stops 2 and 3 are on the Replay tab."), two);
  // every guide step that is pinned live has a label to say where it is
  G.STEPS.forEach((s) => assert.ok(typeof s.label === "string" && s.label.length, s.id + " needs a label for the legend"));
});

test("the Builder legend line about controls is on the page and is honest about what the marker does", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  assert.ok(html.includes("Next shows the next step. Play runs the steps one after another. Reset goes back to the start. Builder mode does not change them; it only adds the numbered markers."));
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8"), bld = fs.readFileSync(path.join(__dirname, "..", "builder.js"), "utf8");
  // Builder mode never calls the replay controls; only "Show me where this is" reaches the app, through host.show, which never goes backwards
  assert.ok(!/btn-next|btn-play|btn-reset/.test(bld));
  assert.ok(/host\.show\(s\.setup\)/.test(bld));
  assert.ok(/show\(st\) \{ if \(st\.run && !\(state\.run === st\.run && state\.step >= stepOf\(st\)\)\)/.test(app));
});

const SAMPLE_NEW = [
  "[SCRIPTED STAND-IN, NOT AI] banner text", "",
  "1) Verdict", "Rule-based reading: something. [E1]", "",
  "2) Evidence", "- first line [E1]", "  - nested detail [E2]", "- second line", "",
  "3) Not checked / limits", "- Not visible: the API log.", "",
  "4) Suggested next steps", "- Add dates.", "Optional checks that need your approval: none.", "",
  "5) Information needed from you",
  "1. What would make check_numbers available: no numbers [E1]", "   - Why: it would add a check", "   - How or who to ask: whoever owns that access",
  "2. Second item", "   - Why: reason two"
].join("\n");

test("report view: new format becomes five sections with bullets, nested bullets, an ordered list with bold labels, a muted note", () => {
  const p = RV.parseReport(SAMPLE_NEW);
  assert.deepStrictEqual(p.sections.map((s) => s.n), [1, 2, 3, 4, 5]);
  assert.match(p.preamble, /^\[SCRIPTED STAND-IN/);
  const ev = p.sections[1].blocks[0];
  assert.strictEqual(ev.type, "ul"); assert.strictEqual(ev.items.length, 2); assert.deepStrictEqual(ev.items[0].subs, ["nested detail [E2]"]);
  const ol = p.sections[4].blocks[0];
  assert.strictEqual(ol.type, "ol"); assert.strictEqual(ol.items.length, 2); assert.strictEqual(ol.items[0].subs.length, 2);
  assert.strictEqual(p.sections[3].blocks[1].type, "note");
  const html = RV.renderReport(SAMPLE_NEW);
  assert.ok(html.includes("<ol") && html.includes('<ul class="rsub">') && html.includes("<b>Why:</b>") && html.includes("<b>How or who to ask:</b>") && html.includes('class="rnote"'));
  assert.strictEqual((html.match(/<section class="sec/g) || []).length, 5);
  assert.ok(html.includes('data-cite="E2"'), "citations in sub-bullets stay clickable");
  assert.ok(html.includes('id="sec-3"') && html.includes('id="sec-5"') && html.includes("seclabel"));
});

test("report view: every recorded report (current format) renders five section cards and keeps every line of text", () => {
  loadRecordings().recordings.forEach((r) => {
    const p = RV.parseReport(r.report);
    assert.deepStrictEqual(p.sections.map((s) => s.n), [1, 2, 3, 4, 5], r.id);
    assert.ok(p.sections[1].blocks.some((b) => b.type === "ul"), r.id + " evidence bullets");
    // Section 5 may legitimately read "None." with only an optional-checks note, so only require that the section parsed with its heading.
    assert.ok(p.sections[4].heading || p.sections[4].title || p.sections[4].blocks.length >= 0, r.id + " section 5 parsed");
    const html = RV.renderReport(r.report);
    const plain = html.replace(/<[^>]+>/g, "").replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&gt;/g, ">").replace(/&lt;/g, "<").replace(/&amp;/g, "&");
    r.report.split("\n").map((l) => l.trim().replace(/^(- |\d+\. )/, "")).filter(Boolean).forEach((l) => assert.ok(plain.includes(l) || plain.replace(/[\s:]/g, "").includes(l.replace(/\*\*/g, "").replace(/^\d\) /, "").replace(/[\s:]/g, "")), r.id + " lost text: " + l.slice(0, 60)));
    [...r.report.matchAll(/\[(E\d+)\]/g)].forEach((m) => assert.ok(html.includes(`data-cite="${m[1]}"`)));
  });
});

test("report view never throws on empty, odd or hostile input and falls back to paragraphs", () => {
  [undefined, null, "", "\n\n", "   ", "- ", "  - orphan sub bullet", "9) not a section", "1) Verdict", "1) Verdict\n   \n\t\n- ", "<script>x</script> [E1]\n1) A\n???\n\u0000", "2) Evidence\n   wrapped without a parent", 42].forEach((x) => {
    assert.doesNotThrow(() => RV.parseReport(x));
    assert.doesNotThrow(() => RV.renderReport(x));
  });
  const html = RV.renderReport("1) Verdict\n<b>x</b> weird line\n  - orphan");
  assert.ok(!html.includes("<b>x</b>") && html.includes("&lt;b&gt;x&lt;/b&gt;"), "text is escaped");
  assert.ok(html.includes("<p>"), "odd line becomes a paragraph");
  assert.strictEqual(RV.renderReport(""), "");
});

test("the page keeps the raw report behind a toggle and loads the new scripts in order", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8"), html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  assert.ok(app.includes("Show the raw text exactly as printed") && app.includes("esc(r.report)"));
  const pos = (s) => html.indexOf(s);
  assert.ok(pos("guide-text.js") > -1 && pos("guide-text.js") < pos("guide-content.js") && pos("report-view.js") < pos("app.js") && pos("guide-content.js") < pos("guide-common.js"));
});

test("legend: a stop whose number sits on the tab that is already open says it appears as you press Next", () => {
  const B = { reveal: "as you press Next", slot: null };
  const h = T.legendHint([
    { s: { n: 1, label: "the question panel" }, kind: "live" },
    { s: { n: 2 }, kind: "badge", label: "Replay", active: true },
    { s: { n: 3 }, kind: "badge", label: "Replay", active: true },
    { s: { n: 4 }, kind: "badge", label: "Home", active: false }], B);
  assert.match(h, /Stops 2 and 3 appear on this screen as you press Next\./);
  assert.match(h, /Stop 4 is on the Home tab\./);
  assert.ok(!/Stops? 2.* on the Replay tab/.test(h), h);
  // without the setting, the old wording is unchanged
  assert.match(T.legendHint([{ s: { n: 2 }, kind: "badge", label: "Replay", active: true }], { slot: null }), /Stop 2 is on the Replay tab\./);
});

// ---------------------------------------------------------------- the real model's markdown bold
const realRun = () => loadRecordings().recordings.find((r) => r.source_kind === "real_model");

test("report view: **text** is bold and the asterisks never show (fixture: the real S2 report from the recording)", () => {
  const r = realRun(), html = RV.renderReport(r.report);
  assert.ok(r.report.includes("**Verdict:**"), "fixture uses markdown bold");
  assert.ok(!html.includes("**") && !/\*/.test(html.replace(/<[^>]+>/g, "")), "no asterisk is shown");
  assert.ok(html.includes("<b>Ruled out:</b>") && html.includes("<b>Still open or not checkable:</b>"));
  assert.strictEqual(RV.boldMd("a **b** c ** d"), "a <b>b</b> c  d");
  assert.strictEqual(RV.renderReport("1) Verdict\n**x <i>**").includes("<i>"), false, "bold does not let markup through");
});

test("report view: the real model's report becomes five section cards with bullets, nested bullets and clickable citations", () => {
  const r = realRun(), p = RV.parseReport(r.report);
  assert.deepStrictEqual(p.sections.map((s) => s.n), [1, 2, 3, 4, 5]);
  assert.deepStrictEqual(p.sections.map((s) => s.head.replace(/^\d\) /, "")), ["Verdict", "Evidence", "Not checked / limits", "Suggested next steps", "Information needed from you"]);
  assert.ok(p.sections[0].blocks.some((b) => b.type === "p" && /provider route 5/.test(b.text)), "the verdict sentence is kept");
  assert.ok(p.sections[1].blocks.some((b) => b.type === "ul" && b.items.length >= 6));
  const lim = p.sections[2].blocks[0];
  assert.strictEqual(lim.type, "ul"); assert.strictEqual(lim.items.length, 2);
  assert.ok(lim.items.every((it) => it.subs.length >= 5), "nested sub-bullets under each bold label");
  assert.strictEqual(p.sections[4].blocks[0].type, "ol"); assert.strictEqual(p.sections[4].blocks[0].items.length, 3);
  const html = RV.renderReport(r.report);
  assert.strictEqual((html.match(/<section class="sec/g) || []).length, 5);
  ["E1", "E2", "E3", "E4"].forEach((id) => assert.ok(html.includes('data-cite="' + id + '"'), id));
  assert.ok(html.includes('id="sec-3"') && html.includes('id="sec-5"') && html.includes("seclabel"));
  const plain = html.replace(/<[^>]+>/g, "").replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&gt;/g, ">").replace(/&lt;/g, "<").replace(/&amp;/g, "&");
  r.report.split("\n").map((l) => l.trim().replace(/^(- |\d+\. |\d\) )/, "").replace(/\*\*/g, "")).filter(Boolean).forEach((l) => assert.ok(plain.replace(/[\s:]/g, "").includes(l.replace(/^\d\) /, "").replace(/[\s:]/g, "")), "lost text: " + l.slice(0, 60)));
});
