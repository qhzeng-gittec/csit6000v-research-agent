"""Local web UI for the agent: ask a question about a document, watch every step, check every quote.

    python -m web.server [--host 127.0.0.1] [--port 8000] [--runs runs]

Live questions use the same LLM_* environment variables as `agent.run`. Runs saved under runs/ can be
opened and replayed step by step without any API key. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import queue
import socketserver
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agent.bench import parse_run_name, wrap_doc
from agent.llm import LLM, LLMConfig
from agent.loop import run_agent
from agent.prompts import system_prompt
from agent.textnorm import normalize, normalize_with_map
from agent.tools import Tools
from agent.trace import Trace, read_trace
from agent.verify import ELLIPSIS_RE, QUOTE_RE, Corpus, _check_quote, observed

HERE = Path(__file__).parent
STATIC = {"/": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"),
          "/app.js": ("app.js", "text/javascript")}
RUNS = Path("runs")
LIVE: dict[str, queue.Queue] = {}
TITLES: dict[str, str] = {}
MAX_BODY = 4_000_000
REPLAY_SECONDS = 20  # a replay never takes longer than this, however many steps the run had
TASK_SUFFIX = "\n\nIn your answer, refer only to the document in the file `doc.txt`. Do not employ any outside knowledge."


def quote_marks(answer: str, corpus: Corpus, tool_events: list[dict]) -> list[dict]:
    """Every `"quote" (file)` in the answer: where it is in the answer, whether it passes the verifier,
    and where each of its pieces is in the document (for click-to-source)."""
    seen, _ = observed(tool_events, corpus)
    out = []
    for m in QUOTE_RE.finditer(answer):
        spans = []
        name = corpus.resolve(m.group(2))
        if name:
            ntext, idx = normalize_with_map(corpus.files[name])
            pos = 0
            for piece in (normalize(x) for x in ELLIPSIS_RE.split(m.group(1))):
                i = ntext.find(piece, pos) if len(piece) >= 4 else -1
                if i >= 0:
                    spans.append([idx[i], idx[i + len(piece) - 1] + 1])
                    pos = i + len(piece)
        out.append({"start": m.start(), "end": m.end(), "text": [m.start(1), m.end(1)], "spans": spans,
                    "ok": not _check_quote(m.group(1), m.group(2), corpus, seen)})
    return out


def line_ranges(lines: set[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for n in sorted(lines):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def question_of(run_dir: Path) -> tuple[str, str]:
    """(question, document name) of a saved run: benchmark runs keep it in example.json, web runs in request.json."""
    for name in ("request.json", "example.json"):
        path = run_dir / name
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return str(data.get("question", "")), str(data.get("doc_name") or data.get("id") or "doc.txt")
    return "", "doc.txt"


def opening(run_dir: Path, run: str) -> dict:
    question, doc_name = question_of(run_dir)
    doc = (run_dir / "corpus" / "doc.txt").read_text(encoding="utf-8", errors="replace")
    return {"type": "open", "run": run, "question": question, "doc_name": doc_name, "doc": doc}


def result(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    answer = (run_dir / "answer.md").read_text(encoding="utf-8")
    corpus = Corpus(run_dir / "corpus")
    tool_events = [e for e in read_trace(run_dir / "trace.jsonl") if e["type"] == "tool"]
    quotes = quote_marks(answer, corpus, tool_events) if meta.get("cite") == "quote" else []
    read = line_ranges(observed(tool_events, corpus)[1].get("doc.txt", set()))
    return {"type": "done", "answer": answer, "meta": meta, "quotes": quotes, "read": read}


def list_runs() -> list[dict]:
    out = []
    for path in sorted(RUNS.glob("web/*/meta.json")) + sorted(RUNS.glob("*/*/*__*/meta.json")):
        run_dir = path.parent
        rel = run_dir.relative_to(RUNS).as_posix()
        if rel not in TITLES:
            TITLES[rel] = " ".join(question_of(run_dir)[0].split())[:200]
        m = json.loads(path.read_text(encoding="utf-8"))
        out.append({"run": rel, "exp": rel.split("/")[0], "id": m.get("id") or run_dir.name, "title": TITLES[rel],
                    "full": m.get("cite") == "quote" and bool(m.get("gate")), "arm": m.get("arm"),
                    "rep": parse_run_name(run_dir.name)[2] if m.get("arm") else 0,
                    "status": m.get("status"), "revisions": m.get("revisions") or 0, "error": m.get("error", "")})
    return out


def saved_run(rel: str) -> Path | None:
    run_dir = (RUNS / rel).resolve()
    inside = run_dir.is_relative_to(RUNS.resolve())
    return run_dir if inside and (run_dir / "trace.jsonl").is_file() and (run_dir / "meta.json").is_file() else None


def model_status() -> dict:
    try:
        cfg = LLMConfig.from_env()
    except SystemExit as e:
        return {"ready": False, "model": "", "error": str(e)}
    return {"ready": True, "model": cfg.model, "error": ""}


class LiveTrace(Trace):
    def __init__(self, path: Path, events: queue.Queue):
        super().__init__(path)
        self.events = events

    def log(self, type: str, **fields) -> None:
        super().log(type, **fields)
        self.events.put({"ts": round(time.time(), 3), "type": type, **fields})


def live_run(run_dir: Path, question: str, full: bool, cfg: LLMConfig, events: queue.Queue) -> None:
    corpus = run_dir / "corpus"
    cite, style = ("quote", "inline_strict_plus") if full else ("none", "inline")
    trace = LiveTrace(run_dir / "trace.jsonl", events)
    started = time.monotonic()
    try:
        res = run_agent(question + TASK_SUFFIX, LLM(cfg), Tools(corpus), trace, system_prompt(cite, "files", style),
                        max_steps=30, cite=cite, corpus=Corpus(corpus), gate=full)
        trace.close()
        meta = {"cite": cite, "style": style, "gate": full, "model": cfg.model,
                "wall_s": round(time.monotonic() - started, 2),
                **{k: v for k, v in asdict(res).items() if k != "answer"}}
        (run_dir / "answer.md").write_text(res.answer, encoding="utf-8")
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        events.put(result(run_dir))
    except Exception as e:  # noqa: BLE001 - report any failure to the page instead of a silent hang
        events.put({"type": "error", "message": f"{type(e).__name__}: {e}"[:500]})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def _send(self, body: bytes, content_type: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json", code)

    def _stream(self, events) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for event in events:
                self.wfile.write(b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = parse_qs(url.query)
        run = query.get("run", [""])[0]
        if url.path in STATIC:
            name, content_type = STATIC[url.path]
            self._send((HERE / name).read_bytes(), content_type)
        elif url.path == "/api/config":
            self._json(model_status())
        elif url.path == "/api/runs":
            self._json(list_runs())
        elif url.path in ("/api/run", "/api/replay"):
            run_dir = saved_run(run)
            if run_dir is None:
                return self._json({"error": "no such saved run"}, 404)
            events = [opening(run_dir, run), *read_trace(run_dir / "trace.jsonl"), result(run_dir)]
            if url.path == "/api/run":
                return self._json(events)
            paced = ("assistant", "tool", "verdict")
            steps = sum(e["type"] in paced for e in events)
            delay = min(float(query.get("delay", ["0.5"])[0]), REPLAY_SECONDS / max(1, steps))

            def replay():
                for event in events:
                    yield event
                    time.sleep(delay if event["type"] in paced else 0)

            self._stream(replay())
        elif url.path == "/api/live":
            events = LIVE.pop(run, None)
            if events is None:
                return self._json({"error": "no such live run"}, 404)

            def live():
                while True:
                    event = events.get()
                    yield event
                    if event["type"] in ("done", "error"):
                        return

            self._stream(live())
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/api/ask":
            return self._json({"error": "not found"}, 404)
        size = int(self.headers.get("Content-Length", 0))
        if size > MAX_BODY:
            return self._json({"error": "The document is too large (limit: 4 MB of text)."}, 413)
        body = json.loads(self.rfile.read(size) or b"{}")
        question, document = str(body.get("question", "")).strip(), str(body.get("document", ""))
        if not question or not document.strip():
            return self._json({"error": "Add a document and type a question."}, 400)
        try:
            cfg = LLMConfig.from_env()
        except SystemExit as e:
            return self._json({"error": f"{e} Saved runs can still be opened without a key."}, 400)
        run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{time.monotonic_ns() % 10000:04d}"
        run_dir = RUNS / "web" / run_id
        (run_dir / "corpus").mkdir(parents=True)
        (run_dir / "corpus" / "doc.txt").write_text(wrap_doc(document), encoding="utf-8")
        request = {"question": question, "doc_name": str(body.get("doc_name") or "pasted text")[:120]}
        (run_dir / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        events = LIVE[run_id] = queue.Queue()
        events.put(opening(run_dir, f"web/{run_id}"))
        threading.Thread(target=live_run, daemon=True,
                         args=(run_dir, question, body.get("system") != "plain", cfg, events)).start()
        self._json({"run": run_id})


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self) -> None:  # skip the reverse DNS lookup of the default bind (slow on some machines)
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def main() -> None:
    global RUNS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--runs", default="runs", help="directory with saved runs (and where live runs are written)")
    args = ap.parse_args()
    RUNS = Path(args.runs)
    server = Server((args.host, args.port), Handler)
    print(f"scholar-agent UI: http://{args.host}:{args.port}  (saved runs: {RUNS}/)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
