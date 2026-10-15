"""Main analysis. Reads derived/*.csv, writes results/results.json and results/*.csv.

Primary unit is the TOOL-CALL ORDINAL (concurrency-invariant). Wall-clock minutes are derived
only through an explicit seconds-per-call assumption (SEC_PER_CALL), because the recorded
sessions ran 12-14 agents concurrently on one vLLM server, which inflates recorded durations
relative to the sequential official scorer.

Two semantics for "solved by call k" (both lower bounds on what a hard cap would score):
  completed : resolved AND the run finished within k tool calls
  in_place  : resolved AND the final patch already existed in the working tree by call k
              (last edit event <= k). The harness recovers the working-tree diff on cutoff,
              so this is the better estimate; it cannot see edits made through run_command.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

sys.path.insert(0, str(Path(__file__).parent))
from common import DER, OUT  # noqa: E402

B = 2000
SEC_PER_CALL = {"fast": 12, "central": 20, "slow": 30}
# measured sequential latency (31B, 8 tasks, current harness) added when the calibration output exists
_cal = OUT / "calibration_cal31b.json"
if _cal.exists():
    SEC_PER_CALL["measured_31b"] = round(json.load(open(_cal))["sec_per_tool_call_pooled"], 2)
OFFICIAL_MIN = (4.9, 6.0)      # per-task allowance band, ~120 tasks in 12 h (see docs/LOG.md D6)
GRID = np.arange(0, 41)        # 40 = the observed per-task tool-call budget
RES = {}
rng = np.random.default_rng(20261013)

runs = pd.read_csv(DER / "runs.csv")
tasks = pd.read_csv(DER / "tasks.csv")
obs = runs[runs.group == "obs"].copy()
e3 = runs[runs.group == "e3"].copy()
RES["n_runs_obs"], RES["n_runs_e3"], RES["n_tasks"] = int(len(obs)), int(len(e3)), int(obs.task.nunique())


def task_curves(df, col):
    out = {}
    for t, g in df.groupby("task"):
        v = g[col].to_numpy(float)
        r = g["resolved"].to_numpy(bool)
        out[t] = np.array([np.mean(r & (v <= k)) for k in GRID])
    return out


def boot_curve(curves, reps=B):
    M = np.stack(list(curves.values()))
    n = len(M)
    bs = np.stack([M[rng.integers(0, n, n)].mean(0) for _ in range(reps)])
    return M.mean(0), np.percentile(bs, 2.5, 0), np.percentile(bs, 97.5, 0)


def curve_table(df, label):
    rows = {}
    for sem, col in (("completed", "tool_calls"), ("in_place", "last_edit_call_f")):
        est, lo, hi = boot_curve(task_curves(df, col))
        rows[sem] = (est, lo, hi)
    return rows


# -------------------------------------------------------------- 1. anytime curves
pool = curve_table(obs, "obs_all")
base = curve_table(obs[obs.cell.isin(["base_s1", "base_s2"])], "official_prompt")
c0 = curve_table(e3[e3.cell.isin(["e3_c0a", "e3_c0b"])], "e3_c0")
c1 = curve_table(e3[e3.cell == "e3_c1"], "e3_c1")
c2 = curve_table(e3[e3.cell == "e3_c2"], "e3_c2")
tab = {"k": GRID.tolist()}
for name, d in (("obs_all", pool), ("official_prompt", base), ("e3_official", c0), ("e3_larger_budget", c1), ("e3_late_compaction", c2)):
    for sem, (est, lo, hi) in d.items():
        tab[f"{name}__{sem}"] = est.tolist()
        tab[f"{name}__{sem}__lo"] = lo.tolist()
        tab[f"{name}__{sem}__hi"] = hi.tolist()
pd.DataFrame(tab).to_csv(OUT / "anytime_curves.csv", index=False)

final = pool["completed"][0][-1]
RES["final_resolve_rate_obs"] = float(final)
for K in (10, 15, 20, 25, 30, 40):
    RES[f"obs_all_in_place_at_{K}calls"] = {s: float(pool["in_place"][i][K]) for i, s in enumerate(("est", "lo", "hi"))}
    RES[f"obs_all_completed_at_{K}calls"] = {s: float(pool["completed"][i][K]) for i, s in enumerate(("est", "lo", "hi"))}
# share of the eventual (40-call) score available by k calls
RES["share_of_final_in_place"] = {str(K): float(pool["in_place"][0][K] / pool["in_place"][0][-1]) for K in (10, 15, 20, 25, 30)}
RES["share_of_final_completed"] = {str(K): float(pool["completed"][0][K] / pool["completed"][0][-1]) for K in (10, 15, 20, 25, 30)}

# official band expressed in tool calls, for each latency assumption
RES["official_band_in_calls"] = {n: [round(OFFICIAL_MIN[0] * 60 / s, 1), round(OFFICIAL_MIN[1] * 60 / s, 1)] for n, s in SEC_PER_CALL.items()}
for n, s in SEC_PER_CALL.items():
    lo_k, hi_k = int(OFFICIAL_MIN[0] * 60 / s), int(OFFICIAL_MIN[1] * 60 / s)
    RES[f"score_inside_band_{n}"] = {
        "calls": [lo_k, hi_k],
        "in_place": [float(pool["in_place"][0][min(lo_k, 40)]), float(pool["in_place"][0][min(hi_k, 40)])],
        "completed": [float(pool["completed"][0][min(lo_k, 40)]), float(pool["completed"][0][min(hi_k, 40)])],
        "share_of_final_in_place": [float(pool["in_place"][0][min(lo_k, 40)] / pool["in_place"][0][-1]),
                                    float(pool["in_place"][0][min(hi_k, 40)] / pool["in_place"][0][-1])]}

# -------------------------------------------------------------- 2. concurrency inflation
obs["lat"] = obs.duration_s / obs.llm_calls
e3["lat"] = e3.duration_s / e3.llm_calls
RES["recorded_sec_per_llm_call_median"] = {"obs": float(obs.lat.median()), "e3": float(e3.lat.median())}
RES["inflation_vs_central_assumption"] = float(obs.lat.median() / SEC_PER_CALL["central"])
resolved_obs = obs[obs.resolved]
RES["resolved_duration_s_pctiles_recorded"] = np.percentile(resolved_obs.duration_s, [10, 50, 90]).round(0).tolist()
RES["resolved_tool_calls_pctiles"] = np.percentile(resolved_obs.tool_calls, [10, 50, 90]).tolist()
RES["resolved_last_edit_call_pctiles"] = np.percentile(resolved_obs.last_edit_call_f, [10, 50, 90]).tolist()

# -------------------------------------------------------------- 3. where the calls go
by_task = obs.groupby("task").resolved.agg(["sum", "count"])
never = set(by_task[by_task["sum"] == 0].index)
always = set(by_task[by_task["sum"] == by_task["count"]].index)
obs["task_class"] = np.where(obs.task.isin(never), "never", np.where(obs.task.isin(always), "always", "mixed"))
RES["task_classes"] = {"never": len(never), "mixed": int(obs.task.nunique() - len(never) - len(always)), "always": len(always)}
tot_calls = obs.tool_calls.sum()
parts = {}
r = obs[obs.resolved]
explore = (r.first_edit_call.fillna(r.tool_calls) - 1).clip(lower=0).sum()
edit_span = (r.last_edit_call_f - r.first_edit_call.fillna(r.last_edit_call_f) + 1).clip(lower=0).sum()
tail = (r.tool_calls - r.last_edit_call_f).clip(lower=0).sum()
parts["resolved: explore before first edit"] = explore
parts["resolved: edit span"] = edit_span
parts["resolved: after final edit (verification tail)"] = tail
for term, g in obs[~obs.resolved].groupby("termination"):
    parts[f"unresolved: {term}"] = g.tool_calls.sum()
RES["calls_total_obs"] = int(tot_calls)
RES["call_shares"] = {k: float(v / tot_calls) for k, v in parts.items()}
RES["share_calls_on_never_solved_tasks"] = float(obs[obs.task_class == "never"].tool_calls.sum() / tot_calls)
RES["share_calls_unresolved_runs"] = float(obs[~obs.resolved].tool_calls.sum() / tot_calls)
RES["tail_share_of_resolved_run_calls"] = float(tail / r.tool_calls.sum())
RES["median_tail_calls_resolved"] = float((r.tool_calls - r.last_edit_call_f).median())
# oracle routing bound: cap never-solved tasks at C calls
for C in (5, 10, 15):
    saved = (obs[obs.task_class == "never"].tool_calls - C).clip(lower=0).sum()
    RES[f"oracle_cut_never_solved_at_{C}_frees_share"] = float(saved / tot_calls)

# -------------------------------------------------------------- 4. headroom: k attempts, fixed total budget
def task_p(df, col, cap):
    return df.groupby("task").apply(lambda g: float(np.mean(g.resolved.to_numpy(bool) & (g[col].to_numpy(float) <= cap))), include_groups=False)


budgets = [10, 15, 20, 30, 40]
ks = [1, 2, 3, 4]
head = {}
for sem, col in (("in_place", "last_edit_call_f"), ("completed", "tool_calls")):
    for Bt in budgets:
        for k in ks:
            p = task_p(obs, col, Bt // k).to_numpy()
            succ = 1 - (1 - p) ** k
            idx = np.arange(len(succ))
            bs = [succ[rng.integers(0, len(succ), len(succ))].mean() for _ in range(1000)]
            head[f"{sem}|B={Bt}|k={k}"] = [float(succ.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
RES["headroom_k_attempts"] = head
pd.DataFrame([{"semantics": k.split("|")[0], "budget_calls": int(k.split("|")[1][2:]), "k": int(k.split("|")[2][2:]),
               "est": v[0], "lo": v[1], "hi": v[2]} for k, v in head.items()]).to_csv(OUT / "headroom_k_attempts.csv", index=False)
best = {}
for sem in ("in_place", "completed"):
    for Bt in budgets:
        ests = {k: head[f"{sem}|B={Bt}|k={k}"][0] for k in ks}
        kb = max(ests, key=ests.get)
        best[f"{sem}|B={Bt}"] = {"best_k": kb, "est": ests[kb], "k1": ests[1]}
RES["headroom_best_k"] = best

# -------------------------------------------------------------- 5. how much of runtime is the task?
# one-way ICC(1) of log tool calls over the balanced 7-run design
g = obs.assign(lt=np.log(obs.tool_calls.clip(lower=1))).groupby("task").lt
n = 7
msb = n * g.mean().var(ddof=1)
msw = g.var(ddof=1).mean()
RES["icc_log_tool_calls"] = float((msb - msw) / (msb + (n - 1) * msw))
RES["per_task_resolve_rate_pctiles"] = np.percentile(by_task["sum"] / by_task["count"], [25, 50, 75]).tolist()

# -------------------------------------------------------------- 6. drivers of lateness (task level)
solved = obs[obs.resolved].groupby("task").last_edit_call_f.median().rename("med_calls_to_patch")
allmed = obs.groupby("task").tool_calls.median().rename("med_tool_calls_all")
rate = (by_task["sum"] / by_task["count"]).rename("resolve_rate")
T = tasks.set_index("task").join([solved, allmed, rate])
feat_dep = ["issue_chars", "has_traceback", "mentions_py_path", "patch_lines", "n_gold_files", "file_lines_max", "windows", "func_lines_max"]
drv = []
for outcome in ("resolve_rate", "med_calls_to_patch", "med_tool_calls_all"):
    for f in feat_dep:
        d = T[[f, outcome]].dropna()
        if d[f].nunique() < 2 or len(d) < 8:
            continue
        rho = spearmanr(d[f], d[outcome]).correlation
        bs = []
        for _ in range(1000):
            s = d.iloc[rng.integers(0, len(d), len(d))]
            if s[f].nunique() < 2 or s[outcome].nunique() < 2:
                continue
            bs.append(spearmanr(s[f], s[outcome]).correlation)
        drv.append({"outcome": outcome, "feature": f, "n": len(d), "rho": float(rho),
                    "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
                    "oracle": f in ("patch_lines", "n_gold_files", "file_lines_max", "windows", "func_lines_max")})
pd.DataFrame(drv).to_csv(OUT / "drivers_spearman.csv", index=False)

# -------------------------------------------------------------- 7. deployable solvability predictor (LOO)
y = (T.resolve_rate > 0).astype(int).to_numpy()
Xd = pd.DataFrame({"log_issue_chars": np.log(T.issue_chars), "has_traceback": T.has_traceback,
                   "has_codeblock": T.has_codeblock, "n_backticks": T.n_backticks, "mentions_py_path": T.mentions_py_path})
Xr = Xd.assign(is_rich=(T.repo == "rich").astype(int))
pred = {}
for name, X in (("issue_text_only", Xd), ("issue_text_plus_repo", Xr)):
    p = np.zeros(len(y))
    for i in range(len(y)):
        tr = np.arange(len(y)) != i
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500))
        m.fit(X[tr], y[tr])
        p[i] = m.predict_proba(X[~tr])[0, 1]
    auc = roc_auc_score(y, p)
    bs = []
    for _ in range(1000):
        ii = rng.integers(0, len(y), len(y))
        if y[ii].min() == y[ii].max():
            continue
        bs.append(roc_auc_score(y[ii], p[ii]))
    pred[name] = {"loo_auc": float(auc), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "n": int(len(y)),
                  "positives": int(y.sum())}
RES["solvability_predictor_loo"] = pred

# -------------------------------------------------------------- 8. E3: does the larger budget change time-to-patch?
e3r = e3[e3.resolved]
RES["e3_resolved_runs"] = {c: int(g.shape[0]) for c, g in e3r.groupby("cell")}
RES["e3_median_in_place_call_resolved"] = {c: float(g.last_edit_call_f.median()) for c, g in e3r.groupby("cell")}
RES["e3_median_tool_calls_all"] = {c: float(g.tool_calls.median()) for c, g in e3.groupby("cell")}

with open(OUT / "results.json", "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(json.dumps(RES, indent=1)[:6000])
