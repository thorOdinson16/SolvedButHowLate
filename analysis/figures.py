"""Figures for the writeup. Palette = the dataviz skill's documented reference palette, unmodified
(adjacent-pair validated for up to 8 slots; we use at most 5). Light surface; direct labels; one axis.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from common import OUT, FIG  # noqa: E402

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True})
R = json.load(open(OUT / "results.json"))
cur = pd.read_csv(OUT / "anytime_curves.csv")
k = cur.k.to_numpy()
_cal = OUT / "calibration_cal31b.json"
SPC = round(json.load(open(_cal))["sec_per_tool_call_pooled"], 1) if _cal.exists() else 20  # measured (LOG D23) else assumed (D5)
SPC_LABEL = "measured, sequential, 31B, 8 tasks" if _cal.exists() else "assumption"


def band(ax, lo_s=SPC):
    x = 6.0 * 60 / lo_s
    ax.axvline(x, color=INK2, lw=1.2, ls="--")
    ax.text(x + 0.6, 0.02, f"6 min pool average (~120 tasks, @{SPC:g} s/call)", ha="left", va="bottom", fontsize=8, color=INK2)


# ---- Fig 1: anytime curve
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for name, lab, col, ls in (("obs_all__in_place", "patch already in place", C[0], "-"),
                           ("obs_all__completed", "run completed", C[1], "-")):
    ax.plot(k, cur[name], color=col, lw=2, ls=ls)
    ax.fill_between(k, cur[name + "__lo"], cur[name + "__hi"], color=col, alpha=0.15, lw=0)
band(ax)
ax.text(40.5, cur["obs_all__in_place"].iloc[-1], "patch in place", color=C[0], va="center", fontsize=9, fontweight="bold")
ax.text(40.5, cur["obs_all__completed"].iloc[-1] + 0.025, "run completed", color=C[1], va="center", fontsize=9, fontweight="bold")
ax.set_xlim(0, 48); ax.set_ylim(0, 0.5)
ax.set_xlabel("tool calls used per task"); ax.set_ylabel("share of runs resolved by that point")
sec = ax.secondary_xaxis("top", functions=(lambda x: x * SPC / 60, lambda m: m * 60 / SPC))
sec.set_xlabel(f"minutes at {SPC:g} s per tool call ({SPC_LABEL})", fontsize=9); sec.spines["top"].set_visible(False)
ax.set_title("Share of runs resolved vs. tool calls used\n71 tasks, 497 runs; bands = 95% task-bootstrap CI", fontsize=10, loc="left", pad=34)
fig.tight_layout(); fig.savefig(FIG / "fig2_call_curve.png", dpi=170); plt.close(fig)

# ---- Fig 2: where the calls go
sh = R["call_shares"]
order = ["resolved: explore before first edit", "resolved: edit span", "resolved: after final edit (verification tail)",
         "unresolved: agent_stop", "unresolved: call_budget", "unresolved: timeout", "unresolved: context_overflow"]
labels = ["resolved: explore", "resolved: edit", "resolved: verify tail (5%)", "unresolved: gave up", "unresolved: call budget",
          "unresolved: time out", "unresolved: overflow"]
cols = [C[0], C[0], C[0], C[1], C[1], C[1], C[1]]
alphas = [1.0, 0.65, 0.35, 1.0, 0.75, 0.5, 0.3]
fig, ax = plt.subplots(figsize=(7.2, 2.9))
left = 0
for o, lab, c, a in zip(order, labels, cols, alphas):
    w = sh[o]
    ax.barh(0, w, left=left, color=c, alpha=a, edgecolor=SURF, linewidth=2)
    if w > 0.06:
        ax.text(left + w / 2, 0, f"{w:.0%}", ha="center", va="center", color="white" if a > 0.5 else INK, fontsize=9, fontweight="bold")
    ax.text(left + w / 2, 0.55 if order.index(o) % 2 == 0 else -0.55, lab, ha="center", va="center", fontsize=8, color=INK2)
    left += w
ax.set_xlim(0, 1); ax.set_ylim(-1, 1); ax.set_yticks([]); ax.grid(False)
ax.set_xlabel("share of all 12,777 tool calls")
ax.set_title("Recorded runs (497, 12,777 calls): two thirds of tool calls go to runs that never resolve", fontsize=10, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig3_where_calls_go.png", dpi=170); plt.close(fig)

# ---- Fig 3: k attempts under a fixed total budget
h = pd.read_csv(OUT / "headroom_k_attempts.csv")
h = h[h.semantics == "in_place"]
fig, ax = plt.subplots(figsize=(7.2, 4.0))
for i, kk in enumerate((1, 2, 3, 4)):
    d = h[h.k == kk].sort_values("budget_calls")
    ax.plot(d.budget_calls, d.est, color=C[i], lw=2, marker="o", ms=5)
    ax.text(d.budget_calls.iloc[-1] + 0.8, d.est.iloc[-1], f"{kk} attempt{'s' if kk > 1 else ''}", color=C[i], va="center", fontsize=9, fontweight="bold")
ax.set_xlim(8, 50); ax.set_ylim(0, 0.45)
ax.set_xlabel("total tool-call budget per task (split equally across attempts)"); ax.set_ylabel("expected share resolved")
ax.set_title("Recorded runs (71 tasks): splitting a fixed budget into retries does not help", fontsize=10, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig4_retries.png", dpi=170); plt.close(fig)

# ---- Fig 4: harness-window cost vs calls-to-patch (task level)
runs = pd.read_csv(OUT.parent / "derived" / "runs.csv"); tasks = pd.read_csv(OUT.parent / "derived" / "tasks.csv").set_index("task")
obs = runs[runs.group == "obs"]
y = obs[obs.resolved].groupby("task").last_edit_call_f.median().rename("y")
d = tasks.join(y).dropna(subset=["y"])
fig, ax = plt.subplots(figsize=(7.2, 4.0))
for i, repo in enumerate(("fastapi", "rich")):
    s = d[d.repo == repo]
    ax.scatter(s.windows, s.y, s=34, color=C[i], edgecolor=SURF, linewidth=1.2, alpha=0.95)
    ax.text(0.02, 0.95 - 0.07 * i, f"{repo} (n={len(s)})", color=C[i], fontsize=9, fontweight="bold", transform=ax.transAxes)
from scipy.stats import spearmanr
_r = spearmanr(d.windows, d.y).correlation
ax.text(0.98, 0.04, f"Spearman rho = {_r:.2f}  (95% CI 0.22 to 0.74, task bootstrap)", ha="right", fontsize=8.5, color=INK2, transform=ax.transAxes)
ax.set_xscale("log"); ax.set_xlabel("150-line read windows needed to cover the edited files (log scale)")
ax.set_ylabel("median tool calls until the final patch exists")
ax.set_title("Bigger edit sites take more calls to reach a patch (solved tasks only, n=%d)" % len(d), fontsize=10, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig5_window_cost.png", dpi=170); plt.close(fig)
# ---- Fig 5: direct wall-clock curve from the full sequential run (LOG D24/D25)
_w = OUT / "full31b_wall_curve.csv"
if _w.exists():
    w = pd.read_csv(_w)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(w.minutes, w.resolved, color=C[0], lw=2)
    ax.fill_between(w.minutes, w.lo, w.hi, color=C[0], alpha=0.15, lw=0)
    ax.axvline(6.0, color=INK2, lw=1.2, ls="--")
    ax.text(6.2, 0.58, "pool average, about 120 tasks (6.0 min)", ha="left", va="top", fontsize=8, color=INK2)
    ax.set_xlim(0, 20); ax.set_ylim(0, 0.6)
    ax.set_xlabel("wall-clock minutes per task (sequential, Kaggle 4xL4, 31B)"); ax.set_ylabel("share of tasks resolved by that time")
    ax.set_title("Sequential 31B run, 71 tasks, one run each: share resolved vs. minutes\nband = 95% task-bootstrap CI; final share 45.1% (one run needs 20+ min)", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig1_wall_clock_curve.png", dpi=170); plt.close(fig)
print("figures written")

