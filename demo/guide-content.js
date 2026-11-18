/*
 * Content for Take a Tour and Builder mode. This is the ONLY file that is specific to a project.
 * Plain data, no DOM, so it can be unit tested in Node. Rewrite every string; keep the shape.
 */
(function (root) {
  // Settings the shared guide code reads.
  const META = {
    storageKey: "incident_investigator_tour_seen_v1",   // unique per project
    tourButton: "Take the tour",
    builderLabel: "Builder mode",
    builderAria: "Builder mode, shows the gaps and fixes on every screen"
  };

  // Builder mode wording. slot: when a step's feature lives on a screen that is not open, its number goes in one labelled row.
  // Set slot to null if the product has a single screen.
  const BUILDER = {
    title: "Builder mode",
    cornerHint: "in this panel once you load it",
    reveal: "as you press Next",
    slot: { when: ".topnav button[data-tab=replay]", into: "#slot-replay", caption: "Stops on the Replay screen", where: "the Replay screen", open: "the Replay tab" }
  };

  // Where each source label comes from.
  const SOURCES = {
    recorded: { short: "Recorded tool output", full: "Taken from output that the real command-line tool printed when it was run on the mock system. Recorded by scripts/record_demo.py, not typed by hand." },
    written: { short: "Written for this demo", full: "Written for this demo by the author. It explains the page and is not output of the tool." }
  };

  // The guide. Pictures are served from assets/ with relative paths so the demo works under /repo-name/ on GitHub Pages.
  const MASCOT = { name: "Product Builder Anshul", wave: "assets/mascot-wave.png", thumbs: "assets/mascot-thumbs.png" };

  const WELCOME = {
    kicker: "Portfolio concept",
    title: "A short tour of a replay",
    p1: "Incident Investigator is a command-line tool that checks why verification codes are missing or late, and cites the check behind every claim. This page replays {{runs}} recorded runs of it.",
    p2: "Each stop shows one idea on the live page: the current scenario, what I built, why it should work, and how I would measure it.",
    note: "Built by Anshul Thangiah as a portfolio concept. Four of the five recordings are a scripted simulation (no AI model runs); one is saved output of a real model. Every person, number and result is synthetic. Not affiliated with any company or product. Each stop is labelled: recorded tool output, or written for this demo."
  };

  // Each step: the four rows, a source label, the live feature to spotlight (target), where its number goes in Builder mode (pin),
  // fallbacks (a tab or panel that leads to it, so every number shows on every screen), and how to put the app in the right state (setup).
  // setup.run is a recording id; setup.step is the number of checks shown (0 = the question only) or "end" for the whole report.
  const TAB = ".topnav button[data-tab=replay]";
  const STEPS = [
    {
      id: "question", n: 1, title: "The question a product manager types", src: "recorded",
      scenario: "A product manager sees a symptom and has to find out which team or system to ask. The question is plain English.",
      built: "The tool takes that question as it is. Here it is the recorded question for scenario S2, with the exact command that was run on the mock system.",
      why: "Starting from the person's own words means no form to fill in first. The tool then decides which read-only checks to run.",
      measure: "How long it takes from typing the question to the first useful result, and how often the person has to reword it or add detail before the tool picks a sensible first check. Shorter and fewer rewordings are better. It tells you whether the tool saves the work of deciding where to look.",
      setup: { view: "replay", run: "S2", step: 0 },
      target: "#q-block", pin: "#q-block", label: "the question panel", fallback: [TAB]
    },
    {
      id: "check", n: 2, title: "The first check it picks, and what it answers", src: "recorded",
      scenario: "Without a tool, someone opens the delivery log by hand and reads it.",
      built: "The tool runs fetch_delivery_logs for a date range and shows the dates it was given, a plain line on what the check answers, and the real numbers from the mock system.",
      why: "The model can only pick a check by name and give it dates. It cannot write a web address, a database query or a file path: the tool builds those itself from your settings. So the card shows everything the model asked for.",
      measure: "Checks run beyond the shortest path to the answer, per investigation, and the seconds until the first useful result. Fewer and faster are better. It tells you whether the tool reaches the evidence without wasted effort.",
      setup: { view: "replay", run: "S2", step: 1 },
      target: "#call-E1", pin: "#call-E1", label: "the first check card", fallback: [TAB]
    },
    {
      id: "evidence", n: 3, title: "Evidence with citation tags", src: "recorded",
      scenario: "A written finding often has no way back to the data behind it.",
      built: "Every claim in the report ends with a tag such as [E1]. Click a tag and the page highlights the check that the tag points to.",
      why: "A claim that points at one check can be tested by reading that check. A claim with no tag is easy to spot.",
      measure: "The % of claims in a report that carry an [E#] tag and whose number matches the check it cites. Higher is better. It tells you whether a reader can trust a sentence without redoing the check, which is where the time is saved.",
      setup: { view: "replay", run: "S2", step: "end" },
      target: "#sec-2", pin: "#sec-2", label: "the Evidence section of the report", fallback: [TAB]
    },
    {
      id: "notchecked", n: 4, title: "What was not checked", src: "recorded",
      scenario: "A confident answer usually hides what nobody looked at.",
      built: "Section 3 of every report lists what the tools could not see and which checks were not available, in a block of its own.",
      why: "Naming the blind spots next to the verdict stops a reader from taking a finding as proof that everything else is fine.",
      measure: "The % of investigations where the real cause was something the report had not listed as a limit. Lower is better. It tells you whether the list of blind spots can be relied on, so nobody assumes everything else was ruled out.",
      setup: { view: "replay", run: "S2", step: "end" },
      target: "#sec-3", pin: "#sec-3", label: "the Not checked section of the report", fallback: [TAB]
    },
    {
      id: "asks", n: 5, title: "The information it asks you for", src: "recorded",
      scenario: "When a check cannot run, a person usually finds out only after asking around.",
      built: "Section 5 says what would make each missing check available, such as phone numbers to look up, or approval for the one check that sends a test message.",
      why: "A named request is something a person can act on. It turns a gap into a next step.",
      measure: "The % of requests in section 5 that a person can supply, and how often supplying them settles the question in the next round. Higher is better. It tells you whether the requests are specific enough to act on, so the next round is short.",
      setup: { view: "replay", run: "S2", step: "end" },
      target: "#sec-5", pin: "#sec-5", label: "the Information needed section of the report", fallback: [TAB]
    },
    {
      id: "inconclusive", n: 6, title: "The run that ends inconclusive on purpose", src: "recorded",
      scenario: "Half of the code requests in scenario S8 are lost before they reach the provider, which no configured tool can see.",
      built: "The expected answer for S8 is inconclusive. The page labels it and shows what the scripted stand-in actually wrote, including where it falls short of that answer.",
      why: "A tool that can say it does not know is safer than one that always names a cause.",
      measure: "On cases where no tool can see the cause, the % of runs that say inconclusive and do not name a cause. Higher is better; naming a wrong cause is the worst result. It tells you whether the tool avoids sending people after a cause that is not there.",
      setup: { view: "replay", run: "S8", step: "end" },
      target: "#inconclusive-label", pin: "#inconclusive-label", label: "the inconclusive note above the report", fallback: [TAB]
    },
    {
      id: "privacy", n: 7, title: "Privacy: three facts", src: "written",
      scenario: "Incident data can hold phone numbers, keys and message text.",
      built: "The Privacy panel states three facts taken from docs/PRIVACY_AND_SAFETY.md: the model passes dates only, phone numbers appear as aliases, and the only check that does more than read, one that sends a real test message to your own number, is off by default.",
      why: "Limiting what the model can ask for and see is easier to trust than a promise about what it will do.",
      measure: "The number of phone numbers, keys or message texts found in what the model sees or in saved files, across a set of test runs. Zero is the target. It tells you whether the privacy rules hold in practice, so the tool can be used without exposing personal data.",
      setup: { view: "home" },
      target: "#privacy", pin: "#privacy", label: "the Privacy panel", fallback: [".topnav button[data-tab=home]"]
    },
    {
      id: "realmodel", n: 8, title: "The same question, answered by a real model", src: "recorded",
      scenario: "The scripted stand-in fills a template with numbers. It does not choose checks or weigh evidence.",
      built: "One recording is a real language model's report on the same invented outage, saved by the evaluation runner. It was given the same read-only checks. Its tool results were not saved, so the cards show that.",
      why: "A model can name the pattern and say what to ask next in sentences a reader can follow. The tool still limits it to read-only checks and makes it cite them.",
      measure: "The % of scenarios where the model reaches the expected outcome and cause, and the checks it runs beyond the shortest path. Higher outcome and fewer extra checks are better. It tells you whether the tool's value holds when the model changes, so a reader knows what to expect from their own model.",
      setup: { view: "replay", run: "S2-real", step: "end" },
      target: "#report", pin: "#report", label: "the real model's report", fallback: [TAB]
    }
  ];

  const CLOSE = {
    title: "What this shows about how I work",
    points: [
      ["Start from the person's question.", "The tool takes the question as typed and picks its own read-only checks."],
      ["Show the evidence.", "Each claim carries a tag that leads to the check behind it."],
      ["Say what was not checked.", "Blind spots and missing checks get a block of their own, and an inconclusive run is a valid result."],
      ["Ship something that runs, and be honest about its limits.", "A working command-line tool with {{tests}} automated tests. Four recordings come from a scripted stand-in and one from a real model, so the page shows both what the tool prints and what a model adds."]
    ],
    ctas: {
      try: { title: "Replay a run", desc: "Pick one of the {{runs}} recordings", focus: "#picker button" },
      builder: { title: "Turn on Builder mode", desc: "See each stop marked on the live screens" }
    },
    limits: "Four recordings are a scripted simulation (rule-based, not an AI) on invented data. The fifth is one real-model run on one scenario: it shows what a model can do, not how often it does it. Across all {{real_scenarios}} scenarios the real model passed {{real_passed}} of {{real_total}} checks in one run, and {{real_all}} scenarios passed every check.",
    plan: [
      ["First", "Fix the gaps the real-model run showed: failure reasons for the latest day, a slow-delivery share, and a nudge to run the API check when the logs look normal."],
      ["Next", "Check that each number in a sentence matches the result it cites."],
      ["Later", "Repeat the full evaluation to see how stable the scores are, and test the database checks against a live test database."]
    ]
  };

  const api = { META, BUILDER, SOURCES, MASCOT, WELCOME, STEPS, CLOSE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.GUIDE = api;
})(typeof self !== "undefined" ? self : this);
