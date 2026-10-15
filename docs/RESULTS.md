# Results (generated from `results/*.json|csv`; re-run `analysis/*.py` to regenerate)

Data: 71 verifiable public tasks (rich 42, fastapi 29), 497 observational runs (7 configurations × 71),
284 runs of the context experiment E3 (4 configurations × 71). One agent (Gemma 4 31B QAT W4A16, the
official starter agent), per-task budgets 40 tool calls / 30 min / 100 turns, 12–14 concurrent agents.
All intervals are 95% task-clustered bootstrap (2,000 reps) unless stated. **All analyses are
exploratory** (no pre-registration of this paper's analyses); see LOG.md D10.

## 1. Anytime curve: share of runs resolved within k tool calls

| calls k | patch already in place | run completed |
|---|---|---|
| 10 | 8.2% [4.0, 13.3] | 1.6% [0.2, 3.8] |
| 15 | 17.5% [10.3, 24.9] | 12.9% [7.4, 19.3] |
| 20 | 24.3% [15.7, 33.0] | 20.7% [13.3, 29.0] |
| 25 | 28.8% [19.9, 37.8] | 26.0% [17.5, 34.8] |
| 30 | 31.4% [21.9, 40.6] | 29.8% [20.5, 38.6] |
| 40 (full budget) | 38.8% [28.6, 48.7] | 39.2% [28.6, 48.9] |

Share of the full-budget score already available (in place): 21% at 10 calls, **45% at 15**, 63% at 20,
74% at 25, 81% at 30. Median resolved run: 20 tool calls (p10 12, p90 40); final patch exists at call 17
(p10 8, p90 37).

### Translating calls into the official allowance (assumption-dependent)
Allowance band 4.9–6.0 min/task (LOG D6; superseded by D26-D27: the pool is 12 h over about 120 tasks = 6.0 min/task, 4.9 min is unsupported). The mapping needs seconds per tool call (LOG D5):

| s/call | band in calls | score inside band, in place | score inside band, completed |
|---|---|---|---|
| 12 (fast) | 24–30 | 28–31% | 25–30% |
| 20 (earlier assumption) | 14–18 | 16–22% | 10–18% |
| **15.6 (measured, §8)** | **18–23** | **21.5–27.2%** | **17.9–24.3%** |
| 30 (slow) | 9–12 | 6–12% | 1–5% |

At the **measured** sequential latency the agent has 55–70% of its full-budget (40-call) score
available inside the allowance. Sensitivity: across 12–30 s/call the same agent would score 1–31%, so
latency still matters, but it is now measured on 8 tasks rather than assumed. Recorded concurrent
latency was 34.6 s/LLM call (44 s on the 8 calibration tasks), 2.8–3.4× the sequential value.

## 2. Where the tool calls go (12,777 calls, 497 runs)

| Category | Share of calls |
|---|---|
| resolved: explore before first edit | 12.3% |
| resolved: edit span | 17.9% |
| resolved: after final edit (verification tail) | 5.3% |
| unresolved: gave up (agent_stop) | 21.8% |
| unresolved: call budget exhausted | 21.0% |
| unresolved: wall-clock timeout | 15.1% |
| unresolved: context overflow | 7.8% |

- 65.6% of calls are spent in runs that never resolve; **49.0% on the 32 tasks never solved** in 7 runs.
- Task classes: never solved 32, mixed 22, always solved 17.
- Verification tail is small: 15.4% of resolved-run calls, median 3 calls after the last edit.
  (Stopping at the first passing check therefore saves little.)
- Oracle routing bound: cutting the never-solved tasks at 5 / 10 / 15 calls would free 40% / 32% / 24%
  of all calls. This needs knowing in advance which tasks are unsolvable.

## 3. What predicts lateness and solvability

Deployable predictors (issue text only), leave-one-out logistic regression, target "solved at least once":
AUC **0.51** [0.38, 0.64]; with repository indicator 0.54 [0.40, 0.68] (n = 71, 39 positives).
**Issue text does not predict solvability in this sample**, so the routing bound in §2 is not
achievable with these features.

Oracle features (use the reference patch/repo; explanatory only), Spearman ρ [95% CI]:

| Feature | vs per-task resolve rate (n=71) | vs median calls-to-patch, solved tasks (n=39) | vs median tool calls, all runs (n=71) |
|---|---|---|---|
| gold-patch changed lines | −0.53 [−0.69, −0.35] | +0.14 [−0.20, 0.47] | +0.16 [−0.07, 0.37] |
| files edited | −0.36 [−0.53, −0.15] | +0.17 [−0.16, 0.42] | +0.13 [−0.08, 0.33] |
| 150-line read windows to cover edited files | −0.28 [−0.47, −0.06] | **+0.51 [0.22, 0.74]** | **+0.43 [0.22, 0.60]** |
| largest edited file, lines | −0.23 [−0.45, −0.02] | +0.51 [0.19, 0.74] | +0.44 [0.21, 0.62] |
| issue length (deployable) | +0.29 [0.07, 0.51] | −0.45 [−0.68, −0.16] | −0.31 [−0.51, −0.08] |

Fix size explains *whether* a task is solved; edit-site size in harness-window units explains *how many
calls it takes*. These are different axes.

### Replication of the window-cost → calls-to-patch result (24 screened pairs; LOG D10)
| Check | n | ρ [95% CI] |
|---|---|---|
| all observational runs | 39 | 0.51 [0.22, 0.74] |
| E3 session (same tasks, other seeds/configs) | 35 | 0.57 [0.27, 0.80] |
| fastapi only | 16 | 0.57 [0.08, 0.84] |
| rich only | 23 | 0.35 [−0.10, 0.71] |
| partial ρ, controlling patch lines + issue length | 39 | 0.51 |
Same direction everywhere; the rich-only interval includes 0. E3 reuses the same 71 tasks, so it
replicates runs, not tasks.

## 4. Retries under a fixed total budget
Expected share resolved when a total budget B is split equally across k independent attempts
(in-place semantics; independence across the 7 recorded runs is assumed):

| B (calls) | k=1 | k=2 | k=3 | k=4 |
|---|---|---|---|---|
| 20 | **24.3%** | 11.7% | 3.4% | 2.4% |
| 30 | **31.4%** | 22.3% | 13.7% | 6.0% |
| 40 | **38.8%** | 29.9% | 23.5% | 15.1% |

One long attempt beats k short ones at every budget tested (best k = 1 for B = 10…40, both
semantics). Reason: successful runs need on the order of 15–20 calls, so short attempts rarely finish.
(Earlier "pass@k" numbers, 39% → 46% for k = 2, give *each* attempt the full budget and are a
different quantity.)

## 5. Context-budget experiment E3 (time angle)
Resolved counts 23 / 22 (official budget, two seeds) vs 30 (larger input budget) and 28 (delayed
compaction). Median call at which the final patch exists, among resolved runs: 13 / 16 / 15 / 15.5.
The larger budget solved more tasks without making the solved ones faster.

## 6. Not found / negative results
- Harness-window cost does **not** predict context overflow (ρ −0.16 [−0.38, 0.07]).
- Early prompt-size trajectory does **not** predict overflow (AUC 0.50–0.58).
- Issue text does **not** predict solvability (AUC 0.51).

## 8. Sequential calibration on Kaggle L4×4 (current harness, 8 tasks, one at a time)
Notebooks `cal31b-seq`, `cal12b-seq` (LOG D19–D23). Same 8 tasks, seed 101, single-agent config.
Per-task times include ~3–4 s of subprocess-sandbox setup and verification (official containers may add more).

| Quantity | 31B | 12B |
|---|---|---|
| seconds per tool call, pooled (median; IQR) | **15.6** (14.7; 9.9–26.6) | 12.9 (15.6; 5.5–18.3) |
| seconds per LLM call, median | 12.9 | 13.9 |
| completion throughput, pooled | 28.8 tok/s | 52.4 tok/s |
| completion tokens per LLM call | 366 | 532 |
| tasks resolved (of 8) | 3 (the 3 always-solved) | 3 (the same 3) |
| context-overflow runs | **0 / 8** | **4 / 8** |
| tool calls on the 3 solved tasks | 47 | 85 |
| agent time on the 3 solved tasks | 488 s | 1,380 s |
| median tool calls, all 8 | 17 | 33.5 |

Reading (n = 8, indicative only):
- Measured 31B sequential latency (15.6 s/call, 28.8 tok/s) is close to the 20 s assumption and to a
  public notebook's 34 tok/s; the recorded concurrent sessions were 2.8–3.4× slower per call.
- **Smaller was not faster to a solution:** the 12B decodes 1.8× faster but writes longer reasoning,
  so per-call time is similar, it needs ~1.8× the tool calls and ~2.8× the time on the same solved
  tasks, and half its runs overflow the 16,384-token input ceiling (retained thoughts of 10–12k
  characters fill it within a few calls; one run overflowed after 4 tool calls).
- **Drift check:** 31B outcomes match the recorded `base_s1` on these tasks (3/8 resolved both; median
  tool calls 17 vs 14.5) and show no overflow. This is consistent with no large behavioural drift, but
  8 tasks cannot detect a modest one, and the compaction interval (5→15) change did not visibly
  matter here. The script's "drift_summary" for 12B compares a different model to recorded 31B runs
  and must not be read as drift.

## 9. Full sequential run of 31B on all 71 tasks (current harness; LOG D24/D25)
Two Kaggle 4xL4 kernels, one task at a time each, one run per task, same agent/budgets as the recorded
study. Source: `results/full31b.json`, `results/full31b_wall_curve.csv`, `figures/fig5_wall_clock_curve.png`.
Pre-stated analyses (a)-(d); (e) was added after seeing them.

| Quantity | New run (71 tasks, 1 run each) | Recorded (same 71 tasks, 7 runs each) |
|---|---|---|
| (a) share resolved | **45.1% [33.8, 56.3]** | 39.2% [29.0, 49.5] |
| paired difference, new - recorded | **+5.8 pts [+0.8, +11.1]** | |
| by recorded class: always (17) / mixed (22) / never (32) | 100% / 64% / 3% | |
| (b) completed-by-k, k = 10 / 15 / 20 / 25 / 30 / 40 | 4.2 / 14.1 / 23.9 / 29.6 / 31.0 / 45.1% | 1.6 / 12.9 / 20.7 / 26.0 / 29.8 / 39.2% |
| (c) seconds per tool call, pooled over 71 tasks | **13.3 [11.5, 15.3]** (task median 11.1) | 44 (concurrent) |
| median tool calls | 23 (mean 25.0) | 25 |
| (d) context-overflow runs | 14.1% [7.0, 22.5] (10/71) | 11.3% |
| (e) wall-clock: resolved within 3 / 4.9 / 6 / 10 / 15 min | 18.3 / **32.4 [22.5, 43.7]** / **35.2 [23.9, 46.5]** / 40.8 / 43.7% | n/a (concurrent) |

Reading:
- **Current harness is not worse than the recorded one**; the point estimate is higher (+5.8 pts, CI
  just above 0). A single run per task is a noisy outcome and the harness changed (compaction interval,
  thinking budget), so we do not attribute the difference to a cause.
- **The 8-task latency (15.6 s/call) was a little high.** Over 71 tasks it is 13.3 s/call; resolved runs
  are faster per call than unresolved ones, which matters for the next point.
- **Direct wall-clock measurement** (e): 32-35% of tasks are resolved inside the 4.9-6.0 min band,
  i.e. 72-78% of the run's own final score (45.1%). The call-based mapping (25-30% in place) was
  conservative because it applied a pooled latency to resolved runs, which take fewer, cheaper calls.
- Median task takes 4.1 min; the longest 20.3 min; no run hit the 30-minute limit.
- Caveat: sandbox is a subprocess (official containers may add overhead); the 4.9 min end of the band is unsupported (test set is about 120 tasks, pool 6.0 min/task); one run per task; first-session load time (~6-8 min) excluded.


### Per-task cap trade-off (post hoc, LOG D26; `results/full31b_cap_table.csv`)
The official rule is a pooled 12 hours for all tasks (competition overview), so a cap trades resolved
share against mean time per task. Resolved = resolved with duration <= cap (a lower bound).

| cap (min) | resolved | mean min/task | tasks in 12 h (setup excluded) |
|---|---|---|---|
| 3 | 18.3% | 2.8 | 262 |
| 4 | 29.6% | 3.4 | 212 |
| 5 | 32.4% | 3.9 | 185 |
| 6 | 35.2% | 4.3 | 169 |
| 8 | 39.4% | 4.8 | 151 |
| 10 | 40.8% | 5.0 | 143 |
| 15 | 43.7% | 5.4 | 134 |
| 20 | 43.7% | 5.5 | 131 |
| none | 45.1% | 5.5 | 131 |

## 7. Caveats that bound every claim above
0. Harness drift: the recorded sessions (Oct 2–5) predate harness changes documented on Oct 13
   (compaction interval 5→15, enforced thinking budget, protected-file stripping, three more allowed
   models; LOG D16). Behaviour of the current scorer may differ.
1. Latency: concurrent sessions; sequential seconds/call unmeasured here (largest uncertainty).
2. 71 tasks from two repositories; the 58 excluded tasks fail the reference patch in that environment
   (mostly missing test dependencies), so the sample is selective.
3. One agent, one harness; the competition allows participants to change prompts, tools and budgets.
4. "In place" ignores edits made via shell commands; "completed" ignores recoverable partial patches.
5. Exploratory analysis; the driver screen involved 24 comparisons; replication reuses the same tasks.
6. Independence across the seven recorded runs of a task is assumed in §4.
