# Solved, but How Late?

**An anytime curve for a local 4-bit Gemma 4 coding agent under a pooled time budget**

Paper for the Kaggle competition *Google: The Gemma 4 Developer Agent, Paper Track*.
This repository holds the analysis code, aggregate results, figures and paper source.

- Paper (IEEE two-column PDF): [`paper/paper.pdf`](paper/paper.pdf), LaTeX source [`paper/paper.tex`](paper/paper.tex)
- Kaggle Writeup text (Markdown): [`paper/draft_writeup.md`](paper/draft_writeup.md)
- Every number with its interval and caveat: [`docs/RESULTS.md`](docs/RESULTS.md)
- Chronology and every decision, including claims withdrawn: [`docs/LOG.md`](docs/LOG.md)

## Question

The competition gives an agent a pooled 12 hours for all hidden tasks (about 120, so roughly
6 minutes per task on average). That makes two questions practical: how early in a run is the
answer available, and what does a per-task time cap cost?

## Main findings

All numbers are for the Gemma 4 31B QAT W4A16 agent, 71 verified tasks (rich and fastapi),
budgets of 40 tool calls, 30 minutes and 100 turns. Intervals are 95% task-clustered bootstrap.

| Finding | Result |
|---|---|
| Sequential run, all 71 tasks, one at a time on Kaggle 4xL4 | 45.1% resolved [33.8, 56.3] |
| Latency | 13.3 s per tool call [11.5, 15.3] pooled |
| Resolved within 3 / 5 / 6 / 10 / 15 min | 18% / 32% / 35% / 41% / 44% |
| Share of final score available by 6 min | 78% |
| A 10-minute per-task cap | keeps 91% of the score, mean 5.0 min per task |
| Median task time | 4.1 min (p90 10.2, max 20.3) |
| Replicate of 36 tasks | 41.7% vs 44.4%; 33 of 36 outcomes agree |
| Tool calls spent in runs that never resolve | 66% (recorded runs) |
| Issue text predicts which tasks are never solved | no (leave-one-out AUC 0.51 [0.38, 0.64]) |
| One long attempt vs splitting a fixed budget into retries | one long attempt wins at every budget |
| Edit-site size (read windows) vs calls to patch | Spearman 0.51 [0.22, 0.74]; no link to context overflow |

The study is exploratory and on 71 tasks. The +5.8 point gain of the sequential run over the
recorded runs is suggestive, not established (see limitations in the paper).

## Data

| Source | Used for | In this repo |
|---|---|---|
| Public per-run tables of an earlier study (`agent_saw_data`, Apache-2.0 LICENSE in its repository): 497 observational runs and 284 context-budget runs on 71 tasks | Call-count curves, where calls go, retries, drivers | No (cite and download) |
| Competition files (`tasks.jsonl`, repository snapshots) | Task features such as patch size and read windows | No (competition rules forbid redistribution) |
| New sequential run: per-task results of the 31B agent on all 71 tasks, two Kaggle kernels, plus a 36-task replicate | Wall-clock curve, cap table, latency | Aggregates only, in `results/` |

Per-task labels and task text are not redistributed.

## Repository layout

```
analysis/
  build_tables.py      per-run and per-task tables from the public run tables
  analyze.py           anytime curves, call decomposition, retries, driver screen
  replicate.py         replication of the read-window result
  calibration.py      latency calibration (8-task study, 31B and 12B)
  trace_latency.py     per-call latency from trace timestamps
  full_run.py          wall-clock curve and cap table from the sequential run
  figures.py           all five figures
  check_numbers.py     asserts that the numbers quoted in the paper match results/
  exploration/         scripts behind discarded hypotheses (provenance only)
figures/               fig1 wall-clock curve (headline) to fig5 window cost; card images
results/               aggregate outputs (JSON and CSV) used by the paper
kaggle/build_calibration.py   builds the Kaggle notebooks used for the sequential run
paper/                 paper.tex, paper.pdf, classic variant, Markdown Writeup
docs/                  RESULTS.md, LOG.md, COMPUTE_PLAN.md
reproduce.sh           runs the whole pipeline
```

## Reproducing

Requirements: Python 3.10, `pip install -r requirements.txt`.

```
# expects ../data (competition files) and ../agent_saw_data (public run tables)
bash reproduce.sh
```

This rebuilds the tables, recorded-run numbers, replication, figures and the number check.
The sequential-run step (`analysis/full_run.py`) reads per-task result files from the Kaggle
kernels. Those are not redistributed, so the step is skipped when they are absent and the
aggregates already in `results/` are used instead. The Kaggle notebooks are built with:

```
python kaggle/build_calibration.py <model> <shard> <nshards> [replicate-tag]
```

Everything is deterministic: a full re-run left every `results/*.json|csv` byte-identical.
A few checks and figure annotations read the private calibration files and will be partial
without them.

## Limitations in one paragraph

71 tasks from two repositories; one agent configuration; one run per task in the full
sequential run (a 36-task replicate bounds noise at about 3 tasks); latency was measured in a
subprocess sandbox, and the official containers' set-up time, which counts against the 12 hours,
was not measured; the hidden test set may be distributed differently; the analysis is
exploratory. Details are in section 7 of the paper.

## Citation

```
Solved, but How Late? An anytime curve for a local 4-bit Gemma 4 coding agent
under a pooled time budget. Kaggle, Google: The Gemma 4 Developer Agent, Paper Track, 2026.
```

## Licence

Code: [MIT](LICENSE). Paper text and figures: CC BY 4.0 (as released on Kaggle).
