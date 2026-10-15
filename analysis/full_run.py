"""Analysis of the full sequential 31B run (LOG D24). Pre-stated analyses only:
(a) resolved share vs recorded, paired by task; (b) 'completed' anytime curve vs recorded on the same
tasks; (c) seconds per tool call over all tasks; (d) context-overflow rate.
Usage: python -I analysis/full_run.py <results.jsonl> [<results.jsonl> ...]  -> results/full31b.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import DER, OUT, jl  # noqa: E402

rng = np.random.default_rng(20261014)
B = 2000
KS = [10, 15, 20, 25, 30, 40]
new = pd.DataFrame([r for f in sys.argv[1:] for r in jl(f)])
n_all = len(new)
new = new[new.status == "done"].drop_duplicates("instance_id").rename(columns={"instance_id": "task"})
rec = pd.read_csv(DER / "runs.csv")
rec = rec[rec.group == "obs"]
tasks = sorted(set(new.task) & set(rec.task))
new = new[new.task.isin(tasks)].set_index("task").loc[tasks]
rec = rec[rec.task.isin(tasks)]
rate = rec.groupby("task").resolved.mean().loc[tasks]
n = len(tasks)


def boot(fn):
    idx = rng.integers(0, n, (B, n))
    v = np.array([fn(i) for i in idx])
    return float(fn(np.arange(n))), [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


res_new = new.resolved.astype(float).to_numpy()
res_rec = rate.to_numpy()
out = {"n_records": int(n_all), "n_tasks_done": int(n)}
out["resolved_new"] = boot(lambda i: res_new[i].mean())
out["resolved_recorded_same_tasks"] = boot(lambda i: res_rec[i].mean())
out["paired_diff_new_minus_recorded"] = boot(lambda i: (res_new[i] - res_rec[i]).mean())
cls = np.where(res_rec == 0, "never", np.where(res_rec == 1, "always", "mixed"))
out["resolved_by_recorded_class"] = {c: {"n": int((cls == c).sum()), "new_rate": float(res_new[cls == c].mean())}
                                     for c in ("always", "mixed", "never") if (cls == c).any()}
tc = new.tool_calls.to_numpy(float)
rr = rec.assign(done=rec.resolved)
cur_new, cur_rec = {}, {}
rec_by_task = {t: g for t, g in rec.groupby("task")}
for k in KS:
    a = ((res_new > 0) & (tc <= k)).astype(float)
    b = np.array([((rec_by_task[t].resolved) & (rec_by_task[t].tool_calls <= k)).mean() for t in tasks])
    cur_new[k] = boot(lambda i: a[i].mean()); cur_rec[k] = boot(lambda i: b[i].mean())
out["completed_curve_new"], out["completed_curve_recorded_same_tasks"] = cur_new, cur_rec
dur, calls = new.duration_s.to_numpy(float), tc
out["sec_per_tool_call_pooled"] = boot(lambda i: dur[i].sum() / calls[i].sum())
out["sec_per_tool_call_per_task_median"] = float(np.median(dur / np.maximum(calls, 1)))
out["tool_calls_median"] = float(np.median(calls))
out["tool_calls_mean"] = float(calls.mean())
out["tool_calls_recorded_median_same_tasks"] = float(rec.tool_calls.median())
err = new.error.fillna("").astype(str).str.lower()
ovf = err.str.contains("context|overflow|input token|too long").to_numpy()
out["overflow_rate"] = boot(lambda i: ovf[i].mean())
out["recorded_overflow_rate_same_tasks"] = float((rec.termination == "context_overflow").mean()) if "termination" in rec else None
out["duration_min_median"] = float(np.median(dur) / 60)
# (e) ADDED AFTER SEEING (a)-(d), not pre-stated (LOG D25): direct wall-clock curve, no call->minute mapping
wall = {}
for m in (3, 4.9, 6.0, 10, 15, 30):
    a = ((res_new > 0) & (dur <= m * 60)).astype(float)
    wall[str(m)] = boot(lambda i: a[i].mean())
out["resolved_within_wall_minutes_new"] = wall
grid = np.arange(0, 20.01, 0.5)
rows = []
for m in grid:
    a = ((res_new > 0) & (dur <= m * 60)).astype(float)
    e, ci = boot(lambda i: a[i].mean()); rows.append((m, e, ci[0], ci[1]))
pd.DataFrame(rows, columns=["minutes", "resolved", "lo", "hi"]).to_csv(OUT / "full31b_wall_curve.csv", index=False)
# (f) ADDED AFTER SEEING (a)-(e) (LOG D26): the official rule is a pooled 12 h for all tasks, so a
# per-task cap trades resolved share against mean time per task (setup time excluded, unmeasured).
caps = []
for c in (3, 4, 5, 6, 8, 10, 15, 20, 30):
    r_ = lambda i, c=c: ((res_new[i] > 0) & (dur[i] <= c * 60)).mean()
    t_ = lambda i, c=c: np.minimum(dur[i], c * 60).mean() / 60
    (re, rci), (te, tci) = boot(r_), boot(t_)
    caps.append((c, re, rci[0], rci[1], te, tci[0], tci[1], 720 / te))
pd.DataFrame(caps, columns=["cap_min", "resolved", "lo", "hi", "mean_min", "mean_lo", "mean_hi", "tasks_in_12h"]).to_csv(OUT / "full31b_cap_table.csv", index=False)
out["mean_task_minutes_uncapped"] = float(dur.mean() / 60)
out["timeout_30min_runs"] = int((dur >= 1800).sum())
(OUT / "full31b.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
