import json, collections, sys, os, math, itertools
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
A = r"C:\Users\AbhiDS\Documents\AgentPaperTrack\agent_saw_data"
ep = list(map(json.loads, open(os.path.join(A, "data", "main2_episodes.jsonl"), encoding="utf-8")))
# comparable cells only: the official-prompt configs (same agent) -> base_s1, base_s2, none? keep base cells + all for reference
by = collections.defaultdict(list)
for e in ep: by[e["instance_id"]].append(bool(e["resolved"]))
mean = np.mean([np.mean(v) for v in by.values()])
print("tasks", len(by), "mean per-run resolve", round(mean, 3))
def pass_at_k(v, k):
    n, c = len(v), sum(v)
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)
for k in (1, 2, 3, 7):
    print(f"pass@{k} (unbiased, over 7 runs): {np.mean([pass_at_k(v, k) for v in by.values()]):.3f}")
mixed = [t for t, v in by.items() if 0 < sum(v) < len(v)]
print("tasks never solved:", sum(1 for v in by.values() if sum(v) == 0), " always solved:", sum(1 for v in by.values() if all(v)), " mixed:", len(mixed))
# time: durations of resolved vs unresolved
dr = [e["duration_s"] for e in ep if e["resolved"]]
du = [e["duration_s"] for e in ep if not e["resolved"]]
q = lambda x: np.percentile(x, [10, 50, 90]).round(0).tolist()
print("duration resolved p10/50/90 (s):", q(dr), " unresolved:", q(du))
for T in (120, 180, 240, 300, 420, 600):
    kept = sum(1 for d in dr if d <= T) / len(dr)
    saved = np.mean([max(0, d - T) for d in [e["duration_s"] for e in ep]])
    print(f"cap {T:4d}s: keeps {kept:.2f} of resolved runs; mean time saved per run {saved:.0f}s")
print("termination x resolved:", collections.Counter((e["termination"], bool(e["resolved"])) for e in ep))
print("mean duration s:", round(np.mean([e["duration_s"] for e in ep]), 0))
