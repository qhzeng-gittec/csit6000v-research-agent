"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const icon = (name) => `<svg><use href="#i-${name}"/></svg>`;
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const num = (n) => Number(n || 0).toLocaleString("en-US");
const span = (s) => (s < 90 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`);

const EXPERIMENTS = {
  "web": "Your questions",
  "facts-test100": "Test set · OpenRouter",
  "tacc-facts100": "Test set · course cluster",
  "facts-files30": "Development set",
};
// What each collection is, and the heading it sits under in the collection menu.
const ABOUT = {
  "web": ["Asked in this app", ""],
  "facts-test100": ["Main results, four configurations each", "Reported results"],
  "tacc-facts100": ["Same questions, run on TACC", "Reported results"],
  "facts-files30": ["Used to choose the method", "Method development"],
};
const ARMS = {A0: "Plain", A9: "Rules", A8: "Quotes", A10: "Full system"};
const ARM_HELP = {A0: "Plain agent: no writing rules, no quotes, no verifier", A9: "Writing rules only",
                  A8: "Rules and word-for-word quotes, but the verifier does not send anything back",
                  A10: "Full system: rules, quotes and the verifier"};
const ARM_RANK = {A0: 0, A9: 90, A8: 91, A10: 100};
const WRAP = 100;  // agent/bench.py: wrap_doc
const FILTERS = [
  ["all", "All", () => true],
  ["revised", "Revised", (r) => r.revisions > 0],
  ["failed", "Not verified", (r) => r.status !== "answered"],
];
const EXAMPLES = [
  ["facts-test100/facts/facts0028__A10__r0", "Verifier at work",
   "The first draft has a quote that is not in the document. The verifier sends it back and the model fixes it."],
  ["facts-test100/facts/facts0028__A0__r0", "Plain agent",
   "The same question without quotes: nothing in the answer can be checked against the source."],
  ["tacc-facts100/facts/facts0028__A10__r0", "Course cluster (TACC)",
   "The same question, answered by the course's Qwen service on TACC."],
  ["tacc-facts100/facts/facts0349__A10__r0", "Failure case",
   "The document has a character the model cannot type, so one quote never passes. The answer is marked as not verified."],
];
const LIST_LIMIT = 80;

const S = {runs: [], items: new Map(), order: [], collection: "", filter: "all", search: "", doc: null, mode: "full", turns: [], current: null,
           busy: false, stream: null, lineEls: new Map(), config: {ready: false, model: "", error: ""}, activeRun: "", timer: null};

/* ------------------------------------------------------------------ markdown */
// Python counts characters, JavaScript counts UTF-16 units: convert offsets that come from the server.
function offsets(text) {
  if (!/[\uD800-\uDFFF]/.test(text)) return (i) => i;
  const map = [];
  let u = 0;
  for (const ch of text) { map.push(u); u += ch.length; }
  map.push(u);
  return (i) => map[Math.min(i, map.length - 1)];
}

function inline(s) {
  const codes = [];
  s = s.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return `${codes.length - 1}`; });
  s = esc(s);
  s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  s = s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^\w*])\*(?=\S)([^*\n]*?\S)\*(?![\w*])/g, "$1<em>$2</em>");
  s = s.replace(/(^|[^\w_])_(?=\S)([^_\n]*?\S)_(?![\w_])/g, "$1<em>$2</em>");
  s = s.replace(/\n/g, "<br>");
  return s.replace(/(\d+)/g, (_, i) => `<code>${esc(codes[Number(i)])}</code>`);
}

const LI = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const BLANK = /^\s*$/;
const FENCE = /^\s*```/;
const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const RULE = /^\s*([-*_])(\s*\1){2,}\s*$/;
const TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;
const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

function list(lines, i, base) {
  const first = LI.exec(lines[i]);
  const ordered = /\d/.test(first[2]);
  const start = ordered && parseInt(first[2], 10) !== 1 ? ` start="${parseInt(first[2], 10)}"` : "";
  let html = ordered ? `<ol${start}>` : "<ul>";
  while (i < lines.length) {
    const item = LI.exec(lines[i]);
    if (!item || item[1].length < base) break;
    let text = item[3];
    let nested = "";
    i += 1;
    while (i < lines.length) {
      if (BLANK.test(lines[i])) {
        let j = i + 1;
        while (j < lines.length && BLANK.test(lines[j])) j += 1;
        const next = j < lines.length ? LI.exec(lines[j]) : null;
        if (!next || next[1].length < base) break;
        i = j;
        continue;
      }
      const next = LI.exec(lines[i]);
      if (next && next[1].length >= base + 2) {
        const inner = list(lines, i, next[1].length);
        nested += inner[0];
        i = inner[1];
      } else if (!next && /^\s+\S/.test(lines[i]) && !FENCE.test(lines[i])) {
        text += "\n" + lines[i].trim();
        i += 1;
      } else {
        break;
      }
    }
    html += `<li>${inline(text)}${nested}</li>`;
    if (i < lines.length && BLANK.test(lines[i])) break;
  }
  return [html + (ordered ? "</ol>" : "</ul>"), i];
}

function md(src) {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  const isTable = (i) => lines[i].includes("|") && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1]);
  const startsBlock = (i) => FENCE.test(lines[i]) || HEADING.test(lines[i]) || RULE.test(lines[i]) || LI.test(lines[i])
    || /^\s*>/.test(lines[i]) || isTable(i);
  let html = "";
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    let m;
    if (BLANK.test(line)) {
      i += 1;
    } else if (FENCE.test(line)) {
      const body = [];
      i += 1;
      while (i < lines.length && !FENCE.test(lines[i])) body.push(lines[i++]);
      i += 1;
      html += `<pre><code>${esc(body.join("\n"))}</code></pre>`;
    } else if ((m = HEADING.exec(line))) {
      const level = Math.min(m[1].length + 1, 4);
      html += `<h${level}>${inline(m[2])}</h${level}>`;
      i += 1;
    } else if (RULE.test(line)) {
      html += "<hr>";
      i += 1;
    } else if (/^\s*>/.test(line)) {
      const body = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ""));
      html += `<blockquote>${md(body.join("\n"))}</blockquote>`;
    } else if (isTable(i)) {
      html += "<table><thead><tr>" + cells(line).map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>";
      i += 2;
      while (i < lines.length && lines[i].includes("|") && !BLANK.test(lines[i])) {
        html += "<tr>" + cells(lines[i++]).map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
      }
      html += "</tbody></table>";
    } else if (LI.test(line)) {
      const out = list(lines, i, LI.exec(line)[1].length);
      html += out[0];
      i = out[1];
    } else {
      const body = [line];
      i += 1;
      while (i < lines.length && !BLANK.test(lines[i]) && !startsBlock(i)) body.push(lines[i++]);
      html += `<p>${inline(body.join("\n").trim())}</p>`;
    }
  }
  return html;
}

// Quotes found by the same pattern as the verifier (agent/verify.py: QUOTE_RE); used for drafts only.
function draftQuotes(text, issues) {
  const failed = new Set((issues || []).map((x) => x.cited));
  const out = [];
  const re = /[“"]([^"“”]{8,}?)[”"]\s*\(([^()\s]+)\)/g;
  let m;
  while ((m = re.exec(text))) {
    out.push({start: m.index, end: m.index + m[0].length, text: [m.index + 1, m.index + 1 + m[1].length],
              ok: !failed.has(`"${m[1]}" (${m[2]})`), spans: []});
  }
  return out;
}

// Answer text -> HTML. Each quote becomes a highlighted passage followed by a numbered marker.
function answerHtml(text, quotes, serverOffsets) {
  const at = serverOffsets ? offsets(text) : (i) => i;
  const clean = (s) => s.replace(/[-]/g, "");
  let src = "";
  let pos = 0;
  quotes.forEach((q, i) => {
    const start = at(q.start);
    if (start < pos) return;
    const inner = clean(text.slice(at(q.text[0]), at(q.text[1]))).replace(/\s*\n\s*/g, " ");
    src += clean(text.slice(pos, start)) + `${i}“${inner}”${i}`;
    pos = at(q.end);
  });
  src += clean(text.slice(pos));
  const state = (i) => (quotes[Number(i)].ok ? "ok" : "bad");
  const tip = (i) => (quotes[Number(i)].ok ? "Found word for word in the document. Click to see it."
                                           : "Not found in the document.");
  return md(src)
    .replace(/(\d+)/g, (_, i) => `<mark class="q ${state(i)}" data-q="${i}" title="${tip(i)}">`)
    .replace(//g, "</mark>")
    .replace(/(\d+)/g, (_, i) => `<button type="button" class="cite ${state(i)}" data-q="${i}" title="${tip(i)}">`
      + icon(quotes[Number(i)].ok ? "check" : "x") + (Number(i) + 1) + "</button>");
}

/* ------------------------------------------------------------------ dropdown */
// options: [{value, title, about, count, group}]. Each option is a button, so Enter and Space pick it.
function picker(root, onPick) {
  const button = root.querySelector(".pick");
  const menu = root.querySelector(".menu");
  const options = () => [...menu.querySelectorAll("[data-value]")];
  const close = () => {
    menu.hidden = true;
    button.setAttribute("aria-expanded", "false");
  };
  button.addEventListener("click", () => {
    if (!menu.hidden) return close();
    menu.hidden = false;
    button.setAttribute("aria-expanded", "true");
    return (menu.querySelector("[aria-selected=true]") || options()[0]).focus();
  });
  menu.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-value]");
    if (!el) return;
    close();
    button.focus();
    onPick(el.dataset.value);
  });
  root.addEventListener("keydown", (ev) => {
    if (menu.hidden) return;
    const all = options();
    const at = all.indexOf(document.activeElement);
    const to = {ArrowDown: (at + 1) % all.length, ArrowUp: (at - 1 + all.length) % all.length, Home: 0, End: all.length - 1}[ev.key];
    if (ev.key === "Escape") {
      close();
      button.focus();
    } else if (to !== undefined) {
      ev.preventDefault();
      all[to].focus();
    }
  });
  document.addEventListener("click", (ev) => { if (!root.contains(ev.target)) close(); });
  return (items, value) => {
    const chosen = items.find((x) => x.value === value);
    button.querySelector("span").textContent = chosen ? chosen.title : "";
    let html = "";
    let group = null;
    for (const x of items) {
      if (x.group && x.group !== group) html += `<div class="group">${esc(x.group)}</div>`;
      group = x.group || group;
      html += `<button type="button" role="option" data-value="${esc(x.value)}" aria-selected="${x.value === value}">`
        + `<span class="tick">${x.value === value ? icon("check") : ""}</span>`
        + `<span class="body"><b>${esc(x.title)}</b>${x.about ? `<small>${esc(x.about)}</small>` : ""}</span>`
        + (x.count === undefined ? "" : `<span class="count">${num(x.count)}</span>`) + "</button>";
    }
    menu.innerHTML = html;
  };
}
const setCollections = picker($("collection"), (value) => {
  S.collection = value;
  renderCollections();
  renderRuns();
});
const setArms = picker($("arm-picker"), (run) => openRun(run, false));

/* ------------------------------------------------------------------ sidebar */
const rank = (r) => (r.arm in ARM_RANK ? ARM_RANK[r.arm] : Number(String(r.arm || "").slice(1)) || 0) * 10 + (r.rep || 0);

// One entry per question: a benchmark question was run in several configurations, shown as tabs in the top bar.
function groupRuns() {
  S.items = new Map();
  for (const r of S.runs) {
    if (!S.items.has(r.exp)) S.items.set(r.exp, new Map());
    const key = r.exp === "web" ? r.run : r.id;
    const group = S.items.get(r.exp);
    if (!group.has(key)) group.set(key, {title: r.title || r.id, runs: []});
    group.get(key).runs.push(r);
  }
  for (const group of S.items.values()) {
    for (const item of group.values()) {
      item.runs.sort((x, y) => rank(x) - rank(y));
      item.main = item.runs[item.runs.length - 1];
      item.hay = `${item.title} ${item.main.id}`.toLowerCase();
    }
  }
  const known = Object.keys(EXPERIMENTS).filter((e) => S.items.has(e));
  S.order = known.concat([...S.items.keys()].filter((e) => !(e in EXPERIMENTS)));
  if (!S.items.has(S.collection)) S.collection = S.order[0] || "";
  renderCollections();
}

function renderCollections() {
  setCollections(S.order.map((e) => ({value: e, title: EXPERIMENTS[e] || e, about: (ABOUT[e] || [""])[0],
                                      group: (ABOUT[e] || ["", "Other saved runs"])[1], count: S.items.get(e).size})), S.collection);
}

function itemOf(run) {
  for (const group of S.items.values()) {
    for (const item of group.values()) if (item.runs.some((r) => r.run === run)) return item;
  }
  return null;
}

function renderFilters() {
  $("filters").innerHTML = FILTERS.map(([key, label]) =>
    `<button type="button" role="tab" data-filter="${key}" aria-selected="${S.filter === key}">${label}</button>`).join("");
}

function renderRuns() {
  const words = S.search.toLowerCase().split(/\s+/).filter(Boolean);
  const keep = FILTERS.find((f) => f[0] === S.filter)[2];
  let items = [...(S.items.get(S.collection) || new Map()).values()];
  if (S.collection === "web") items.reverse();
  items = items.filter((item) => keep(item.main) && words.every((w) => item.hay.includes(w)));
  let html = "";
  for (const item of items.slice(0, LIST_LIMIT)) {
    const r = item.main;
    const active = item.runs.some((x) => x.run === S.activeRun);
    const note = r.status !== "answered" ? `<span class="m bad">${esc(r.status.replace(/_/g, " "))}</span>`
      : S.collection === "web" && !r.full ? '<span class="m">Plain agent</span>' : "";
    html += `<button type="button" class="run${active ? " active" : ""}" data-run="${esc(r.run)}" title="${esc(r.id)}">`
      + `<span class="q">${esc(item.title)}</span>${note}</button>`;
  }
  if (items.length > LIST_LIMIT) html += `<div class="more">${items.length - LIST_LIMIT} more. Search to narrow the list.</div>`;
  $("runs").innerHTML = html || '<div class="none">Nothing here matches.</div>';
}

// Top bar: where the open run comes from and, for a benchmark question, its other configurations.
function renderTop() {
  const item = S.activeRun ? itemOf(S.activeRun) : null;
  const exp = S.activeRun.split("/")[0];
  $("context").textContent = S.activeRun ? (EXPERIMENTS[exp] || exp) : "New question";
  const runs = item && item.runs.length > 1 ? item.runs : [];
  const repeated = new Set(runs.filter((r) => r.rep > 0).map((r) => r.arm));
  const label = (r) => (ARMS[r.arm] || r.arm) + (repeated.has(r.arm) ? `, run ${r.rep + 1}` : "");
  const many = runs.length > 4;
  $("context").hidden = runs.length > 0;
  $("arms").hidden = !runs.length || many;
  $("arm-picker").hidden = !many;
  if (many) {
    setArms(runs.map((r) => ({value: r.run, title: label(r), about: ARM_HELP[r.arm] || "A configuration tried during development"})), S.activeRun);
  } else {
    $("arms").innerHTML = runs.map((r) =>
      `<button type="button" class="${r.run === S.activeRun ? "on" : ""}" data-run="${esc(r.run)}" `
      + `title="${esc(ARM_HELP[r.arm] || r.arm)}">${esc(label(r))}</button>`).join("");
  }
}

function renderModel() {
  const c = S.config;
  $("model").textContent = c.ready ? `Model: ${c.model}` : "No model key set. Saved runs only.";
  $("question").disabled = !c.ready;
  $("question").placeholder = c.ready ? "Ask a question about the document"
    : "Set a model key to ask new questions";
}

async function loadRuns() {
  S.runs = await (await fetch("/api/runs")).json();
  groupRuns();
  renderRuns();
  renderTop();
}

/* ------------------------------------------------------------------ document panel */
function renderDoc() {
  const t = S.current;
  if (!t) return;
  $("doc-name").textContent = t.docName;
  const at = offsets(t.doc);
  let marks = [];
  t.quotes.forEach((q, i) => (q.spans || []).forEach(([a, b]) => marks.push({a: at(a), b: at(b), q: i})));
  marks.sort((x, y) => x.a - y.a);
  let end = -1;
  marks = marks.filter((m) => (m.a >= end ? ((end = m.b), true) : false));
  const lines = t.doc.split("\n");
  if (lines[lines.length - 1] === "") lines.pop();
  const parts = [];
  let pos = 0;
  let k = 0;
  for (const line of lines) {
    const stop = pos + line.length;
    let out = "";
    let p = pos;
    let across = -1;  // a quote that continues on the next line
    while (k < marks.length && marks[k].b <= pos) k += 1;
    for (let j = k; j < marks.length && marks[j].a <= stop; j += 1) {
      const a = Math.max(marks[j].a, pos);
      const b = Math.min(marks[j].b, stop);
      if (marks[j].b > stop) across = marks[j].q;
      if (b <= a) continue;
      out += esc(t.doc.slice(p, a)) + `<mark data-q="${marks[j].q}">${esc(t.doc.slice(a, b))}</mark>`;
      p = b;
    }
    parts.push({out: out + esc(t.doc.slice(p, stop)), across});
    pos = stop + 1;
  }
  // The file is wrapped at WRAP characters for the agent. A line that was cut by the wrap is joined with
  // the next one, so the reader sees the original paragraphs; the number is the first line of each.
  const cut = (i) => i + 1 < lines.length && lines[i] !== "" && lines[i + 1] !== ""
    && lines[i].length + 1 + lines[i + 1].trimStart().split(/\s/)[0].length > WRAP;
  let html = "";
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i] === "") continue;
    const first = i;
    let body = "";
    let read = false;
    for (;;) {
      const more = cut(i);
      const glue = !more ? "" : parts[i].across >= 0 ? `<mark data-q="${parts[i].across}"> </mark>` : " ";
      read = read || t.read.has(i + 1);
      body += `<span class="l${t.read.has(i + 1) ? " read" : ""}" data-n="${i + 1}">${parts[i].out}${glue}</span>`;
      if (!more) break;
      i += 1;
    }
    html += `<div class="para${read ? " read" : ""}"><span class="n">${first + 1}</span><p>${body}</p></div>`;
  }
  t.lineCount = lines.length;
  $("doc").innerHTML = html;
  $("doc").scrollTop = 0;
  S.lineEls = new Map([...$("doc").querySelectorAll(".l")].map((el) => [Number(el.dataset.n), el]));
  renderLegend();
}

function renderLegend(message) {
  const t = S.current;
  if (!t) return;
  const located = t.quotes.filter((q) => q.spans && q.spans.length).length;
  let html = `<span><i class="l-read"></i>Read by the agent: ${t.read.size} of ${t.lineCount || 0} lines</span>`;
  if (located) html += `<span><i class="l-ok"></i>${plural(located, "verified quote")}</span>`;
  if (message) html += `<span class="k bad">${esc(message)}</span>`;
  $("legend").innerHTML = html;
  $("quote-nav").hidden = !located;
  if (located) $("quote-pos").textContent = t.active >= 0 ? `${t.active + 1} / ${t.quotes.length}` : `${located} quotes`;
}

function showSource(t) {
  if (S.current !== t) {
    S.current = t;
    renderDoc();
  }
  $("app").classList.add("with-source");
}

function markRead(t, numbers, follow) {
  let first = null;
  for (const n of numbers) {
    if (t.read.has(n)) continue;
    t.read.add(n);
    if (first === null) first = n;
    const el = S.current === t ? S.lineEls.get(n) : null;
    if (el) {
      el.classList.add("read");
      el.closest(".para").classList.add("read");
    }
  }
  if (S.current !== t) return;
  renderLegend();
  if (follow && first !== null && S.lineEls.get(first)) {
    S.lineEls.get(first).closest(".para").scrollIntoView({block: "start", behavior: "smooth"});
  }
}

function focusQuote(t, i, scrollAnswer) {
  showSource(t);
  t.active = i;
  document.querySelectorAll("mark.active").forEach((x) => x.classList.remove("active"));
  const inAnswer = t.el.querySelectorAll(`mark.q[data-q="${i}"]`);
  inAnswer.forEach((x) => x.classList.add("active"));
  const inDoc = $("doc").querySelectorAll(`mark[data-q="${i}"]`);
  inDoc.forEach((x) => x.classList.add("active"));
  if (inDoc[0]) inDoc[0].scrollIntoView({block: "center", behavior: "smooth"});
  renderLegend(inDoc[0] ? "" : "This quote is not in the document.");
  if (scrollAnswer && inAnswer[0]) inAnswer[0].scrollIntoView({block: "center", behavior: "smooth"});
}

function stepQuote(delta) {
  const t = S.current;
  if (!t) return;
  const located = t.quotes.map((q, i) => (q.spans && q.spans.length ? i : -1)).filter((i) => i >= 0);
  if (!located.length) return;
  const at = located.indexOf(t.active);
  focusQuote(t, located[(at + delta + located.length) % located.length], true);
}

/* ------------------------------------------------------------------ thread */
function nearBottom() {
  const el = $("thread");
  return el.scrollHeight - el.scrollTop - el.clientHeight < 160;
}

function hero() {
  const have = new Map(S.runs.map((r) => [r.run, r]));
  const rows = EXAMPLES.filter(([run]) => have.has(run)).map(([run, tag, why]) =>
    `<button type="button" class="example" data-run="${esc(run)}"><span class="q">${esc(tag)}</span>`
    + `<span class="why">${esc(why)}</span><span class="tag">${esc(have.get(run).title)}</span>${icon("chev")}</button>`).join("");
  $("thread").innerHTML = `<div class="hero">
    <h1>Ask a document.<br>Check every quote.</h1>
    <p>The agent reads your document with read-only tools and answers with word-for-word quotes.
       A verifier then checks that every quote really is in the document, and sends the answer back if one is not.</p>
    ${rows ? `<div class="examples"><h2>Saved examples, no key needed</h2>${rows}</div>` : ""}
  </div>`;
}

function resetThread() {
  if (S.stream) S.stream.close();
  S.stream = null;
  clearInterval(S.timer);
  S.turns = [];
  S.current = null;
  S.activeRun = "";
  setBusy(false);
  $("app").classList.remove("with-source");
  $("replay").hidden = true;
  $("toggle-source").hidden = true;
  hero();
  renderRuns();
  renderTop();
}

function newTurn(open, instant) {
  const el = document.createElement("article");
  el.className = "turn";
  const lines = open.doc.split("\n").length - (open.doc.endsWith("\n") ? 1 : 0);
  el.innerHTML = `<div class="user"><div class="bubble">${esc(open.question)}</div>
      <button type="button" class="doclink" data-doc>${icon("doc")}${esc(open.doc_name)}, ${num(lines)} lines</button></div>
    <div class="agent">
      <details class="activity"${instant ? "" : " open"}>
        <summary><span class="spin"></span><span class="label">Starting</span><svg class="caret"><use href="#i-chev"/></svg></summary>
        <ol class="steps"></ol>
      </details>
      <div class="verdict checking" hidden></div>
      <div class="answer" hidden></div>
      <div class="facts" hidden></div>
    </div>`;
  if (!S.turns.length) $("thread").innerHTML = "";
  $("thread").appendChild(el);
  const t = {el, run: open.run, question: open.question, docName: open.doc_name, doc: open.doc, quotes: [], read: new Set(),
             active: -1, done: false, instant, started: null, calls: 0, revisions: 0, lineCount: lines, plain: false};
  S.turns.push(t);
  $("toggle-source").hidden = false;
  S.current = null;
  showSource(t);
  if (!instant) el.scrollIntoView({block: "start", behavior: "smooth"});
  return t;
}

function setLabel(t, html, working) {
  const summary = t.el.querySelector(".activity > summary");
  summary.querySelector(".label").innerHTML = html;
  const spin = summary.querySelector(".spin");
  if (spin && !working) spin.remove();
}

function addStep(t, e, kind, name, what, details) {
  const stick = !t.instant && nearBottom();
  const li = document.createElement("li");
  li.className = `step ${kind}`;
  const clock = t.started !== null && e.ts ? Math.max(0, e.ts - t.started) : null;
  const time = clock === null ? "" : `<span class="t">${Math.floor(clock / 60)}:${String(Math.floor(clock % 60)).padStart(2, "0")}</span>`;
  li.innerHTML = `<span class="ic">${icon(name)}</span><div><div class="head"><span class="what">${what}</span>${time}</div>${details || ""}</div>`;
  t.el.querySelector(".steps").appendChild(li);
  if (stick) $("thread").scrollTop = $("thread").scrollHeight;
}

const fold = (label, body) => `<details><summary>${label}</summary>${body}</details>`;
const short = (s, n) => (s.length > n ? s.slice(0, n) + "…" : s);

function toolStep(t, e) {
  const a = e.args || {};
  const output = fold(`Output, ${num(e.content.length)} characters`, `<pre>${esc(e.content)}</pre>`);
  if (e.is_error) {
    const call = e.name === "bash" ? `<code>${esc(short(String(a.command || ""), 90))}</code>` : `<code>${esc(e.name)}</code>`;
    return addStep(t, e, "warn", "alert", `${call} was refused`, `<pre>${esc(e.content)}</pre>`);
  }
  if (e.name === "read") {
    const numbers = [...e.content.matchAll(/^\s*(\d+)\t/gm)].map((m) => Number(m[1]));
    markRead(t, numbers, !t.instant);
    const range = numbers.length ? `lines ${numbers[0]} to ${numbers[numbers.length - 1]} of ` : "";
    return addStep(t, e, "", "eye", `Read ${range}<code>${esc(a.path || "doc.txt")}</code>`, output);
  }
  if (e.name === "bash") {
    if (/\bdoc\.txt\b/.test(String(a.command || ""))) {
      markRead(t, [...e.content.matchAll(/^(\d+)[:-]/gm)].map((m) => Number(m[1])), !t.instant);
    }
    return addStep(t, e, "", "term", `Ran <code>${esc(short(String(a.command || ""), 110))}</code>`, output);
  }
  if (e.name === "edit_draft") {
    const diff = `<div class="diff"><div class="del">${esc(String(a.old || ""))}</div><div class="add">${esc(String(a.new || ""))}</div></div>`;
    return addStep(t, e, "", "pen", "Edited the draft", fold("What changed", diff));
  }
  return addStep(t, e, "", "term", `Called <code>${esc(e.name)}</code>`, output);
}

function showAnswer(t, text, quotes, draft, serverOffsets) {
  const el = t.el.querySelector(".answer");
  el.hidden = false;
  el.classList.toggle("draft", draft);
  el.innerHTML = text.trim() ? answerHtml(text, quotes, serverOffsets) : "<p>(no answer text)</p>";
}

function showVerdict(t, kind, html) {
  const el = t.el.querySelector(".verdict");
  el.hidden = false;
  el.className = `verdict ${kind}`;
  const name = {ok: "shield", bad: "alert", warn: "alert", checking: "shield"}[kind];
  el.innerHTML = icon(name) + `<div>${html}</div>`;
}

function finish(t, r) {
  const m = r.meta;
  t.done = true;
  t.plain = m.cite !== "quote";
  t.quotes = r.quotes;
  t.read = new Set();
  for (const [a, b] of r.read) for (let n = a; n <= b; n += 1) t.read.add(n);
  showAnswer(t, r.answer, r.quotes, false, true);
  const total = r.quotes.length;
  const bad = r.quotes.filter((q) => !q.ok).length;
  const sentBack = m.revisions ? ` <span>The verifier sent the draft back ${m.revisions === 1 ? "once" : m.revisions + " times"}.</span>` : "";
  if (m.status === "error") showVerdict(t, "bad", `The run failed. <span>${esc(m.error || "")}</span>`);
  else if (m.status === "empty") showVerdict(t, "bad", "The model returned no answer text.");
  else if (t.plain) showVerdict(t, "checking", "Plain agent. <span>No quotes, so nothing in this answer was verified.</span>");
  else if (!total) showVerdict(t, "warn", "The answer contains no quotes. <span>Nothing could be verified.</span>");
  else if (!bad && m.status === "answered") showVerdict(t, "ok", `All ${plural(total, "quote")} found word for word in the document.${sentBack}`);
  else if (m.status === "budget_exhausted") showVerdict(t, "warn", `The agent ran out of steps. <span>${total - bad} of ${plural(total, "quote")} verified.</span>`);
  else if (m.status === "collapse_reverted") showVerdict(t, "warn", `A revision removed too much, so the first draft was kept. <span>${total - bad} of ${plural(total, "quote")} verified.</span>`);
  else showVerdict(t, "bad", `Not verified: ${bad} of ${plural(total, "quote")} could not be found in the document. <span>The verifier allows two revision rounds.</span>`);
  const facts = [m.model, plural(m.steps || 0, "model call"), `${num(m.prompt_tokens)} + ${num(m.completion_tokens)} tokens`,
                 m.wall_s != null ? span(Number(m.wall_s)) : ""].filter(Boolean);
  const box = t.el.querySelector(".facts");
  box.hidden = false;
  box.innerHTML = facts.map((x) => `<span>${esc(x)}</span>`).join("")
    + `<button type="button" class="ghost" data-copy>${icon("copy")}Copy</button>`;
  t.answer = r.answer;
  const worked = m.wall_s != null ? `Worked for ${span(Number(m.wall_s))}` : "Finished";
  setLabel(t, `<b>${worked}</b> · ${plural(m.steps || 0, "model call")}${m.revisions ? " · " + plural(m.revisions, "revision") : ""}`, false);
  if (!t.instant) t.el.querySelector(".activity").open = false;
  if (S.current === t) {
    const top = $("doc").scrollTop;
    renderDoc();
    $("doc").scrollTop = top;
  }
}

function onEvent(t, e) {
  if (t.started === null && e.ts) t.started = e.ts;
  if (e.type === "assistant") {
    t.calls += 1;
    const calls = e.tool_calls || [];
    const text = (e.content || "").trim();
    if (calls.length) return setLabel(t, calls.some((c) => c.function.name === "edit_draft") ? "Fixing the draft" : "Reading the document", true);
    if (!text) return addStep(t, e, "warn", "alert", "The model returned an empty reply");
    if (text.length < 40 && t.revisions) {
      addStep(t, e, "", "check", "Finished the revision");
    } else {
      addStep(t, e, "", "pen", `Wrote a draft answer, ${num(text.length)} characters`);
      showAnswer(t, e.content, [], true, false);
    }
    return setLabel(t, "Checking the quotes", true);
  }
  if (e.type === "tool") return toolStep(t, e);
  if (e.type === "verdict") {
    showAnswer(t, e.draft, draftQuotes(e.draft, e.issues), true, false);
    if (e.ok) {
      showVerdict(t, "ok", `All ${plural(e.citations, "quote")} found word for word in the document.`);
      return addStep(t, e, "ok", "shield", `<b>Verifier passed.</b> All ${plural(e.citations, "quote")} are in the document, word for word`);
    }
    const items = e.issues.map((x) => `<div class="issue"><div class="cited">${esc(short(x.cited || "", 260))}</div>`
      + `<div>${esc(x.message)}</div>${x.hint ? `<div class="hint">${esc(short(x.hint, 420))}</div>` : ""}</div>`).join("");
    showVerdict(t, "bad", `${plural(e.issues.length, "quote")} not found in the document. <span>Sent back for revision.</span>`);
    return addStep(t, e, "bad", "alert", `<b>Verifier found ${plural(e.issues.length, "problem")}.</b> A quote is not in the document`, items);
  }
  if (e.type === "user" && e.note === "verification") {
    t.revisions += 1;
    setLabel(t, "Revising the answer", true);
    return addStep(t, e, "", "back", `Sent back to the model, revision round ${t.revisions}`, fold("Message to the model", `<pre>${esc(e.content)}</pre>`));
  }
  if (e.type === "user" && e.note === "empty_reply") return addStep(t, e, "warn", "back", "Empty reply, asked the model to answer directly");
  if (e.type === "user" && e.note === "budget_exhausted") return addStep(t, e, "warn", "alert", "Step limit reached, asked for a final answer");
  if (e.type === "collapse_reverted") return addStep(t, e, "warn", "alert", "The revision removed too much of the answer, so the first draft is kept");
  if (e.type === "error") {
    setLabel(t, "<b>Stopped</b>", false);
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = e.message;
    return t.el.querySelector(".agent").appendChild(box);
  }
  if (e.type === "done") return finish(t, e);
  return null;
}

/* ------------------------------------------------------------------ running */
function setBusy(busy) {
  S.busy = busy;
  updateSend();
}

function updateSend() {
  $("send").disabled = S.busy || !S.config.ready || !S.doc || !$("question").value.trim();
  const saved = S.turns.length && S.turns[S.turns.length - 1].done && S.turns[S.turns.length - 1].run;
  $("replay").hidden = S.busy || !saved;
}

function attach(doc) {
  S.doc = doc;
  const el = $("attached");
  el.hidden = !doc;
  el.innerHTML = doc ? `<span class="chip">${icon("doc")}${esc(doc.name)} · ${num(doc.text.length)} characters`
    + `<button type="button" id="detach" title="Remove the document">${icon("x")}</button></span>` : "";
  $("attach").hidden = Boolean(doc);
  updateSend();
}

function follow(url, onEnd) {
  let t = null;
  const stream = new EventSource(url);
  S.stream = stream;
  setBusy(true);
  const stop = () => {
    stream.close();
    if (S.stream === stream) {
      S.stream = null;
      setBusy(false);
    }
    if (onEnd) onEnd();
  };
  stream.onmessage = (msg) => {
    const e = JSON.parse(msg.data);
    if (e.type === "open") {
      t = newTurn(e, false);
      setLabel(t, "Thinking", true);
      return;
    }
    if (!t) return;
    onEvent(t, e);
    if (e.type === "done" || e.type === "error") stop();
  };
  stream.onerror = () => {
    if (t && !t.done) onEvent(t, {type: "error", message: "The connection to the local server was lost."});
    stop();
  };
}

async function openRun(run, replay) {
  attach(null);
  resetThread();
  S.activeRun = run;
  const exp = run.split("/")[0];
  if (S.items.has(exp) && S.collection !== exp) {
    S.collection = exp;
    renderCollections();
  }
  renderRuns();
  renderTop();
  if (replay) return follow(`/api/replay?run=${encodeURIComponent(run)}`, () => adoptDocument());
  const res = await fetch(`/api/run?run=${encodeURIComponent(run)}`);
  const events = await res.json();
  if (!res.ok) return null;
  const t = newTurn(events[0], true);
  for (const e of events.slice(1)) onEvent(t, e);
  $("thread").scrollTop = 0;
  adoptDocument();
  return updateSend();
}

// After a saved run is opened, its document stays attached so that a new question can be asked about it.
function adoptDocument() {
  const t = S.turns[S.turns.length - 1];
  if (t && !S.doc) attach({name: t.docName, text: t.doc});
}

async function ask() {
  const question = $("question").value.trim();
  if (S.busy || !question || !S.doc) return;
  const body = {question, document: S.doc.text, doc_name: S.doc.name, system: S.mode};
  setBusy(true);
  const res = await fetch("/api/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) {
    setBusy(false);
    $("notice").hidden = false;
    $("notice").textContent = data.error;
    return;
  }
  $("question").value = "";
  $("question").style.height = "auto";
  S.activeRun = `web/${data.run}`;
  renderTop();
  follow(`/api/live?run=${encodeURIComponent(data.run)}`, async () => {
    S.collection = "web";
    await loadRuns();
  });
}

/* ------------------------------------------------------------------ events */
$("runs").addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-run]");
  if (el) openRun(el.dataset.run, false);
});
$("filters").addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-filter]");
  if (!el) return;
  S.filter = el.dataset.filter;
  renderFilters();
  renderRuns();
});
$("search").addEventListener("input", (ev) => { S.search = ev.target.value; renderRuns(); });
$("arms").addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-run]");
  if (el) openRun(el.dataset.run, false);
});
$("new").addEventListener("click", () => { attach(null); resetThread(); $("question").focus(); });
$("replay").addEventListener("click", () => {
  const t = S.turns[S.turns.length - 1];
  if (t && t.run) openRun(t.run, true);
});
$("toggle-source").addEventListener("click", () => $("app").classList.toggle("with-source"));
$("close-source").addEventListener("click", () => $("app").classList.remove("with-source"));
$("prev-quote").addEventListener("click", () => stepQuote(-1));
$("next-quote").addEventListener("click", () => stepQuote(1));

$("thread").addEventListener("click", (ev) => {
  const example = ev.target.closest(".example");
  if (example) return openRun(example.dataset.run, true);
  const turnEl = ev.target.closest(".turn");
  const t = S.turns.find((x) => x.el === turnEl);
  if (!t) return null;
  const quote = ev.target.closest("[data-q]");
  if (quote && t.done) return focusQuote(t, Number(quote.dataset.q), false);
  if (ev.target.closest("[data-doc]")) return showSource(t);
  const copy = ev.target.closest("[data-copy]");
  if (copy && navigator.clipboard) {
    navigator.clipboard.writeText(t.answer || "");
    copy.lastChild.textContent = "Copied";
  }
  return null;
});
$("doc").addEventListener("click", (ev) => {
  const mark = ev.target.closest("mark[data-q]");
  if (mark && S.current) focusQuote(S.current, Number(mark.dataset.q), true);
});

$("mode").addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-mode]");
  if (!el) return;
  S.mode = el.dataset.mode;
  for (const b of $("mode").children) b.setAttribute("aria-checked", String(b === el));
});
$("question").addEventListener("input", (ev) => {
  ev.target.style.height = "auto";
  ev.target.style.height = Math.min(ev.target.scrollHeight, 180) + "px";
  updateSend();
});
$("question").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
    ev.preventDefault();
    ask();
  }
});
$("composer").addEventListener("submit", (ev) => { ev.preventDefault(); ask(); });
$("attached").addEventListener("click", (ev) => { if (ev.target.closest("#detach")) attach(null); });

function openSheet() {
  $("paste").value = "";
  $("paste-name").value = "";
  $("sheet").hidden = false;
  $("paste").focus();
}
async function readFile(file) {
  if (!file) return;
  attach({name: file.name, text: await file.text()});
  $("sheet").hidden = true;
  $("question").focus();
}
$("attach").addEventListener("click", openSheet);
$("cancel-doc").addEventListener("click", () => { $("sheet").hidden = true; });
$("sheet").addEventListener("click", (ev) => { if (ev.target === $("sheet")) $("sheet").hidden = true; });
$("choose").addEventListener("click", () => $("file").click());
$("file").addEventListener("change", (ev) => { readFile(ev.target.files[0]); ev.target.value = ""; });
$("use-doc").addEventListener("click", () => {
  const text = $("paste").value;
  if (!text.trim()) return $("paste").focus();
  attach({name: $("paste-name").value.trim() || "pasted text", text});
  $("sheet").hidden = true;
  return $("question").focus();
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") $("sheet").hidden = true; });
const box = $("box");
box.addEventListener("dragover", (ev) => { ev.preventDefault(); box.classList.add("drag"); });
box.addEventListener("dragleave", () => box.classList.remove("drag"));
box.addEventListener("drop", (ev) => {
  ev.preventDefault();
  box.classList.remove("drag");
  readFile(ev.dataTransfer.files[0]);
});

(async function init() {
  renderFilters();
  S.config = await (await fetch("/api/config")).json();
  renderModel();
  await loadRuns();
  hero();
  updateSend();
})();
