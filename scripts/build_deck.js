// Builds docs/demo/slides.pptx (speaker notes included).
// Usage: PPTX_SKILL_DIR=<pptx skill dir> NODE_PATH=<node_modules with pptxgenjs> node scripts/build_deck.js docs/demo/slides.pptx
// Dev-time tool only: not part of the service, adds no Python dependency.
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");

const OUT = process.argv[2] || "docs/demo/slides.pptx";
const THEME = {
  name: "Risk Harness",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0F1B2D", lt1: "FFFFFF", dk2: "24344F", lt2: "EEF2F6",
    accent1: "1FB5A3", accent2: "F2A33A", accent3: "E4572E",
    accent4: "5B8DEF", accent5: "9AA9BF", accent6: "3DDC97",
    hlink: "1FB5A3", folHlink: "9AA9BF",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "AI for the SDLC, inside the controls";
const C = pres.SchemeColor;

const titleOpts = (color) => ({
  name: "title", type: "title", x: 0.5, y: 0.35, w: 9, h: 0.8,
  fontSize: 32, bold: true, color, margin: 0, valign: "top",
});
const num = () => ({ x: 9.1, y: 5.2, w: 0.5, h: 0.3, color: C.accent5, fontSize: 10 });
pres.defineSlideMaster({ title: "DARK", background: { color: C.text1 }, slideNumber: num(),
  objects: [{ placeholder: { options: titleOpts(C.background1), text: "" } }] });
pres.defineSlideMaster({ title: "LIGHT", background: { color: C.background1 }, slideNumber: num(),
  objects: [{ placeholder: { options: titleOpts(C.text1), text: "" } }] });

const shadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 90, opacity: 0.15 });
const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, ...o });

function slide(master, title, notes, section) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  s.addNotes(notes);
  return s;
}
const light = (t, n, sec) => slide("LIGHT", t, n, sec);
const dark = (t, n, sec) => slide("DARK", t, n, sec);

function card(s, x, y, w, h, head, body, accent, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, shadow: shadow(), objectName: name + " card" });
  s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.2, w: 0.4, h: 0.4, fill: { color: accent }, objectName: name + " marker" });
  txt(s, head, { x: x + 0.75, y: y + 0.15, w: w - 0.95, h: 0.5, fontSize: 18, bold: true, color: C.text1, valign: "middle", objectName: name + " head" });
  txt(s, body, { x: x + 0.2, y: y + 0.8, w: w - 0.4, h: h - 0.95, fontSize: 14, color: C.text2, valign: "top", objectName: name + " body" });
}
function chip(s, x, y, w, label, fill, color, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.6, rectRadius: 0.08, fill: { color: fill }, objectName: name });
  txt(s, label, { x, y, w, h: 0.6, fontSize: 12, bold: true, color, align: "center", valign: "middle", objectName: name + " label" });
}

// 1. Title
pres.addSection({ title: "Framing" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Framing" });
  s.addNotes("Open: this is not a chatbot in an IDE. It is an agent that works through skills, under hooks, with humans at gates. Ask the CTO: what would your auditor need to see?");
  s.addShape(pres.shapes.OVAL, { x: 7.6, y: 0.6, w: 1.6, h: 1.6, fill: { color: C.accent1 }, objectName: "motif outer" });
  s.addShape(pres.shapes.OVAL, { x: 8.0, y: 1.0, w: 0.8, h: 0.8, fill: { color: C.text1 }, objectName: "motif inner" });
  txt(s, "AI for the SDLC,\ninside the controls", { x: 0.6, y: 1.7, w: 8, h: 1.6, fontFace: "Cambria", fontSize: 44, bold: true, color: C.background1, valign: "top", objectName: "title text" });
  txt(s, "Claude Code as the harness for a bank", { x: 0.6, y: 3.5, w: 8, h: 0.5, fontSize: 20, color: C.accent1, objectName: "subtitle" });
  txt(s, "Skills · Hooks · Subagents · Headless · Audit", { x: 0.6, y: 4.6, w: 8, h: 0.4, fontSize: 14, color: C.accent5, objectName: "tagline" });
}

// 2. Problem
{
  const s = light("\"Trust the model\" is not a control",
    "Banks want AI across the SDLC but cannot accept trust as a control. Controls have to be mechanical, logged and independent of the model. Ask: what would your auditor need to see?", "Framing");
  card(s, 0.5, 1.5, 2.8, 2.9, "Mechanical", "Enforced by code that runs on every prompt and tool call, not by instructions the model may ignore.", C.accent1, "mechanical");
  card(s, 3.6, 1.5, 2.8, 2.9, "Logged", "Every allow and block is recorded as hashes, so the trail never holds the sensitive data itself.", C.accent2, "logged");
  card(s, 6.7, 1.5, 2.8, 2.9, "Independent", "Review comes from a separate read-only agent and from humans, not from the author.", C.accent4, "independent");
}

// 3. Harness
pres.addSection({ title: "Harness" });
{
  const s = light("The harness: five building blocks",
    "Walk the five. Skills are procedures with scoped tools. Hooks are deterministic enforcement. Subagents give independent review. Headless runs the same controls in automation. Audit answers what did the AI do. Diagram: Harness overview in docs/demo/diagrams.md.", "Harness");
  const items = [
    ["Skills", "Repeatable procedures, each with its own tool allow-list", C.accent1],
    ["Hooks", "Deterministic checks on every prompt, tool call and stop", C.accent2],
    ["Subagents", "Independent, read-only reviewer with explicit tools", C.accent4],
    ["Headless", "Same hooks in automation, with caps", C.accent6],
    ["Audit", "Hash-only decision log plus a per-PR evidence pack", C.accent3],
  ];
  items.forEach(([h, b, col], i) => {
    const y = 1.35 + i * 0.75;
    s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: col }, objectName: `block ${h} marker` });
    txt(s, String(i + 1), { x: 0.5, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.text1, align: "center", valign: "middle", objectName: `block ${h} num` });
    txt(s, h, { x: 1.2, y, w: 2.2, h: 0.6, fontSize: 20, bold: true, color: C.text1, valign: "middle", objectName: `block ${h} name` });
    txt(s, b, { x: 3.4, y, w: 6.1, h: 0.6, fontSize: 16, color: C.text2, valign: "middle", objectName: `block ${h} desc` });
  });
}

// 4. Gates
{
  const s = light("Six human gates",
    "Claude never merges, never deploys and never self-approves. G1 spec, G2 plan, G3 ship, G4 triage, G5 PR review by CODEOWNERS, G6 production approval. Say plainly: admin enforcement and the required CI check are not on yet in this demo repo.", "Harness");
  const g = [["G1", "Spec"], ["G2", "Plan"], ["G3", "Ship"], ["G4", "Triage"], ["G5", "PR review"], ["G6", "Prod"]];
  g.forEach(([k, v], i) => {
    const x = 0.5 + i * 1.5;
    s.addShape(pres.shapes.OVAL, { x: x + 0.1, y: 1.8, w: 1.1, h: 1.1, fill: { color: C.text1 }, objectName: `gate ${k}` });
    txt(s, k, { x: x + 0.1, y: 1.8, w: 1.1, h: 1.1, fontSize: 24, bold: true, color: C.accent1, align: "center", valign: "middle", objectName: `gate ${k} label` });
    txt(s, v, { x, y: 3.05, w: 1.3, h: 0.4, fontSize: 14, bold: true, color: C.text1, align: "center", objectName: `gate ${k} name` });
  });
  txt(s, "The agent proposes. Hooks and humans dispose.", { x: 0.5, y: 4.2, w: 9, h: 0.5, fontSize: 20, italic: true, color: C.text2, align: "center", objectName: "gates tagline" });
}

// 5. Live guardrails
{
  const s = dark("Live: the guardrails block things",
    "Do these live, they cost almost nothing because they are blocked before model work. 1) paste a fake card number into a prompt. 2) ask it to read .env. 3) try to commit with red tests. Then show one audit.jsonl line: decisions, hashes only.", "Harness");
  const rows = [["Prompt with a fake card number", "UserPromptSubmit DLP"], ["Read .env", "PreToolUse path policy"], ["Commit with red tests", "Commit gate + Stop gate"]];
  rows.forEach(([a, b], i) => {
    const y = 1.5 + i * 0.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 9, h: 0.75, rectRadius: 0.08, fill: { color: C.text2 }, objectName: `block row ${i + 1}` });
    txt(s, a, { x: 0.8, y, w: 5, h: 0.75, fontSize: 18, color: C.background1, valign: "middle", objectName: `block action ${i + 1}` });
    txt(s, "BLOCKED  " + b, { x: 5.2, y, w: 4.1, h: 0.75, fontSize: 14, bold: true, color: C.accent2, align: "right", valign: "middle", objectName: `block result ${i + 1}` });
  });
  txt(s, "Each decision is logged to .claude/audit/audit.jsonl as hashes only.", { x: 0.5, y: 4.55, w: 9, h: 0.4, fontSize: 14, color: C.accent5, objectName: "audit note" });
}

// 6. Flow 1
pres.addSection({ title: "Flow 1" });
{
  const s = light("Flow 1: PRD to prod (recorded)",
    "Play recording R1, about 3 minutes. Stress that G1 and G2 are human decisions, and that deploy is CI plus a human approver, never Claude. Diagram: Flow 1 in docs/demo/diagrams.md.", "Flow 1");
  const steps = [["PRD", C.accent5, C.text1], ["Spec", C.accent1, C.text1], ["G1", C.text1, C.accent1], ["Plan", C.accent1, C.text1], ["G2", C.text1, C.accent1]];
  const steps2 = [["Code\ntests first", C.accent1, C.text1], ["Secure\nship", C.accent1, C.text1], ["G3", C.text1, C.accent1], ["PR + G5", C.text1, C.accent1], ["CI + G6", C.text1, C.accent1]];
  steps.forEach(([l, f, c], i) => chip(s, 0.5 + i * 1.8, 1.6, 1.5, l, f, c, `flow1 a${i}`));
  steps2.forEach(([l, f, c], i) => chip(s, 0.5 + i * 1.8, 2.8, 1.5, l, f, c, `flow1 b${i}`));
  txt(s, "Dark chips are human gates. Deploy is CI, never Claude.", { x: 0.5, y: 4.0, w: 9, h: 0.4, fontSize: 16, color: C.text2, objectName: "flow1 caption" });
}

// 7. Flow 2 symptom (native chart)
pres.addSection({ title: "Flow 2" });
{
  const s = light("Flow 2: declines spike after midnight",
    "Synthetic traffic through the real decision code, so the symptom is genuine and not a hand-edited log. Baseline is about 20 declines a day; the log now shows 43, with 26 between 00:00 and 05:00 UTC. Reproduce with the histogram command in README section 4a.", "Flow 2");
  const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
  const counts = { 0: 1, 2: 16, 3: 4, 4: 5, 6: 1, 7: 2, 8: 1, 9: 1, 10: 2, 12: 1, 16: 3, 18: 1, 19: 3, 20: 1, 23: 1 };
  s.addChart(pres.charts.BAR, [{ name: "DECLINED_VELOCITY", labels: hours, values: hours.map((_, i) => counts[i] || 0) }], {
    x: 0.5, y: 1.3, w: 6.2, h: 3.7, barDir: "col", chartColors: ["1FB5A3"],
    showTitle: true, title: "Velocity declines by UTC hour", titleFontSize: 14, titleColor: "0F1B2D", titleFontFace: "+mn-lt",
    catAxisLabelColor: "24344F", valAxisLabelColor: "24344F", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, showLegend: false,
    valGridLine: { color: "EEF2F6", size: 0.5 }, catGridLine: { style: "none" },
  });
  txt(s, "43", { x: 7.1, y: 1.4, w: 2.4, h: 0.9, fontSize: 54, bold: true, fontFace: "Cambria", color: C.accent3, objectName: "stat 43" });
  txt(s, "declines today, against about 20 on a clean run", { x: 7.1, y: 2.3, w: 2.4, h: 0.7, fontSize: 14, color: C.text2, valign: "top", objectName: "stat 43 label" });
  txt(s, "26", { x: 7.1, y: 3.2, w: 2.4, h: 0.9, fontSize: 54, bold: true, fontFace: "Cambria", color: C.accent1, objectName: "stat 26" });
  txt(s, "of them between 00:00 and 05:00 UTC", { x: 7.1, y: 4.1, w: 2.4, h: 0.7, fontSize: 14, color: C.text2, valign: "top", objectName: "stat 26 label" });
}

// 8. Triage
{
  const s = light("Triage: evidence before opinion",
    "Live: /log-triage. Read the report aloud, this is G4. Point out that redaction happens first and that the skill is read-only; the model used is the cheaper one.", "Flow 2");
  card(s, 0.5, 1.5, 2.8, 2.9, "1. Redact", "fintech-data-check runs first; the model only sees the redacted view of the log.", C.accent1, "triage redact");
  card(s, 3.6, 1.5, 2.8, 2.9, "2. Cluster", "Bucket by decline reason and hour, compare to baseline, correlate with recent commits.", C.accent2, "triage cluster");
  card(s, 6.7, 1.5, 2.8, 2.9, "3. Classify", "Severity, customer impact, money at risk and auto_fix_eligible. Not eligible pages on-call.", C.accent4, "triage classify");
}

// 9. Headless
{
  const s = dark("Headless: no human at the keyboard",
    "Play recording R3. Key point: claude -p WITHOUT --bare, so every hook still fires. Show the allow-lists and the dollar caps in scripts/log_to_fix.sh. The script stops before commit; shipping stays human. Do not claim a turn cap: --max-turns is unverified.", "Flow 2");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.4, w: 9, h: 1.7, rectRadius: 0.08, fill: { color: C.text2 }, objectName: "terminal" });
  txt(s, "$ scripts/log_to_fix.sh INC-DEMO-001", { x: 0.8, y: 1.55, w: 8.4, h: 0.4, fontFace: "Courier New", fontSize: 16, color: C.accent6, objectName: "terminal cmd" });
  txt(s, "Stage 1  triage   haiku   read-only    cap $0.50\nG4       eligibility check, stops if not eligible\nStage 2  fix      sonnet  app/ + tests/ cap $1.50", { x: 0.8, y: 2.0, w: 8.4, h: 1.0, fontFace: "Courier New", fontSize: 12, color: C.background1, valign: "top", objectName: "terminal out" });
  const facts = [["No --bare", "hooks run"], ["Allow-listed tools", "per stage"], ["Stops before commit", "human ships"]];
  facts.forEach(([a, b], i) => {
    const x = 0.5 + i * 3.1;
    txt(s, a, { x, y: 3.5, w: 2.9, h: 0.5, fontSize: 20, bold: true, color: C.accent1, objectName: `fact ${i} head` });
    txt(s, b, { x, y: 4.0, w: 2.9, h: 0.4, fontSize: 14, color: C.background1, objectName: `fact ${i} body` });
  });
}

// 10. Fix
{
  const s = light("The fix: test first, minimal diff",
    "Reference result is on the demo-fixed branch: git diff demo-start demo-fixed --stat. The strict xfail forced the guard test back on, which is the system telling the fixer to remove the marker. The diff budget is 3 files or 80 lines.", "Flow 2");
  card(s, 0.5, 1.5, 4.3, 2.9, "Before", "Overnight events recorded three times, so counts inflate and cards are falsely declined. Money compared through float().", C.accent3, "before");
  card(s, 5.2, 1.5, 4.3, 2.9, "After", "Failing regression test first, then removal of the mirroring and a Decimal compare. Strict xfail removed. 95 tests pass.", C.accent1, "after");
}

// 11. Review
{
  const s = dark("Independent review",
    "The security-reviewer subagent has read-only tools and did not write the code. Any loosened control or test, including an xfail, is High and blocks. Do not claim you can force a specific subagent in headless mode; that is unverified.", "Flow 2");
  txt(s, "security-reviewer", { x: 0.5, y: 1.5, w: 9, h: 0.6, fontFace: "Courier New", fontSize: 28, bold: true, color: C.accent1, objectName: "agent name" });
  txt(s, "Tools: Read, Grep, Glob, git diff, git log, git status\nNo edit. No network. Reviews the diff against main.", { x: 0.5, y: 2.2, w: 9, h: 0.9, fontSize: 18, color: C.background1, valign: "top", objectName: "agent tools" });
  txt(s, "Any High finding = BLOCK", { x: 0.5, y: 3.5, w: 9, h: 0.6, fontFace: "Cambria", fontSize: 32, bold: true, color: C.accent2, objectName: "agent rule" });
}

// 12. Honest lessons
pres.addSection({ title: "Close" });
{
  const s = light("Honest lessons",
    "Candour is the credibility. 1) A chained git add and commit slipped past the first commit gate because nothing was staged yet; CI caught it, and we added working-tree and outgoing-commit scans plus git hooks. 2) The float-money hook is lexical and the seeded float compare passed it. 3) Admin enforcement and the required CI check are not yet on.", "Close");
  card(s, 0.5, 1.5, 2.8, 2.9, "Gate gap", "A chained add and commit bypassed the first commit gate. CI caught it. Now three scan points.", C.accent3, "lesson gate");
  card(s, 3.6, 1.5, 2.8, 2.9, "Lexical hook", "The float-for-money check matches names. A neutral name passed it, so review stays independent.", C.accent2, "lesson hook");
  card(s, 6.7, 1.5, 2.8, 2.9, "Not on yet", "Admin enforcement and the required CI check. Never say no one can bypass main.", C.accent4, "lesson gh");
}

// 13. Close
{
  const sl = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
  sl.addNotes("Evidence: the compliance-evidence skill produces a per-PR pack, so what did the AI do has one answer. Close on the one-liner and ask what the CTO's auditors would want in that pack.");
  sl.addText("What did the AI do?", { placeholder: "title" });
  txt(sl, "One evidence pack per PR: controls exercised, gate approvals, test and security results, data-handling attestation.", { x: 0.5, y: 1.5, w: 9, h: 1.0, fontSize: 20, color: C.background1, valign: "top", objectName: "evidence text" });
  txt(sl, "Speed inside controls.", { x: 0.5, y: 3.3, w: 9, h: 0.9, fontFace: "Cambria", fontSize: 44, bold: true, color: C.accent1, objectName: "closing line" });
  txt(sl, "The agent proposes, hooks and humans dispose, every step leaves evidence.", { x: 0.5, y: 4.3, w: 9, h: 0.5, fontSize: 16, color: C.accent5, objectName: "closing sub" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
