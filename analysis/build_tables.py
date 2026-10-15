"""Build derived/runs.csv (one row per agent run) and derived/tasks.csv (one row per task).

Sources
  - agent_saw_data/runs/<session>/<cell>/run_log.jsonl   outcome, tool/LLM calls, duration
  - agent_saw_data/data/main{2,3}_episodes.jsonl         termination, prompt tokens, compactions
  - agent_saw_data/data/main{2,3}_calls.jsonl            per-call table (edit events)
  - data/tasks.jsonl + data/snapshots/*.tgz              pre-run task features (offline)
Session main1 is excluded: its server was overloaded (95.8% of runs hit the wall clock).
"""
import ast
import math
import re
import sys
import tarfile
import collections
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, SAW, DER, jl  # noqa: E402

tasks = {t["instance_id"]: t for t in jl(DATA / "tasks.jsonl")}

# ---------------------------------------------------------------- runs
rows = []
for sess in ("main2a", "main2b", "main3"):
    for d in sorted((SAW / "runs" / sess).iterdir()):
        if not d.is_dir():
            continue
        for r in jl(d / "run_log.jsonl"):
            rows.append(dict(
                session=sess, cell=r["condition"], task=r["instance_id"],
                repo=r["repo"].split("/")[1], resolved=bool(r["resolved"]),
                status=r["status"], tool_calls=r["tool_calls"], llm_calls=r["llm_calls"],
                duration_s=r["duration_s"], patch_chars=r["patch_chars"]))
runs = pd.DataFrame(rows)
runs["group"] = np.where(runs.session == "main3", "e3", "obs")

ep = []
for f in ("main2_episodes.jsonl", "main3_episodes.jsonl"):
    ep += jl(SAW / "data" / f)
epd = pd.DataFrame(ep)[["run", "cell", "instance_id", "resolved", "termination", "max_prompt_tokens",
                        "n_compactions", "first_source_edit_call", "n_gold_source_files"]]
epd = epd.rename(columns={"run": "session", "instance_id": "task", "resolved": "resolved_ep"})
runs = runs.merge(epd, on=["session", "cell", "task"], how="left")
agree = (runs.resolved == runs.resolved_ep.astype(bool)).mean()
print(f"run_log vs episodes resolved agreement: {agree:.4f}  (n={len(runs)})")

# last / first edit call index from the per-call table (1-based ordinal)
last_edit, first_edit, n_edit = {}, {}, {}
for f, sessions in (("main2_calls.jsonl", ("main2a", "main2b")), ("main3_calls.jsonl", ("main3",))):
    for c in jl(SAW / "data" / f):
        if c.get("edit_files"):
            k = (c["cell"], c["instance_id"])
            o = c["call"] + 1
            last_edit[k] = max(last_edit.get(k, 0), o)
            first_edit[k] = min(first_edit.get(k, 10**9), o)
            n_edit[k] = n_edit.get(k, 0) + 1
runs["last_edit_call"] = [last_edit.get((c, t), np.nan) for c, t in zip(runs.cell, runs.task)]
runs["first_edit_call"] = [first_edit.get((c, t), np.nan) for c, t in zip(runs.cell, runs.task)]
runs["n_edit_calls"] = [n_edit.get((c, t), 0) for c, t in zip(runs.cell, runs.task)]
miss = runs[runs.resolved & runs.last_edit_call.isna()]
print("resolved runs with no edit event in call table:", len(miss))
# fallback: if resolved but no edit event is visible, assume the patch existed only at the end
runs["last_edit_call_f"] = runs.last_edit_call.fillna(runs.tool_calls)
runs.to_csv(DER / "runs.csv", index=False)

# ---------------------------------------------------------------- task features (pre-run)
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? ")


def patch_files(p):
    return [l[6:].split("\t")[0] for l in p.splitlines() if l.startswith("+++ b/")]


def old_lines(p):
    out, f, cur = collections.defaultdict(set), None, 0
    for ln in p.splitlines():
        if ln.startswith("--- "):
            f = None if "/dev/null" in ln else ln[4:].strip().removeprefix("a/")
        m = HUNK.match(ln)
        if m:
            cur = int(m.group(1))
            continue
        if f is None or ln.startswith(("---", "+++", "diff ", "index ")):
            continue
        if ln.startswith("-"):
            out[f].add(cur); cur += 1
        elif ln.startswith("+"):
            out[f].add(max(cur - 1, 1))
        elif ln.startswith(" "):
            cur += 1
    return out


def changed(p):
    return sum(1 for l in p.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))


trow = []
for iid in sorted(runs.task.unique()):
    t = tasks[iid]
    ps = t["problem_statement"]
    gfl = [f for f in patch_files(t["patch"]) if f.endswith(".py") and not re.search(r"(^|/)(tests?|docs?)/|test_", f)]
    ol = old_lines(t["patch"])
    flines, fnlines = [], []
    with tarfile.open(DATA / "snapshots" / f"{iid}.tgz") as tf:
        names = {m.name: m for m in tf.getmembers() if m.isfile()}
        for f in gfl:
            cand = [n for n in names if n == f or n.endswith("/" + f)]
            if not cand:
                continue
            src = tf.extractfile(names[cand[0]]).read().decode("utf-8", "replace")
            flines.append(src.count("\n") + 1)
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            best = 0
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if any(n.lineno <= l <= (n.end_lineno or n.lineno) for l in ol.get(f, ())):
                        best = max(best, (n.end_lineno or n.lineno) - n.lineno + 1)
            fnlines.append(best)
    trow.append(dict(
        task=iid, repo=t["repo"].split("/")[1],
        # --- deployable (knowable from the issue text alone)
        issue_chars=len(ps), has_traceback=int("Traceback" in ps),
        has_codeblock=int("```" in ps), n_backticks=min(ps.count("`"), 40),
        mentions_py_path=int(bool(re.search(r"[\w/]+\.py\b", ps))),
        # --- oracle (uses the reference patch / repository; explanatory only)
        patch_lines=changed(t["patch"]), n_gold_files=len(gfl),
        file_lines_max=max(flines or [0]), windows=sum(math.ceil(x / 150) for x in flines),
        func_lines_max=max(fnlines or [0]), test_patch_lines=changed(t["test_patch"])))
pd.DataFrame(trow).to_csv(DER / "tasks.csv", index=False)
print("wrote", len(runs), "runs and", len(trow), "tasks")
print(runs.groupby("group").size().to_dict(), runs.cell.nunique(), "cells")
