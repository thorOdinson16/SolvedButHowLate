# Paper project: call-budget anytime curves for a local 4-bit coding agent

Working title: *Solved, but How Late?* Target: Kaggle "Gemma 4 Developer Agent – Paper Track"
(deadline 2026-11-12 23:59 UTC, 3,000-word Writeup).

## One-paragraph summary
From 497 recorded runs on 71 verified tasks, the agent resolves 38.8% of runs with a 40-call budget
but only 17.5% by 15 calls; a full sequential 71-task run (13.3 s per tool call) resolves 32-35% of tasks
by 6 min (the ~120-task pool average); 78% of its own 45.1% final score. Two thirds of tool calls go to runs that never resolve, retries
do not help under a fixed total budget, issue text does not predict solvability, and edit-site size in
read-window units predicts calls-to-patch. Everything is exploratory and on 71 tasks.

## Read in this order
1. `docs/RESULTS.md` – all numbers with intervals and caveats
2. `docs/LOG.md` – chronology, every decision (D1–D24), claims I withdrew
3. `paper/draft_writeup.md` – draft Writeup (Markdown); `paper/paper.tex` + `paper/paper.pdf` – LaTeX/PDF version
4. `docs/COMPUTE_PLAN.md` – whether AWS/Kaggle compute is needed (short: measure latency on Kaggle L4×4)
5. `figures/` – fig1 wall-clock curve (headline), fig2 call-count curve, fig3 where calls go, fig4 retries, fig5 window cost vs calls

## Reproduce (laptop, minutes, no GPU)
Prereqs: competition data at `../data` (tasks.jsonl, snapshots/), the public run tables at
`../agent_saw_data`, Python 3.10 with `requirements.txt`. One command:
```
bash reproduce.sh      # tables -> numbers -> replication -> sequential-run analysis -> figures -> number check
```
Verified 2026-10-14: a full re-run leaves every `results/*.json|csv` byte-identical.
The sequential-run analysis (`analysis/full_run.py`) reads per-task result files from the Kaggle kernels
(`kaggle/output_full_s0|s1/calibration/results.jsonl`); those are per-task labels and are **not**
redistributed. The aggregates they produce (`results/full31b*.json|csv`) are. The notebook builder
(`kaggle/build_calibration.py <model> <shard> <nshards>`) is included.
`analysis/exploration/` holds the quick scripts behind the discarded hypotheses (provenance only).

## Rules to respect
- Do **not** publish `derived/` or task-level labels: competition data may not be redistributed.
- Publish code and aggregate numbers only. Cite the public run-table dataset (Apache-2.0).

## Status (2026-10-14)
Pipeline re-runnable and deterministic; sequential latency **measured** on Kaggle L4×4 (31B 15.6 s per
tool call; 12B comparison; 8 tasks) and wired into the figures; citations existence-checked; draft updated.
Full 71-task sequential 31B run DONE 2026-10-14 (LOG D24/D25; RESULTS section 9; fig5).
Open: model-size claims at n>8, official-scorer overhead, writeup polish (LOG §5).
Kaggle quota used so far ≈ 3.8 of 30 GPU-hours.
