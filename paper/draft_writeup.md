# Solved, but How Late? A Measured Anytime Curve for a Local 4-bit Coding Agent

*Subtitle: how much of an agent's score is available early, where its tool calls go, and what a per-task cap costs under a pooled time budget*

> **DRAFT v0.3 (2026-10-14).** Numbers are final for the analyses in `results/`. Open verification
> items are listed in LOG D27. Related-work references were existence- and
> abstract-checked; full texts not read. Figures live in `figures/` (fig1 is the headline).

## Abstract

The competition studied here gives an agent a pooled 12 hours for all hidden tasks, so what matters is
how much of its capability arrives early and what a per-task time cap costs. We study the Gemma 4 31B
(4-bit) developer agent in three ways: 497 recorded runs on 71 verified tasks, a context-budget
experiment (284 runs), and a new sequential run of the same agent on all 71 tasks under the current
harness (one task at a time, Kaggle 4×L4, 13.3 s per tool call). That run resolves 45.1% of tasks
[33.8, 56.3]; 32% are resolved within 5 minutes and 35% within 6, and with about 120 hidden tasks
the pool is 6 minutes per task. Uncapped, the agent averages 5.5 minutes, leaving about 30 seconds per
task for set-up; a 10-minute cap keeps 91% of the final score and lowers the mean to 5.0 minutes. Two thirds of all tool calls (66%) are spent in runs that never resolve and
half on 32 tasks that are never solved, yet issue text does not predict which tasks these are
(leave-one-out AUC 0.51). Under a fixed total call budget one long attempt beats every split into
retries. The edit-site size in harness read-window units predicts calls-to-patch (Spearman 0.51
[0.22, 0.74], replicated) but not context overflow. We report negative results and provide code that
reproduces every recorded-run number from public tables; the sequential run is released as aggregates.

## 1 Introduction

Small local coding agents are scored by the share of issues whose hidden tests pass, but a deployment
bounds time. In this competition the rule is pooled: 12 hours for all tasks, including sandbox setup
and excluding patch validation, with optional per-task limits. The practical questions are therefore
"how early is the answer available?" and "what does a per-task cap cost?", not only "can the agent
solve it?". Public analyses of this competition study retrieval quality, harness failure modes,
behaviour traces and leaderboard noise; we ask the budget question and answer it from measured runs.

**Contributions.** (1) A measured wall-clock anytime curve and a per-task-cap trade-off table for a
sequential 71-task run, with task-clustered intervals. (2) Anytime curves in tool-call units from 497
recorded runs, which are invariant to concurrency. (3) A decomposition of where calls are spent and a
fixed-budget retry analysis. (4) A test of which task properties explain lateness and solvability,
including three negative results. (5) Open code on public run tables.

## 2 Related work *(existence and abstract-level claims verified; full texts not read)*

**Trajectory behaviour.** Failed runs are longer and more variable than successful ones, and agents
often reach the right files even when they fail (Majgaonkar et al., arXiv:2511.00197). Across 9,374
trajectories the underlying LLM matters more than the framework, and patch size alone does not explain
difficulty (Mehtiyev and Assunção, arXiv:2604.02547). File choice is too coarse to separate success
from failure; function selection and completion behaviour localize the difference (Shu et al.,
arXiv:2607.06184). **Difficulty.** Static task features predict difficulty before any run (AUC 0.863),
with patch fragmentation and repository scale the largest drivers (Al-Haque and Johnson,
arXiv:2608.18280); our fix-size result agrees, and we add a time-to-patch axis. **Harness and
context.** Context management mostly acts by preventing overflow and matters most under tight budgets
(Fan et al., arXiv:2609.20804). **Localization.** Graph-guided localization (LocAgent, Chen et al.,
arXiv:2503.09089). **Early termination.** EET (Guo et al., Findings of ACL 2026; arXiv:2601.05777)
cuts agent cost by 19–55% on SWE-bench Verified by stopping unproductive iterations using experience
from earlier runs; it targets cost at fixed success, while we measure how much score is available by
a given time and whether any deployable signal can route time. **Within this competition**, public
notebooks audit retrieval, document an output-cap/context interaction and a coupled-timeout trap, and
analyse leaderboard noise; we differ in measuring time-to-resolution directly.

## 3 Setting and data

**Agent and harness.** The competition's model (Gemma 4 31B, QAT W4A16), nine tools including three
code-graph tools, vLLM with a 32,768-token window (16,384-token input ceiling), event compaction, and
per-task budgets of 40 tool calls, 30 minutes and 100 turns in all runs we report. The official rule
is 12 hours for all tasks; the test set has "about 120 tasks", evenly split between public and private
splits and curated from private repositories (competition data page), i.e. about 6.0 minutes per task on average.

**Recorded runs.** Public per-run tables of an earlier study (Apache-2.0): 71 verifiable tasks (rich
42, fastapi 29), 7 configurations × 71 = 497 observational runs and 4 × 71 = 284 runs varying input
budget and compaction threshold. Those sessions ran 12–14 agents concurrently on one server, so their
durations are 2.8–3.4× inflated and are not used as time.

**New sequential run.** The competition's starter harness, current settings (compaction interval 15,
thinking budget), single-agent configuration and the recorded study's budgets, on Kaggle 4×L4, one
task at a time, all 71 tasks, one run each, in two kernels of 36 and 35 tasks. A separate 8-task
calibration (31B and 12B) preceded it.

## 4 Methods

**Units.** Tool-call ordinal for recorded runs; wall-clock minutes of agent time for the new run
(includes ~3–4 s of subprocess sandbox set-up and verification; excludes model load). **Semantics.**
*Completed*: resolved and finished by k calls (or t minutes), a lower bound. *In place*: the final patch
already existed in the working tree by call k, closer to the harness's patch recovery; shell-made edits
are invisible to it. **Uncertainty.** Task-clustered bootstrap, 2,000 replicates. **Cap trade-off.** For
a per-task cap c, resolved share is the share resolved with duration ≤ c, and mean time per task is
mean(min(duration, c)); tasks fitting in 12 hours is 720 / mean minutes (durations already include the measured ~3.6 s sandbox set-up).
**Retries.** A total budget B split into k equal attempts, estimated per task from recorded runs under
an independence assumption. **Driver screen.** 24 exploratory feature-outcome Spearman correlations;
the surviving result is checked within repository, in an independent session and under partial control.
**Analysis status.** The new-run analyses (resolved share, call curve, latency, overflow) were stated
before the results were seen; the wall-clock curve and cap table were added afterwards and are flagged.

## 5 Results

**Headline: the wall-clock curve (Fig. 1).** The sequential run resolves 45.1% [33.8, 56.3] of tasks,
against 39.2% [29.0, 49.5] for the recorded runs on the same tasks (paired difference +5.8 points
[+0.8, +11.1]; we do not attribute it to the harness changes). A replicate of 36 of the tasks (same model, harness, budgets; separate kernel)
resolves 41.7% against 44.4% in the first run; 33 of 36 outcomes agree (3 flips; paired difference -2.8 points [-11.1, 5.6]).
Against recorded runs on the same 36 tasks (35.3%) the two runs differ by +9.1 [2.0, 17.9] and +6.3 [-2.4, 15.1] points; their mean
is +7.7 [1.2, 15.1]. We read this as a suggestive, modest gain, with run-to-run noise of about 3 tasks in 36. Pooled latency in the
replicate is 13.5 s per tool call [11.2, 16.2] (14.8 in the first run on those tasks). Median task time is 4.1 minutes (p90 10.2, maximum 20.3; no run reached
30). Resolved within 3 / 5 / 6 / 10 / 15 minutes: 18% / 32% [23, 44] / 35% [24, 46] / 41% / 44%, so 78% of the run's final score is
available by 6 minutes, the pool average for about 120 tasks. Pooled latency is 13.3 s per tool call
[11.5, 15.3] (task median 11.1; 8-task calibration 15.6) against 44 s in the concurrent sessions.

**What a cap costs (Table 1).** Because the budget is pooled, a cap can be set without the average
changing much.

| per-task cap (min) | resolved | mean min / task | tasks that fit in 12 h |
|---|---|---|---|
| 4 | 29.6% | 3.4 | 212 |
| 6 | 35.2% | 4.3 | 169 |
| 10 | 40.8% | 5.0 | 143 |
| 15 | 43.7% | 5.4 | 134 |
| none (30 min) | 45.1% | 5.5 | 131 |

With about 120 tasks the pool is 6.0 minutes per task. Uncapped, the agent's mean of 5.5 minutes
uses 11.0 of the 12 hours and leaves 29 seconds per task for sandbox set-up, which counts against the
pool and which we could not measure. A 10-minute cap keeps 91% of the score and leaves 57 seconds per
task (10.1 hours used); a 6-minute cap keeps 78% and leaves 105 seconds (8.5 hours). The cap is
therefore a safety margin against set-up time and slower hidden tasks rather than a gain in score.

**Call-count curve (Fig. 2).** In recorded runs, in-place resolution is 8.2% at 10 calls, 17.5% at 15,
24.3% at 20, 31.4% at 30 and 38.8% at 40; 45% of the final score exists by 15 calls. The new run's
completed curve is similar (14.1% at 15, 23.9% at 20, 31.0% at 30, 45.1% at 40). Mapping calls to
minutes with the pooled latency (27 calls at 6 minutes) gives about 30% in place, against 35% measured
directly, because resolved runs use fewer and cheaper calls than unresolved ones.

**Where calls go (Fig. 3).** In recorded runs 12% of calls are exploration before the first edit, 18%
editing and 5% verification after the final edit; unresolved runs consume 22% (gave up), 21% (call
budget), 15% (timeout) and 8% (context overflow). Thirty-two of 71 tasks are never solved in seven runs
and absorb 49% of calls; an oracle cutting them at 10 calls would free 32%. A deployable predictor from
issue text has leave-one-out AUC 0.51 [0.38, 0.64], so this bound is not reachable. In the new run the
same split holds: 100% of always-solved, 64% of mixed and 3% of never-solved tasks were resolved.

**Retries (Fig. 4).** With total budgets of 20 / 30 / 40 calls, one attempt resolves 24.3% / 31.4% /
38.8% against 11.7% / 22.3% / 29.9% for two attempts; successful runs need about 17 calls to the final
patch, so short attempts rarely finish.

**What explains lateness (Fig. 5).** The number of 150-line read windows needed to cover the edited
files predicts calls-to-patch among solved tasks: ρ = 0.51 [0.22, 0.74] (n = 39); 0.57 [0.27, 0.80] in
the independent context-experiment session; 0.57 [0.08, 0.84] in fastapi and 0.35 [−0.10, 0.71] in
rich; partial ρ 0.51 controlling patch size and issue length. Patch size explains *whether* a task is
solved (ρ = −0.53 [−0.69, −0.35]) but not how many calls it takes (0.14 [−0.20, 0.47]).

**Negative results.** Window cost does not predict context overflow (ρ = −0.16 [−0.38, 0.07]);
prompt-size trajectories in the first eight calls do not predict overflow (AUC 0.50–0.58); issue text
does not predict solvability (AUC 0.51). Raising the input budget solved more tasks (23/22 to 30 of 71)
without making solved tasks faster (median final-patch call 13–16).

**Model size (indicative, 8 tasks).** The 12B model decoded 1.8× faster (52 vs 29 tokens/s) but wrote
longer reasoning, so time per tool call was similar (12.9 vs 15.6 s). On the three tasks both solved it
needed 85 tool calls and 1,380 s against 47 calls and 488 s, and four of eight 12B runs overflowed the
input ceiling versus none for 31B. Faster decoding was not faster solving here.

## 6 Discussion

For a pooled, latency-bounded evaluation, a fixed agent's score depends on how the budget is
distributed, not only on per-call speed. Our measurements say three practical things. First, most of
the score arrives early (35% of tasks by 6 minutes of a 45% total), so a moderate cap is cheap. Second,
because retries do not help at small budgets, spare time is better spent on one longer attempt than on
restarts. Third, patch complexity governs *whether* a task is solved and edit-site size governs *how
late*; these are different problems, and the absence of a deployable difficulty signal argues against
routing time by issue text. The read-window result suggests that cheaper localization (fewer windows
read before the first edit) is the lever for lateness.

## 7 Limitations

1. One run per task in the full sequential run; a 36-task replicate shows 3 outcome flips, so the +5.8-point
   difference to recorded runs is suggestive, not established.
2. 71 tasks from two repositories, a selective sample (58 public tasks fail the reference patch in the
   local environment); hidden test repositories are private.
3. Latency is measured in a subprocess sandbox and excludes model load; subprocess set-up measured at a median of 3.6 s per task (trace timestamps vs. task duration; 71 tasks, included in all durations), but the official containers' set-up is unmeasured and counts against the 12 hours.
4. The hidden test set is "about 120" tasks from private repositories, so its time distribution may
   differ from our 71 public tasks; sandbox set-up time counts against the pool and is unmeasured. We
   therefore report the cap table rather than a single allowance.
5. The recorded sessions predate documented harness changes (compaction interval, thinking budget,
   three additional permitted models); the new run uses the current starter harness.
6. One agent configuration; participants may change prompts, tools and budgets. The model-size note is
   n = 8 and indicative only.
7. Exploratory analysis with a 24-comparison screen; the replication reuses the same tasks. "In place"
   cannot see shell-made edits; retry independence is assumed.
8. The recorded-run dataset's page metadata lists no licence; its repository includes an Apache-2.0
   LICENSE file and README statement, which is what we rely on.

## 8 Reproducibility

All numbers derive from public per-run tables, competition files available to participants, and the
sequential-run result table. Code (`analysis/*.py`) rebuilds tables, curves, figures and
`results/*.json` offline in minutes on a laptop; the Kaggle notebook builder is included. Per-task
labels and task text are not redistributed (competition rules).
