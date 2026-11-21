"""System prompts. The citation mode is the experimental variable.

Two input modes:
  files    - the product: documents are files the agent reads with tools
  context  - benchmark protocol: the document is pasted into the user message

The system prompt and the tool list are FIXED for a whole run (prefix-cache friendly):
the revision-mode rules are described here up front, and the mode is switched later by
appending a <verification> message at the end of the history.
"""

BASE_FILES = """You are a research assistant answering questions about a fixed set of papers.
The papers are plain-text files in your working directory. Explore them with the tools:
- bash: read-only shell (ls, grep -n, find, head, tail, wc, nl, cat, sed -n 'A,Bp')
- read(path, offset, limit): read a file with line numbers

Rules:
- Answer ONLY from text you have actually read in this session. Do not answer from memory.
- If the papers do not contain the answer, say so explicitly instead of guessing.
- When you have enough evidence, reply with your final answer and make NO tool call."""

BASE_CONTEXT = """You are a research assistant answering questions about the document given in the user
message (the document is named `doc.txt`).

Rules:
- Answer ONLY from that document. Do not answer from memory.
- If the document does not contain the answer, say so explicitly instead of guessing."""

_NO_CITE_FOR_ABSTAIN = " A statement that the document(s) do not contain the requested information needs no citation."

CITE = {
    "none": "",
    "line": (
        "\n- Support every factual claim with a citation of the form [file:start-end], "
        "using the line numbers shown by `read` or `grep -n`." + _NO_CITE_FOR_ABSTAIN
    ),
    "quote": (
        '\n- Support every factual claim with a verbatim quote copied exactly from the source, '
        'in the form: "exact text" (file). Never paraphrase inside the quotation marks.' + _NO_CITE_FOR_ABSTAIN
    ),
}

# Evidence-first answer format (arms A4/A5). Replaces the inline-quote rule.
EVIDENCE = """
- Final answer format. First list the passages you rely on, copied VERBATIM from the files (no
  paraphrase, no ellipsis inside the quotation marks), then write the answer using only them:
  <evidence>
  [E1] "exact text" (file)
  [E2] "exact text" (file)
  </evidence>
  <answer>
  Your answer to the user. End every factual sentence with the evidence it rests on, e.g. [E1] or
  [E1, E2]. A statement that the document(s) do not contain the requested information needs no marker.
  </answer>
- The user sees only the <answer> part, so it must be complete and readable on its own."""

# Stricter faithfulness style (arm A5): no inference beyond the text, no outside advice.
STRICT = """
- State only what the document(s) say. Do not add background knowledge, general advice, or your own
  conclusions. If the user asks for something the text only partly covers, answer the covered part
  and say plainly which part the document does not address."""

# Extra faithfulness rules (arm A8), written after reading A6's unsupported sentences on the dev split.
STRICT_PLUS = """
- Do not expand abbreviations, name entities, or add details that the text itself does not give.
- Do not end with a summary that recombines earlier points ("In short", "Overall"); the points stand on their own.
- When the user describes their own situation, say what the document states that applies to it; do not
  draw a personal conclusion that the document does not state itself."""

REVISION = """
- After you give an answer, an automatic check verifies your citations. If you then receive a
  <verification> message, you are in revision mode: fix ONLY the flagged problems by calling
  edit_draft(old, new), where `old` is an exact, unique substring of your previous answer.
  Keep everything else unchanged, and reply "Done" when finished.
  Never call edit_draft before you have given an answer."""

# kept for backwards compatibility with earlier imports
BASE = BASE_FILES


STYLES = ("inline", "inline_strict", "inline_strict_plus", "evidence", "evidence_strict", "plain_strict_plus")


def system_prompt(cite: str, mode: str = "files", style: str = "inline") -> str:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    if style.startswith("plain") != (cite == "none") and style != "inline":
        # inline_*/evidence* build on verbatim quotes; plain_* are the same rules without any citation
        raise ValueError(f"style {style!r} does not go with cite={cite!r}")
    if cite not in CITE:
        raise ValueError(f"cite must be one of {sorted(CITE)}")
    if mode not in ("files", "context"):
        raise ValueError("mode must be 'files' or 'context'")
    base = BASE_FILES if mode == "files" else BASE_CONTEXT
    lead = EVIDENCE if style.startswith("evidence") else CITE[cite]
    rule = lead + (STRICT if "strict" in style else "")
    rule += STRICT_PLUS if style.endswith("_plus") else ""
    return base + rule + (REVISION if cite != "none" else "")
