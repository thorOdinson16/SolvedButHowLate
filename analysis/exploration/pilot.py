import json, tarfile, os, re, ast, math, collections, random, sys
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\AbhiDS\Documents\AgentPaperTrack"
D = os.path.join(ROOT, "data"); A = os.path.join(ROOT, "agent_saw_data")
tasks = {t["instance_id"]: t for t in map(json.loads, open(os.path.join(D, "tasks.jsonl"), encoding="utf-8"))}
ep = [json.loads(l) for l in open(os.path.join(A, "data", "main2_episodes.jsonl"), encoding="utf-8")]
by = collections.defaultdict(list)
for e in ep: by[e["instance_id"]].append(e)

def gold_files(patch):
    return [l[6:].split("\t")[0] for l in patch.splitlines() if l.startswith("+++ b/")]
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? ")
def old_lines(patch):
    out, f, cur = collections.defaultdict(set), None, 0
    for ln in patch.splitlines():
        if ln.startswith("--- "):
            f = ln[4:].strip().removeprefix("a/") if "/dev/null" not in ln else None
        elif ln.startswith("+++ "): pass
        m = HUNK.match(ln)
        if m: cur = int(m.group(1)); continue
        if f is None or ln.startswith(("---", "+++", "diff ", "index ")): continue
        if ln.startswith("-"): out[f].add(cur); cur += 1
        elif ln.startswith("+"): out[f].add(max(cur - 1, 1))
        elif ln.startswith(" "): cur += 1
    return out

rows = []
for iid, runs in by.items():
    t = tasks[iid]
    tgz = os.path.join(D, "snapshots", iid + ".tgz")
    gfl = [f for f in gold_files(t["patch"]) if f.endswith(".py") and not re.search(r"(^|/)(tests?|docs?)/|test_", f)]
    ol = old_lines(t["patch"])
    file_lines, func_lines = [], []
    try:
        with tarfile.open(tgz) as tf:
            names = {m.name: m for m in tf.getmembers() if m.isfile()}
            for f in gfl:
                cand = [n for n in names if n == f or n.endswith("/" + f)]
                if not cand: continue
                src = tf.extractfile(names[cand[0]]).read().decode("utf-8", "replace")
                file_lines.append(src.count("\n") + 1)
                try: tree = ast.parse(src)
                except SyntaxError: continue
                ls = ol.get(f, set())
                best = 0
                for n in ast.walk(tree):
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if any(n.lineno <= l <= (n.end_lineno or n.lineno) for l in ls):
                            best = max(best, (n.end_lineno or n.lineno) - n.lineno + 1)
                func_lines.append(best)
    except Exception as e:
        print("snapshot err", iid, e)
    n = len(runs)
    rows.append(dict(
        iid=iid, repo=t["repo"].split("/")[1],
        overflow=sum(r["termination"] == "context_overflow" for r in runs) / n,
        resolved=sum(bool(r["resolved"]) for r in runs) / n,
        maxprompt=np.mean([r["max_prompt_tokens"] or 0 for r in runs]),
        issue_chars=len(t["problem_statement"]),
        patch_lines=sum(1 for l in t["patch"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")),
        n_gold=len(gfl), file_lines_max=max(file_lines or [0]), file_lines_sum=sum(file_lines),
        windows=sum(math.ceil(x / 150) for x in file_lines),
        func_lines_max=max(func_lines or [0]),
        test_patch_lines=sum(1 for l in t["test_patch"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")),
    ))
print("tasks", len(rows), "repos", collections.Counter(r["repo"] for r in rows))
print("tasks with any overflow:", sum(r["overflow"] > 0 for r in rows), " mean resolve", round(np.mean([r["resolved"] for r in rows]), 3))
print("gold file lines: median", np.median([r["file_lines_max"] for r in rows]), "p90", np.percentile([r["file_lines_max"] for r in rows], 90))
print("gold file > 150 lines (needs >1 window):", sum(r["file_lines_max"] > 150 for r in rows), "/", len(rows))
print("gold function > 150 lines:", sum(r["func_lines_max"] > 150 for r in rows))
feats = ["issue_chars", "patch_lines", "n_gold", "file_lines_max", "file_lines_sum", "windows", "func_lines_max", "test_patch_lines"]
rng = random.Random(0)
def boot(x, y, B=1000):
    idx = list(range(len(x))); vals = []
    for _ in range(B):
        s = [rng.choice(idx) for _ in idx]
        r = spearmanr([x[i] for i in s], [y[i] for i in s]).correlation
        if r == r: vals.append(r)
    return np.percentile(vals, [2.5, 97.5])
print("\nSpearman (n=71)           overflow-rate            resolve-rate")
for f in feats:
    x = [r[f] for r in rows]
    o = spearmanr(x, [r["overflow"] for r in rows]); s = spearmanr(x, [r["resolved"] for r in rows])
    bo = boot(x, [r["overflow"] for r in rows]); bs = boot(x, [r["resolved"] for r in rows])
    print(f"{f:18s} {o.correlation:+.2f} [{bo[0]:+.2f},{bo[1]:+.2f}] p={o.pvalue:.3f}   {s.correlation:+.2f} [{bs[0]:+.2f},{bs[1]:+.2f}] p={s.pvalue:.3f}")
json.dump(rows, open(os.path.join(os.path.dirname(__file__), "pilot_rows.json"), "w"))
