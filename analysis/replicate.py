"""Replication checks for the one driver result that survived exploratory screening:
harness-window cost (read windows / gold-file size) vs time-to-patch.

Checks (all exploratory; the screening in analyze.py ran 24 tests, so we require agreement):
  R1  within-repository (rich, fastapi separately)
  R2  independent runs: session main3 (E3) re-measured per-task medians, same tasks, other seeds/configs
  R3  partial rank correlation controlling for gold-patch size and issue length
Output: results/replication.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata

sys.path.insert(0, str(Path(__file__).parent))
from common import DER, OUT  # noqa: E402

rng = np.random.default_rng(7)
runs = pd.read_csv(DER / "runs.csv")
tasks = pd.read_csv(DER / "tasks.csv").set_index("task")


def per_task(df):
    solved = df[df.resolved].groupby("task").last_edit_call_f.median().rename("calls_to_patch")
    allc = df.groupby("task").tool_calls.median().rename("tool_calls_all")
    return tasks.join([solved, allc])


def rho_ci(x, y, reps=1000):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    r = spearmanr(d.x, d.y).correlation
    bs = []
    for _ in range(reps):
        s = d.iloc[rng.integers(0, len(d), len(d))]
        if s.x.nunique() > 1 and s.y.nunique() > 1:
            bs.append(spearmanr(s.x, s.y).correlation)
    return {"n": int(len(d)), "rho": float(r), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5))}


def partial_rho(df, x, y, ctrl):
    d = df[[x, y] + ctrl].dropna()
    R = {c: rankdata(d[c]) for c in [x, y] + ctrl}
    Z = np.column_stack([np.ones(len(d))] + [R[c] for c in ctrl])
    res = lambda v: R[v] - Z @ np.linalg.lstsq(Z, R[v], rcond=None)[0]
    return float(np.corrcoef(res(x), res(y))[0, 1]), int(len(d))


out = {}
obs = per_task(runs[runs.group == "obs"])
e3 = per_task(runs[runs.group == "e3"])
for feat in ("windows", "file_lines_max"):
    for tgt in ("calls_to_patch", "tool_calls_all"):
        out[f"obs_all|{feat}|{tgt}"] = rho_ci(obs[feat], obs[tgt])
        out[f"e3_runs|{feat}|{tgt}"] = rho_ci(e3[feat], e3[tgt])
        for repo in ("rich", "fastapi"):
            s = obs[obs.repo == repo]
            out[f"{repo}|{feat}|{tgt}"] = rho_ci(s[feat], s[tgt])
        pr, n = partial_rho(obs, feat, tgt, ["patch_lines", "issue_chars"])
        out[f"partial_obs|{feat}|{tgt}|ctrl=patch_lines,issue_chars"] = {"n": n, "partial_rho": pr}
json.dump(out, open(OUT / "replication.json", "w"), indent=1)
for k, v in out.items():
    print(k, {a: round(b, 2) if isinstance(b, float) else b for a, b in v.items()})
