import json, collections, sys, os
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
A = r"C:\Users\AbhiDS\Documents\AgentPaperTrack\agent_saw_data"
ep = {(e["cell"], e["instance_id"]): e for e in map(json.loads, open(os.path.join(A, "data", "main2_episodes.jsonl"), encoding="utf-8"))}
calls = collections.defaultdict(list)
for c in map(json.loads, open(os.path.join(A, "data", "main2_calls.jsonl"), encoding="utf-8")):
    calls[(c["cell"], c["instance_id"])].append(c)
def auc(pos, neg):
    if not pos or not neg: return float("nan")
    p, n = np.array(pos), np.array(neg)
    return float(((p[:, None] > n[None, :]).sum() + 0.5 * (p[:, None] == n[None, :]).sum()) / (len(p) * len(n)))
ov = [k for k, e in ep.items() if e["termination"] == "context_overflow"]
print("overflow runs", len(ov), "of", len(ep))
# when does overflow happen
print("overflow at call index: median", np.median([ep[k]["n_calls"] for k in ov]), "max prompt tokens median", np.median([ep[k]["max_prompt_tokens"] or 0 for k in ov]))
# early-warning: among runs that reached call k, does prompt size at call k predict eventual overflow?
for k in (3, 5, 8):
    pos, neg = [], []
    for key, cs in calls.items():
        cs = sorted(cs, key=lambda c: c["call"])
        if len(cs) <= k: continue
        v = cs[k]["prompt_tokens"]
        if v is None: continue
        (pos if ep[key]["termination"] == "context_overflow" else neg).append(v)
    print(f"call {k}: n_pos={len(pos)} n_neg={len(neg)} AUC(prompt_tokens)={auc(pos,neg):.2f}  median pos={np.median(pos) if pos else 0:.0f} neg={np.median(neg):.0f}")
# growth-based: max single-step jump before call k
for k in (5, 8):
    pos, neg = [], []
    for key, cs in calls.items():
        cs = sorted(cs, key=lambda c: c["call"])
        if len(cs) <= k: continue
        pts = [c["prompt_tokens"] for c in cs[:k + 1] if c["prompt_tokens"]]
        if len(pts) < 3: continue
        slope = (pts[-1] - pts[0]) / len(pts)
        (pos if ep[key]["termination"] == "context_overflow" else neg).append(slope)
    print(f"slope@{k}: AUC={auc(pos,neg):.2f}")
# task-level: do same tasks overflow repeatedly?
per = collections.defaultdict(list)
for k, e in ep.items(): per[k[1]].append(e["termination"] == "context_overflow")
mult = sum(1 for v in per.values() if sum(v) >= 2)
print("tasks with >=1 overflow", sum(1 for v in per.values() if any(v)), " >=2 overflows", mult, " all 7", sum(1 for v in per.values() if all(v)))
# resolved rate among non-overflow runs vs overall
res_all = np.mean([bool(e["resolved"]) for e in ep.values()])
res_no = np.mean([bool(e["resolved"]) for e in ep.values() if e["termination"] != "context_overflow"])
print("resolve rate all", round(res_all, 3), "excluding overflow runs", round(res_no, 3))
