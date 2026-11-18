/*
 * Report view: turns the recorded report text into five section cards. Pure functions, no DOM, so Node can test them.
 * The text is never edited: every line of the report is shown, only laid out (headings, lists, bold labels, citation buttons).
 * The raw text stays available on the page in a toggle. Unexpected lines never throw; they become plain paragraphs.
 *
 * A model's markdown bold (**text**) renders as bold, never as asterisks.
 *   parseReport(text)  -> { preamble: string, sections: [{ n, head, blocks }] }
 *       blocks: { type: "p" | "note", text } | { type: "ul" | "ol", start?, items: [{ text, subs: [string] }] }
 *   renderReport(text) -> html string
 */
(function (root) {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // **text** is bold (a model's markdown); the asterisks are never shown. Applied after escaping, so nothing can inject markup.
  const boldMd = (h) => h.replace(/\*\*(?=\S)([\s\S]+?)\*\*/g, "<b>$1</b>").replace(/\*\*/g, "");
  const withCites = (s) => boldMd(esc(s)).replace(/\[(E\d+)\]/g, (m, id) => `<button type="button" class="cite" data-cite="${id}" aria-label="Show check ${id}">[${id}]</button>`);
  const SEC_LABEL = { 3: "Not checked", 5: "What it needs from you" };
  const BOLD = /^(Why|How or who to ask):\s*([\s\S]*)$/;
  const inline = (s) => { const m = String(s).match(BOLD); return m ? `<b>${m[1]}:</b> ${withCites(m[2])}` : withCites(s); };

  function parseBlocks(lines) {
    const blocks = []; let cur = null;
    lines.forEach((raw) => {
      const line = String(raw === undefined || raw === null ? "" : raw).replace(/\r$/, ""), t = line.trim();
      if (!t) { cur = null; return; }
      let m;
      if ((m = line.match(/^(\d+)\.\s+(.*)$/))) {
        if (!cur || cur.type !== "ol") { cur = { type: "ol", start: Number(m[1]), items: [] }; blocks.push(cur); }
        cur.items.push({ text: m[2], subs: [] });
      } else if ((m = line.match(/^- (.*)$/))) {
        if (!cur || cur.type !== "ul") { cur = { type: "ul", items: [] }; blocks.push(cur); }
        cur.items.push({ text: m[1], subs: [] });
      } else if ((m = line.match(/^\s+[-*]\s+(.*)$/))) {
        if (cur && cur.items.length) cur.items[cur.items.length - 1].subs.push(m[1]);
        else { cur = { type: "ul", items: [{ text: m[1], subs: [] }] }; blocks.push(cur); }
      } else if (/^Optional checks/.test(t)) {
        blocks.push({ type: "note", text: t }); cur = null;
      } else if (/^\s+\S/.test(line) && cur && cur.items.length) {
        const it = cur.items[cur.items.length - 1]; it.text += " " + t;   // a wrapped line of the item above
      } else {
        blocks.push({ type: "p", text: t }); cur = null;
      }
    });
    return blocks;
  }

  function parseReport(text) {
    const out = { preamble: "", sections: [] };
    try {
      const lines = String(text === undefined || text === null ? "" : text).split("\n"), pre = [];
      let sec = null;
      lines.forEach((l) => {
        const m = l.match(/^([1-5])\) (.*)$/);
        if (m) {
          // a model may write "1) **Verdict:** sentence": the bold label is the heading, the sentence stays as the first paragraph
          const b = m[2].match(/^\*\*(?=\S)(.+?)\*\*\s*(.*)$/);
          sec = b ? { n: Number(m[1]), head: m[1] + ") " + b[1].replace(/:\s*$/, ""), lines: b[2] ? [b[2], ""] : [] }
                  : { n: Number(m[1]), head: l.trim(), lines: [] };
          out.sections.push(sec);
        }
        else if (sec) sec.lines.push(l);
        else pre.push(l);
      });
      out.preamble = pre.join("\n").trim();
      out.sections = out.sections.map((s) => ({ n: s.n, head: s.head, blocks: parseBlocks(s.lines) }));
    } catch (e) {
      out.preamble = ""; out.sections = [{ n: 0, head: "", blocks: [{ type: "p", text: String(text) }] }];
    }
    return out;
  }

  function renderBlock(b) {
    if (b.type === "note") return `<p class="rnote">${withCites(b.text)}</p>`;
    if (b.type === "p") return `<p>${withCites(b.text)}</p>`;
    const tag = b.type === "ol" ? "ol" : "ul", start = b.type === "ol" && b.start > 1 ? ` start="${b.start}"` : "";
    return `<${tag} class="rlist"${start}>${b.items.map((it) =>
      `<li>${inline(it.text)}${it.subs.length ? `<ul class="rsub">${it.subs.map((s) => `<li>${inline(s)}</li>`).join("")}</ul>` : ""}</li>`).join("")}</${tag}>`;
  }

  function renderReport(text) {
    const p = parseReport(text);
    const pre = p.preamble ? `<p class="banner">${esc(p.preamble)}</p>` : "";
    const cards = p.sections.map((s) => {
      const lab = SEC_LABEL[s.n] ? `<span class="seclabel">${esc(SEC_LABEL[s.n])}</span>` : "";
      let body; try { body = s.blocks.map(renderBlock).join(""); } catch (e) { body = ""; }
      return `<section class="sec ${SEC_LABEL[s.n] ? "emph" : ""}" id="sec-${s.n}" aria-label="Report section ${s.n}">${lab}<h4>${esc(s.head)}</h4><div class="secbody">${body}</div></section>`;
    }).join("");
    return pre + cards;
  }

  const api = { parseReport, renderReport, withCites, esc, boldMd };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ReportView = api;
})(typeof self !== "undefined" ? self : this);
