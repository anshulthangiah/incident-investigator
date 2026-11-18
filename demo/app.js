/*
 * Replay demo. It plays back recordings that scripts/record_demo.py captured from the real command-line tool
 * (scripted stand-in, mock system) plus one run saved from a real model (read from evals/published/). The page adds no results of its own: every number and sentence of a run comes from
 * window.RECORDINGS. The only text written by hand here is the layout wording and the one-line "what this check answers"
 * per tool (written once, below, from docs/BUILD_NOTES.md).
 * No network calls. The only thing stored in the browser is the tour's "seen" flag (in tour.js).
 * The only thing the guide kit needs from this file is window.GuideHost at the bottom.
 */
(function () {
  const $ = (s) => document.querySelector(s);
  const DATA = window.RECORDINGS || { recordings: [], facts: {} };
  const RUNS = DATA.recordings;
  const FACTS = DATA.facts || {};
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // One plain-language line per tool, written once (source: the tools table in docs/BUILD_NOTES.md).
  const WHAT = {
    fetch_delivery_logs: "How many code requests were sent, how many failed and why, how many were repeats, and how long delivery took. Read from the provider's delivery log.",
    get_credit_balance: "Whether the sending account still has credit right now. It cannot show the balance at an earlier time.",
    check_user_data: "Whether newly created users were saved with an empty locale or dial code. It reads current data, never user rows.",
    check_message_queue: "How many messages are waiting in the queue and how long they have waited.",
    check_numbers: "How the specific phone numbers you gave were handled. The model sees aliases only.",
    check_code_api: "Sends one real test message through the verification API. Off by default and needs approval every run.",
    recent_code_changes: "Recent commit subjects and file names in the configured repositories. No code."
  };

  const isReal = (r) => !!r && r.source_kind === "real_model";
  const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  const word = (n) => WORDS[n] || String(n);
  const cap = (w) => w.charAt(0).toUpperCase() + w.slice(1);
  const nStand = RUNS.filter((r) => !isReal(r)).length, nReal = RUNS.filter(isReal).length;
  // the label shown on every run: which kind of author wrote it
  const kindLabel = (r) => (isReal(r) ? "Real language model: " + r.model : "Scripted stand-in (not AI)");
  const kindChip = (r) => `<span class="kind ${isReal(r) ? "kind-real" : "kind-standin"}">${esc(kindLabel(r))}</span>`;

  const state = { view: "home", run: null, step: 0, timer: null };
  const run = () => RUNS.find((r) => r.id === state.run) || null;
  const lastStep = (r) => r.calls.length + 1;   // 0 = the question, 1..n = the checks, n+1 = the report

  // ------------------------------------------------------------ small formatters (they only read fields of the recorded results)
  const num = (n) => Number(n).toLocaleString("en-US");
  function dates(args) {
    const a = args || {};
    const from = a.start_date || a.since_date, to = a.end_date || a.until_date;
    if (!from && !to) return "No dates (this check takes none)";
    return from === to ? from : from + " to " + to;
  }
  function perDayTable(res) {
    const req = res.requests_per_day, fr = res.failure_rate_pct_per_day;
    if (!req || !fr) return "";
    const days = Object.keys(req);
    return `<div class="tablewrap"><table><caption class="sr">Requests and failure rate per day</caption><thead><tr><th scope="col">Day</th>${days.map((d) => `<th scope="col">${esc(d.slice(5))}</th>`).join("")}</tr></thead>
      <tbody><tr><th scope="row">Requests</th>${days.map((d) => `<td>${num(req[d])}</td>`).join("")}</tr>
      <tr><th scope="row">Failed, %</th>${days.map((d) => `<td>${esc(fr[d])}</td>`).join("")}</tr></tbody></table></div>`;
  }
  function summary(c) {
    const r = c.result || {};
    if (c.tool === "fetch_delivery_logs" && r.total !== undefined) {
      const li = [];
      li.push(`<li><b>${num(r.total)}</b> requests over ${r.days.length} days: ${num(r.delivered)} delivered, <b>${num(r.failed)}</b> failed (<b>${esc(r.failure_rate_pct)}%</b>).</li>`);
      const top = (r.failure_reasons || [])[0];
      if (top) li.push(`<li>Most common failure reason: ${esc(top.reason)} (${num(top.count)} rows), category ${esc(top.category)}.</li>`);
      if (r.repeat_requests) li.push(`<li>Repeat requests within ${esc(r.repeat_requests.window_minutes)} minutes: ${num(r.repeat_requests.repeat_requests)} from ${num(r.repeat_requests.recipients_with_a_repeat)} recipients (${esc(r.repeat_requests.share_of_requests_pct)}% of requests).</li>`);
      if (r.delivery_delay_s) li.push(`<li>Delivery delay at the provider: median ${esc(r.delivery_delay_s.median)} s, p90 ${esc(r.delivery_delay_s.p90)} s, max ${esc(r.delivery_delay_s.max)} s.</li>`);
      if (r.days_without_data && r.days_without_data.length) li.push(`<li>Days with no data: ${esc(r.days_without_data.join(", "))}.</li>`);
      return `<ul>${li.join("")}</ul>${perDayTable(r)}`;
    }
    if (c.tool === "get_credit_balance" && r.balance !== undefined) {
      return `<ul><li>Balance now: <b>${esc(r.balance)}</b>, enough for about ${num(r.requests_remaining_at_current_rate)} more requests at the current rate.</li><li>${esc(r.note)}</li></ul>`;
    }
    if (r.error) return `<ul><li>Could not run: ${esc(r.error)}</li></ul>`;
    const items = Object.entries(r).filter(([, v]) => typeof v !== "object").map(([k, v]) => `<li>${esc(k)}: ${esc(v)}</li>`);
    return `<ul>${items.join("")}</ul>`;
  }

  // ------------------------------------------------------------ report: laid out as five section cards by report-view.js (same text, never edited)

  // tokens of the one real scenario, from the recording; the published file has no cost per scenario, so none is shown
  function usageLine(r) {
    const u = r.usage || {}, bits = [];
    if (u.input_tokens != null) bits.push(`${num(u.input_tokens)} input tokens`);
    if (u.output_tokens != null) bits.push(`${num(u.output_tokens)} output tokens`);
    if (u.model_calls != null) bits.push(`${u.model_calls} model calls`);
    if (u.cost_usd != null) bits.push(`about $${Number(u.cost_usd).toFixed(4)} (estimate)`);
    return "This round used a real language model (" + r.model + "): " + bits.join(", ") + (u.cost_usd == null ? ". The cost of this one scenario was not saved." : ".");
  }

  // ------------------------------------------------------------ views
  function setView(v) {
    state.view = v;
    document.querySelectorAll(".topnav button").forEach((b) => { const on = b.dataset.tab === v; b.classList.toggle("active", on); b.setAttribute("aria-current", on ? "page" : "false"); });
    ["home", "replay"].forEach((n) => ($("#view-" + n).hidden = n !== v));
    const cn = $("#builder-controls-note"); if (cn) cn.hidden = v !== "replay";   // the controls only exist on the Replay tab
  }

  function renderNotice() {
    const n = $(".notice"); if (!n || !RUNS.length) return;
    const stand = nStand ? `${cap(word(nStand))} run${nStand === 1 ? " comes" : "s come"} from the scripted stand-in, which is rule-based, not an AI.` : "";
    const real = nReal ? `${cap(word(nReal))} run${nReal === 1 ? " is" : "s are"} the output of a real language model on the same invented data.` : "";
    n.textContent = ["Replay of recorded runs on simulated systems.", stand, real, "Every person, number and result is synthetic. Not affiliated with any company or product."].filter(Boolean).join(" ");
  }
  function renderBuilderNote() {
    const n = $("#builder-recordings"); if (!n) return;
    n.textContent = nReal
      ? `The ${word(nStand)} scripted recordings on this page are real output of that tool, captured by scripts/record_demo.py. The ${word(nReal)} real-model recording was saved from a real model run by the evaluation runner (evals/run_evals.py) and is read from evals/published/; its tool results were not saved.`
      : "The recordings on this page are real output of that tool, captured by scripts/record_demo.py.";
  }

  function renderHome() {
    $("#picker").innerHTML = RUNS.map((r) => `<article class="run-card" id="pick-${esc(r.id)}">
      <h3><span class="rid">${esc(r.id)}</span> ${esc(r.title)}</h3>
      <p class="kindrow">${kindChip(r)}</p>
      <p class="qlabel">The question put to the tool</p>
      <blockquote>${esc(r.question)}</blockquote>
      <p class="hint">${r.calls.length} check${r.calls.length === 1 ? "" : "s"} recorded${isReal(r) ? " (tool names only)" : ""}. Expected outcome in the repo: <b>${esc(r.expected_outcome.replace("_", " "))}</b>.</p>
      <button type="button" class="primary" data-run="${esc(r.id)}" aria-label="Replay this run: ${esc(r.id)}">Replay this run</button>
    </article>`).join("");
  }

  function renderPrivacy() {
    $("#privacy").innerHTML = `<h2>Privacy</h2><ul>
      <li>The model only passes dates. It picks a tool name and dates; the tools build the web addresses, SQL and file paths from your settings.</li>
      <li>Phone numbers are shown to the model as aliases such as N1. No numbers were given in ${RUNS.length === 1 ? "this run" : "these " + RUNS.length + " runs"}.</li>
      <li>Only one check does more than read: <code>check_code_api</code> sends one real test message, through the verification API, to your own phone number. It is off by default and needs your approval every time. In ${RUNS.length === 1 ? "this run" : "these runs"} it was not used.</li></ul>
      <p class="hint">Source: docs/PRIVACY_AND_SAFETY.md.</p>`;
  }

  function renderFooter() {
    const bits = [];
    if (FACTS.scenarios) bits.push(`${FACTS.scenarios} scenarios`);
    if (FACTS.tests) bits.push(`${FACTS.tests} tests`);
    if (FACTS.stand_in_checks_total) bits.push(`the scripted stand-in passes ${FACTS.stand_in_checks_passed} of ${FACTS.stand_in_checks_total} checks (this measures the stand-in only)`);
    const rm = FACTS.real_model;
    const model = rm ? `A real model (${rm.model}) passed ${rm.checks_passed} of ${rm.checks_total} checks over ${rm.scenarios} scenarios in one run; ${rm.scenarios_all_passed} scenarios passed every check. See docs/EVALUATION_RESULTS.md.`
      : (FACTS.model_results ? FACTS.model_results + "." : "");
    $("#footer-line").textContent = "In the repository: " + bits.join(", ") + ". " + model;
  }

  function renderReplay() {
    const r = run(); if (!r) return;
    const s = state.step, last = lastStep(r);
    const head = `<div class="runhead"><h2><span class="rid">${esc(r.id)}</span> ${esc(r.title)}</h2>
      <p class="kindrow" id="run-kind">${kindChip(r)}</p>
      <div class="controls" role="group" aria-label="Replay controls">
        <button type="button" class="primary" id="btn-next" ${s >= last ? "disabled" : ""}>Next</button>
        <button type="button" class="ghost" id="btn-play" ${s >= last ? "disabled" : ""}>${state.timer ? "Pause" : "Play"}</button>
        <button type="button" class="ghost" id="btn-reset" ${s === 0 && !state.timer ? "disabled" : ""}>Reset</button>
        <button type="button" class="ghost" id="btn-pick">Choose another run</button>
      </div>
      <p class="hint" aria-live="polite">${s === 0 ? "Step 0 of " + last : s >= last ? "Run finished" : "Step " + s + " of " + last} (the question, then ${r.calls.length} check${r.calls.length === 1 ? "" : "s"}, then the report)</p></div>`;

    const real = isReal(r);
    const banner = real ? "" : `<p class="banner" id="stand-in-banner">${esc(r.banner)}</p>`;
    const q = `<section class="panel" id="q-block" aria-label="The question"><h3>The question</h3><blockquote>${esc(r.question)}</blockquote>
      ${real ? `<p class="hint">Saved by the evaluation runner on ${esc(r.run_date)} from <code>${esc(r.source)}</code>. The language model (${esc(r.model)}) chose these read-only checks itself. Only the tool names and the final report were saved.</p>`
        : `<p class="hint">Command recorded: <code>${esc(r.source)}</code>. The tool starts the mock system for this scenario, then the scripted stand-in picks checks by keyword rules.</p>`}
      ${r.tools_unavailable ? `<p class="hint">Tool output: ${esc(r.tools_unavailable)}</p>` : ""}</section>`;

    let cards = "";
    r.calls.forEach((c, i) => {
      if (s < i + 1) return;
      const answers = `<div><dt>What this check answers</dt><dd>${esc(WHAT[c.tool] || "")}</dd></div>`;
      cards += c.result_saved === false
        ? `<article class="panel call" id="call-${esc(c.id)}" tabindex="-1" aria-label="Check ${esc(c.id)}, ${esc(c.tool)}">
        <h3><span class="tag">${esc(c.id)}</span> <code>${esc(c.tool)}</code></h3>
        <dl class="kv">${answers}</dl>
        <p class="hint nosave">The result of this check was not saved for this recording.</p></article>`
        : `<article class="panel call" id="call-${esc(c.id)}" tabindex="-1" aria-label="Check ${esc(c.id)}, ${esc(c.tool)}">
        <h3><span class="tag">${esc(c.id)}</span> <code>${esc(c.tool)}</code></h3>
        <dl class="kv"><div><dt>Dates it was given</dt><dd>${esc(dates(c.args))}</dd></div>
        ${answers}</dl>
        <h4>Result</h4>${summary(c)}
        <details><summary>Show the full recorded result</summary><pre>${esc(JSON.stringify(c.result, null, 2))}</pre></details></article>`;
    });
    const checks = `<div id="checks" aria-label="The checks the tool ran">${cards}</div>`;

    let rep = "";
    if (s >= last) {
      const ev = r.eval || {};
      const label = !real && r.expected_outcome === "inconclusive"
        ? `<div class="inconclusive" id="inconclusive-label" role="note"><b>This run ends inconclusive on purpose</b>
            <p>The repo's expected outcome for ${esc(r.id)} is <code>inconclusive</code>: the cause is outside every source the tools can read. Read sections 3 and 5 below for what the tool says it could not see.</p>
            <p>What the scripted stand-in actually wrote: the repo's own scoring reads its verdict as <code>${esc(ev.outcome_from_report || "")}</code>, so the outcome check ${ev.failed_checks && ev.failed_checks.includes("outcome") ? "fails" : "passes"} on this recording. This is a limit of the stand-in, not of the idea.</p></div>` : "";
      const body = window.ReportView.renderReport(r.report);
      rep = `<section class="panel" id="report"><h3>The report</h3>${label}<p class=\"hint\">This is the recorded text laid out as cards. Nothing is added or changed; the raw text is below.</p>${body}
        <details class="rawtoggle" id="raw-report"><summary>Show the raw text exactly as printed</summary><pre class="rawtext">${esc(r.report)}</pre></details>
        <p class="cost" id="cost-line">${esc(real ? usageLine(r) : r.cost_line)}</p>
        <p class="hint">The repo's own scoring of this recording: ${ev.checks_passed} of ${ev.checks_total} text checks pass${ev.failed_checks && ev.failed_checks.length ? " (not passed: " + esc(ev.failed_checks.join(", ")) + ")" : ""}. The checks are text matches, not a judgement of quality.</p></section>`;
    }
    $("#replay").innerHTML = head + banner + q + checks + rep;
  }

  // ------------------------------------------------------------ actions
  function stopTimer() { if (state.timer) { clearInterval(state.timer); state.timer = null; } }
  function load(id, step) {
    stopTimer();
    state.run = id; state.step = Math.max(0, Math.min(step, lastStep(run())));
    renderReplay();
  }
  function advance() {
    const r = run(); if (!r) return;
    if (state.step < lastStep(r)) { state.step++; renderReplay(); }
    if (state.step >= lastStep(r)) stopTimer();
    if (!state.timer) renderReplay();
  }
  function highlight(id) {
    const el = document.getElementById("call-" + id); if (!el) return;
    document.querySelectorAll(".call.hl").forEach((x) => x.classList.remove("hl"));
    el.classList.add("hl");
    el.scrollIntoView({ block: "center", behavior: "auto" });
    el.focus({ preventScroll: true });
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("button"); if (!t) return;
    if (t.dataset.run) { load(t.dataset.run, 0); setView("replay"); window.scrollTo(0, 0); $("#btn-next") && $("#btn-next").focus({ preventScroll: true }); }
    else if (t.dataset.cite) highlight(t.dataset.cite);
    else if (t.id === "btn-next") { stopTimer(); advance(); const b = $("#btn-next"); if (b && !b.disabled) b.focus({ preventScroll: true }); }
    else if (t.id === "btn-reset") { load(state.run, 0); }
    else if (t.id === "btn-pick") { stopTimer(); setView("home"); }
    else if (t.id === "btn-play") {
      if (state.timer) { stopTimer(); renderReplay(); }
      else { state.timer = setInterval(advance, 1400); advance(); renderReplay(); }
      const b = $("#btn-play"); if (b) b.focus({ preventScroll: true });
    }
  });
  document.querySelectorAll(".topnav button").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.tab === "replay" && !state.run && RUNS.length) load(RUNS[0].id, 0);
    stopTimer(); setView(b.dataset.tab);
  }));

  // ------------------------------------------------------------ the host adapter for the guide kit (Take the tour and Builder mode)
  const endOf = (id) => lastStep(RUNS.find((r) => r.id === id));
  const stepOf = (st) => (st.step === "end" ? endOf(st.run) : st.step || 0);
  window.GuideHost = {
    reset() { stopTimer(); state.run = null; state.step = 0; $("#replay").innerHTML = ""; },
    home() { stopTimer(); setView("home"); },
    snapshot() { return { view: state.view, run: state.run, step: state.step }; },
    restore(s) { if (s.run) load(s.run, s.step); setView(s.view); },
    setup(st) { this.reset(); if (st.run) load(st.run, stepOf(st)); setView(st.view); },
    show(st) { if (st.run && !(state.run === st.run && state.step >= stepOf(st))) load(st.run, stepOf(st)); setView(st.view); }
  };

  renderNotice(); renderBuilderNote(); renderHome(); renderPrivacy(); renderFooter();
  setView("home");
})();
