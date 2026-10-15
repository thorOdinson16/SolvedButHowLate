# Work log and decision record

Everything done on this project and every decision taken, in order, including mistakes and
reversals. Dates are the session dates (2026-10-12 to 2026-10-13). "Claude" = the assistant working
with the user.

## 0. Context

- **Goal:** submit a paper to *Google – The Gemma 4 Developer Agent Paper Track* (Kaggle).
- **Deadline:** 2026-11-12 23:59 UTC. Writeup limit 3,000 words. Criteria (equal weights, 0–5):
  Novelty, Quality (generalization), Relevance, Verifiability, Clarity.
- **Prizes:** Best Paper $15k, Best New Resource $10k, Best New Application $10k.
- **User constraints:** paper track only (not the prediction leaderboard); has an AWS account with a
  G/VT on-demand quota of 8 vCPUs and $100 credit; laptop = RTX 5070 Laptop (8 GB), 31 GB RAM,
  Windows 11, Docker + WSL2 working; improvement-on-existing-work is acceptable, not only "unique" ideas.

## 1. Chronology

| # | What | Outcome |
|---|---|---|
| 1 | Fetched the Kaggle paper-track page | Only the title came back: Kaggle pages are JavaScript-rendered |
| 2 | User pasted the paper-track text | Got track rules, topics, rubric, prizes |
| 3 | Wrote `fetch_competition.py` (API + Playwright) and ran it | Rendered Overview/Data/Rules text for both competitions; API part skipped (no Kaggle credentials) |
| 4 | Read main-competition Overview/Data/Rules | Learned harness, tools, 31B W4A16 model, 129 public tasks, ~120 hidden |
| 5 | User downloaded the 20 GB dataset; tested and extracted with 7-Zip | 524 files, integrity OK, 20.9 GB at `data/` |
| 6 | Read `HARNESS_README.md`, `sample_submission/`; profiled tasks, graphs, embeddings | See "Data facts" below |
| 7 | Checked hardware/software (laptop) and AWS quota screenshots | 8 GB VRAM cannot run the 31B model; 8 vCPU quota allows one 8-vCPU GPU instance |
| 8 | Read ~14 public paper-track notebooks | Field is more developed than assumed; see D2 |
| 9 | User added the "What the Agent Saw" dataset (`archive.zip`) | Extracted to `agent_saw_data/`; read its full paper |
| 10 | Pilot tests on the candidate hypotheses | See D3–D5 |
| 11 | Built this project (`paper_project/`) | Tables, analysis, figures, draft |

### Data facts established (not assumptions)
- 129 tasks (fastapi 67, rich 48, requests 13, httpx 1). Gold patches: median 1 file, 12 changed lines.
- Graphs: 127 unique files (task-named hard links collapsed in the zip; map by `<repo>_<base_commit>`),
  median 3,250 nodes, **only `calls` edges** (README promises more), node text = source.
- Embeddings: 256-d float32 per node, keys match graph node ids 1:1, not unit-normalized.
- `search_similar_code` does lookup by symbol name, not natural language (README §6.3).
- Public outcomes dataset: 71 verifiable tasks (rich 42, fastapi 29) × 7 observational runs (497),
  plus a 4-condition context experiment E3 (284 runs). Budgets per run: 40 tool calls, 30 min, 100 turns.
  **Sessions ran 12–14 agents concurrently on one vLLM server on 4×L4** (RUNS.md).

## 2. Decisions

**D1. Paper track only; prize-agnostic, quality-first.** The user is not entering the leaderboard.
No effort went into agent engineering.

**D2. Rejected "audit whether graphs/embeddings help localization" as the core question.**
*Why:* reading the public Code tab showed at least six notebooks already doing this
(`gemma4-localization-oracle` implements gold-node labelling and Recall@k almost exactly as I had
planned; BudgetGraph, GraphFault, Found Is Not Fit do file-level retrieval audits with perturbation
controls). *Correction:* I had earlier called this plan "safe and feasible" without checking prior
work; that was an error of process, now fixed by reading before committing.

**D3. Tested my own next idea (harness-unit cost → context overflow) before building on it.**
*Result (71 tasks, per-task overflow rate over 7 runs):* Spearman ρ(overflow, #150-line windows)
= −0.16 [−0.38, +0.07]; ρ(overflow, file size) = −0.22. Wrong sign, CIs touch 0. **Hypothesis refuted.**
Kept as a reported negative result.

**D4. Tested overflow early-warning from prompt-size trajectories.** AUC 0.50–0.58 at calls 3–8;
overflow occurs late (median call 15, ~14.2k tokens, a cliff next to the 16,384 input ceiling).
**Dropped.**

**D5. Primary unit changed from seconds to tool calls.** *Why:* I noticed the recorded durations come
from sessions with 12–14 concurrent agents sharing one server, so they are inflated relative to the
sequential official scorer. My earlier statement "median solved run = 13 minutes vs. a 5-minute
allowance" was therefore **confounded and is withdrawn**. Tool-call ordinals are invariant to
concurrency. Minutes are derived only through an explicit seconds-per-call assumption with a
sensitivity range (12 / 20 / 30 s). Central 20 s/call comes from ~19.5 s/call in the sequential traces
of one public notebook (two tasks I read directly); the recorded concurrent latency is 34.6 s/call
(1.7× inflation). **This assumption is the largest uncertainty in the paper.**

**D6. Official allowance band 4.9–6.0 minutes/task.** 12 h / ~120 tasks = 6.0 min including startup;
4.9 min is the lower end quoted by a public notebook that accounts for startup and overage. I did not
verify the harness code; the band is an input, not a result, and all headline claims are stated at
all three latency assumptions.

**D7. Two "solved by call k" semantics, reported together.**
*completed* (finished and resolved within k calls) is a pure lower bound; *in place* (final patch
already in the working tree by call k, last edit event ≤ k) is closer to what the harness would
score because the README says unsubmitted working-tree patches are recovered. In-place cannot see
edits made through `run_command`, so it is also not exact. Both are shown; neither is called "the" score.

**D8. Uncertainty by task-clustered bootstrap (2,000 reps), never run-level.** Runs of one task are
not independent (ICC of log tool calls = 0.50; 49/71 tasks have identical outcomes in all 7 runs).

**D9. Session main1 excluded.** Its server was overloaded and 95.8% of runs hit the wall clock
(per the dataset's own preregistration). Its durations/outcomes are not comparable.

**D10. Treated the driver screen as exploratory and demanded replication.** The screen tested 24
(feature × outcome) pairs, so a single ρ is not trusted. The surviving result (read-window cost vs
calls-to-patch) had to hold: within each repository, in the independent E3 runs (same tasks, other
seeds/configs; *not* new tasks), and under partial rank correlation controlling patch size and issue
length. It held in all (see RESULTS.md). It is still 71 tasks from two repositories.

**D11. Split features into "deployable" vs "oracle".** Gold-patch size, files edited and read-window
cost use the reference patch/repo, so they *explain* difficulty but cannot be used to route work at
run time. Issue-text features are deployable. Only deployable features were used in the solvability
predictor (D12).

**D12. Reported the negative result on solvability prediction.** Leave-one-out AUC from issue text
alone is 0.51 [0.38, 0.64]. I considered tuning features/regularization until it passed; I did not,
because with n = 71 and 39 positives that would be fitting noise. The result is reported as-is.

**D13. Do not publish per-task labels or task text.** Competition rules (2.4.b, as quoted by the
public dataset's README) forbid redistributing competition data. The project publishes code and
aggregate numbers only. `derived/` is local working data and must not be uploaded.

**D14. No AWS resources were launched.** No AWS credentials exist on this machine, and, more
importantly, on analysis the most valuable remaining measurement (sequential seconds/call under the
official 4×L4 setup) is better obtained on a free Kaggle L4×4 notebook than on EC2 (see
`docs/COMPUTE_PLAN.md`). The user authorized AWS use; it has not been needed.

**D15. Palette.** Used the dataviz skill's documented reference palette unmodified (adjacent-pair
validated there). Did not re-run the validator script; recorded as an unverified-by-me assumption.

**D16. (2026-10-13, after the main analysis) The harness changed after the recorded sessions.**
Using the Kaggle CLI I found `HARNESS_README.md` on the competition page is 55,940 bytes (dated
2026-10-13) vs. 49,356 bytes in the copy downloaded earlier; `tasks.jsonl` (SHA-256 prefix E4B3FD60F69DBC2B)
and the Dockerfiles are byte-identical. Diff of the docs (saved in `harness_update/`) shows:
- **four permitted base models** now (31B, 12B, E4B, E2B, all QAT W4A16), not only 31B;
- **compaction_interval 5 → 15**; **gpu_memory_utilization 0.80 → 0.90**;
- thinking budget now **enforced** via vLLM `ThinkingTokenBudgetLogitsProcessor`, `seed` forwarded;
- dynamic LoRA right-sizing; protected test/config files **stripped** from patches (not just reset);
- Phase-2 pytest timeout fixed at 300 s; graph edge type is lowercase `calls`.
*Consequences:* (a) the recorded sessions (2026-10-02..05, swegemma 0.2.7) may not match the current
scorer's per-call latency and compaction behaviour, so absolute calls-to-minutes conversions are even
less certain, which strengthens the case for calibrating on the current harness; (b) smaller models
make *model size vs. speed* a real, scoreable axis, and the anytime-curve method applies directly to
12B/E4B/E2B. The dataset's pre-registered 12B replication (E5) was still queued at last record.
*Decision:* no change to the analysis already done; add a limitation and make calibration use the
current harness. I did **not** diff the code, only the documentation, so behavioural differences are
inferred from the README text.

**D17. Kaggle credentials handling (2026-10-13).** The user placed a token in
`AgentPaperTrack/.env` as `KAGGLE_API_TOKEN` and instructed me to load it without printing or reading it.
I never displayed or opened the file contents (Test-Path, then a loader that sets process-level env vars;
only the variable *name* was echoed). Output from CLI calls is redacted for `KGAT_…` patterns. The
Python 3.10 `kaggle` package (1.7.4.5) cannot use this token format, so a separate venv
(`.venv-kaggle`, Python 3.12, kaggle CLI 2.2.4) was created. `.gitignore` now excludes `.env`,
`.venv-kaggle/`, `derived/`, `agent_saw_data/`, `data/`. Auth was verified by listing competition files
(read-only). Nothing was pushed, downloaded beyond two small files, or run on Kaggle compute.

**D18. Local GPU vs Kaggle GPU.** The harness packages (`swegemma`, `adk-submission`,
`adk-eval-core`) are not on PyPI; they exist only in the competition's wheelhouse dataset
(`metric/gemma-4-developer-agent-wheelhouse`, updated 2026-10-12). So harness-faithful runs need
Kaggle. The local RTX 5070 (8 GB, visible in WSL2) cannot hold the 31B model and a homemade harness
would not be comparable to official results. Local GPU role: development and pilots only.
Quota seen by the user: 30 GPU h; the competition page says L4×4 counts double (~15 effective h).

**D19. Calibration notebook (built, not pushed).** `kaggle/build_calibration.py` →
`kaggle/notebooks/cal31-seq/`. Base = the competition's pinned "Getting Started" notebook (pulled to
`kaggle/official_starter/`), whose install/model/vLLM/evaluator cells run the *current* harness
settings (compaction_interval=15, gpu_memory_utilization=0.90, scheduler_reserve_full_isl=False).
I first tried the previous study's builder; it hardcodes the old compaction interval (5) and its
agent configs are not in the public dataset, so I abandoned it for the official starter.
Modifications, all deliberate:
- M1 agent = single LlmAgent, 9 tools, no LoRA adapters, no analyzer sub-agent, official sample
  prompt/sampling (matches the recorded study's preregistered agent so outcomes are comparable);
  *assumption:* the sample_submission prompt equals "the official starter prompt" the study used.
- M2 budgets 40 calls / 30 min / 100 turns / 120 s command timeout (recorded study); the sample's
  own eval_config (10 calls / 1 min) is a smoke-test value.
- M3 8 fixed tasks, one at a time (3 always-solved, 3 mixed, 2 never-solved by recorded outcome;
  SHA-256 order within class; rich_3894, fastapi_13537, rich_3905, rich_3278, rich_4079, rich_3180,
  fastapi_15661, fastapi_15280); no new launches after 150 min.
- M4 per-task JSONL log + traces packed for download.
- Model name set explicitly to 31B (the starter defaults to 12B).
Goals: (a) sequential seconds per tool/LLM call under the current harness; (b) drift check: same
seed (101) and tasks as recorded condition `base_s1`, so outcome/call-count differences indicate
harness drift. With n = 8 the drift check is only indicative.
Expected cost (estimate, not measured): ~2 h wall typical, ≤ 3.3 h worst case ≈ 4–6.5 quota-hours.

**D20. Safeguards and variants (2026-10-13, before the user went AFK).** Builder now takes the model
as an argument and emits `notebooks/cal31b-seq` (31B) and `notebooks/cal12b-seq` (12B); the earlier
`cal31-seq` output was deleted to avoid pushing a stale notebook. Both contain a 4-hour watchdog that
packs results and exits (a hung vLLM/evaluator cannot burn more than ~4 h of wall time); both were
parse-checked cell by cell. **Neither has been pushed.** The user's recollection of a ~6 h per-session
limit is unverified; previous sessions ran 10.1 h (main1) and 6.3 h (main3) on this competition, so the
limit is not 6 h there, and these runs are bounded at ~4 h regardless.

**D21. Kaggle runs launched (2026-10-13 18:09 local) and citation check.** The user, going AFK for
3–4 h, authorized maximum use of Kaggle and local compute with the constraint that RAM/disk must not
crash. Local headroom at launch: 14.3 GB free RAM of 31.4, 175.8 GB free disk. Pushed
`abhids123/g4-latency-calibration-31b-seq` and `…-12b-seq` (both QUEUED), watched by
`kaggle/monitor.ps1` (status transitions in `kaggle/status_log.txt`; token loaded from `.env`, never
printed). Quota arithmetic: two runs × ≤4 h wall × 2 (L4×4 weighting) ≤ 16 quota-h of 30. Not pushed:
E4B/E2B (held back to stay inside quota and see 31B/12B outcomes first).
Citations checked by web search: LocAgent (ACL 2025, arXiv:2503.09089), Majgaonkar et al.
(2511.00197), Mehtiyev & Assunção (2604.02547), Shu et al. (2607.06184), Fan et al. (2609.20804),
Al-Haque & Johnson (2608.18280, ESEM 2026) all exist with matching titles/authors. Only abstracts or
secondary summaries were read; draft wording is limited to what those support. Finding to
note: [Al-Haque & Johnson] report patch fragmentation among the largest predictors of difficulty,
which makes our fix-size/solvability result confirmatory rather than novel.

**D22. First Kaggle attempt failed (v1, 18:09–18:25) and was fixed.** Both kernels ended in ERROR
within ~8 min of GPU time each. Log (`kaggle/output_31b/*.log`) shows the environment is fine:
wheelhouse installed in 53 s, the 31B model started on 4 GPUs (tp=4) in ~6 min (461 s after notebook
start), and the evaluator was constructed. The failure was my own: `NameError: GRAPH_DIR`, defined in
the starter's code-graph demo cell that I had dropped. Fix: define `GRAPH_DIR`/`EMBEDDINGS_DIR` in the
run cell. I also added a static undefined-name check (pyflakes over the concatenated cells) before
re-pushing; it finds none other than a guarded `server_instance`. v2 of both kernels pushed 18:25.
Lesson: dropping starter cells silently removes variables; check dependencies with a linter before
spending quota. The monitor script's log writes also collided with a `tail -f` on the same file on
Windows; the new monitor polls the CLI directly and holds no shared file.
Cost of the failed attempt: ≈ 2 × 8 min of L4×4 wall time ≈ ≤ 0.6 quota-hours (estimate).

**D23. Calibration results (v2 kernels, both COMPLETE 19:22–19:23).** 31B: ~46 min notebook wall
(≈8 min install+model load, 38 min for 8 tasks); 12B ~53 min. Quota used ≈ (46 + 53 + 16 failed) min ×
2 ≈ 3.8 h of 30. Outputs in `kaggle/output_31b|12b/` (traces, results.jsonl, logs), analysed by
`analysis/calibration.py` and `analysis/trace_latency.py` (results/*.json).
Decisions made on seeing the data:
- **Measured sequential latency replaces the 20 s assumption** in the pipeline (`analyze.py` reads
  `results/calibration_cal31b.json`; figure axis relabelled "measured"). Value used: pooled
  15.6 s per tool call (31B). Sensitivity values 12 and 30 s are kept in the tables.
- **The calibration script's "drift_summary" is only valid for 31B.** It compares the notebook's
  outcomes to recorded 31B runs; for the 12B notebook it compares different models, so I did not use
  the 12B drift output and said so in RESULTS §8.
- **Not over-reading n = 8.** The 12B/31B contrasts (overflow 4/8 vs 0/8; 2.8× time on the same 3 solved
  tasks) are reported as indicative; both models solved exactly the three always-solved tasks.
- **Did not launch E4B/E2B or a larger run.** The remaining questions (drift detection, model-size
  axis with real power) need ≥ 30–70 tasks per model; at ~40–50 min per 8 tasks plus ~8 min load that is
  ~4–6 h wall per model for 71 tasks, ~8–12 quota-hours each. That is a decision for the user
  (quota 30 h; ~3.8 h used), not something to spend unattended.
Harness note: the `duration_seconds` the evaluator records already includes sandbox setup and
verification (only ~3–4 s per task here), unlike the README's description of an agent-only clock.

### D24 (2026-10-14) Full sequential run of 31B on all 71 tasks (user: "go ahead")
- **What:** `build_calibration.py <model> <shard> <nshards>` now builds a sharded full run. All 71 tasks
  are sorted by SHA-256 of the id and dealt alternately into 2 shards (36 + 35), so each shard is a
  random mix and a deadline truncation would be unbiased. Same agent, budgets (40 calls / 30 min / 100
  turns / 120 s), starter harness cells and compaction_interval=15 as D19. Kernels
  `abhids123/g4-full-31b-s0of2` and `-s1of2`, pushed 2026-10-14, one task at a time inside each.
- **Why two shards in parallel:** each is still sequential (no shared server), so per-call latency is
  not contaminated; wall time halves. Quota cost is the same either way (L4x4 counts double).
- **Corrected estimate:** the earlier "~3.5-4 h" assumed one kernel; one kernel would be ~6 h
  (8 tasks took ~40-50 min). Two shards: ~3-3.5 h each, ~10-12 quota-hours total of ~26 remaining.
- **Guards:** stop launching tasks after 270 min, watchdog packs results and exits at 5 h; results
  appended per task to `calibration/results.jsonl` so a partial run is still usable.
- **Pre-stated purpose and analysis (before seeing results):** (a) fraction resolved vs recorded 38.8%
  (task-level paired comparison, McNemar-style, with the caveat that 1 run per task is a noisy
  measurement); (b) anytime curve from the new runs vs recorded curve; (c) sec/tool-call distribution
  over 71 tasks vs the 8-task estimate; (d) context-overflow rate. No other analysis is planned.

### D25 (2026-10-14) Full-run results and what changed
- Both shards completed (36 + 35 tasks, 71/71 done, ~3.5 h wall each, no failures; ~10 quota-hours;
  Kaggle quota page afterwards: 12 h 17 m of 30 h left, i.e. ~17.7 h used; the two shards cost ~14 h, about 2x wall time because L4x4 bills double, so my ~10 h estimate was low). Numbers: RESULTS section 9.
- **Added after seeing (a)-(d): direct wall-clock curve (e).** Reason: median task took 4.1 min, which
  made the call->minute mapping unnecessary. Flagged as post hoc; it uses no new data, only the
  recorded `duration_s`.
- **Headline revised:** within the 4.9-6.0 min band 32-35% of tasks are resolved (72-78% of the run's
  own 45.1%), replacing the mapped 21.5-27.2% (call-based, 8-task latency). The older number is kept as
  the conservative alternative in RESULTS section 1.
- **Not claimed:** the +5.8 pt improvement over recorded runs is not attributed to harness changes
  (1 run/task; unknown run-to-run variance for new runs).
- **Consequence:** a second full 71-task seed (~14 h) no longer fits in the remaining 12.3 h. Options: none, or a half-size seed (~7 h) on a random half of the tasks.
- Raw outputs in `kaggle/output_full_s0|s1` (traces, results.jsonl); not for redistribution.

### D26 (2026-10-14) Allowance check, cap table, draft v0.3, reproducibility
- **Allowance (item 3):** the competition overview states the rule: "a limit of 12 hours to submit
  patches for all tasks, inclusive of sandbox setup time, but excluding time for patch validation. You
  may, but are not required, to set per-task time limits in eval_config.yaml." So the budget is
  **pooled**, not a per-task cap. The 4.9-6.0 min "band" is only 12 h / (120-147 tasks); the number of
  hidden tasks is not stated in anything we hold. The harness README's 60-min session default and the
  sample's 1-min value are per-session defaults, not the allowance. Consequence: the paper no longer
  presents 4.9-6.0 as "the allowance"; it reports the wall-clock curve plus a cap trade-off table and
  labels task count [VERIFY].
- **Cap table (post hoc):** added after (a)-(e). Mean uncapped task time 5.5 min -> ~130 tasks in 12 h
  before setup. A 10-min cap keeps 90% of the score for 9% less time.
- **Draft v0.3:** restructured around the wall-clock curve; figures renumbered (fig1 = wall-clock,
  fig2 call curve, fig3 where calls go, fig4 retries, fig5 window cost); ~2,150 words (limit 3,000).
- **Reproducibility (item 4):** `reproduce.sh`, `requirements.txt`, `analysis/check_numbers.py`; full
  re-run verified byte-identical. Per-task result files stay private; aggregates are public.
- **Not done / still open:** hidden task count; official sandbox set-up time; run-to-run variance.

### D27 (2026-10-14) Closing the two caveats: [VERIFY] items and end-to-end read
- **Hidden task count (closed):** the competition data page says "There are about 120 tasks in the test
  set, evenly divided between the public and private splits ... curated from a set of private
  repositories." So the pool is ~6.0 min/task. The 4.9 min figure (147 tasks) has no support and is
  dropped; "4.9-6.0" now appears only in RESULTS section 1's historical sensitivity table.
- **Consequence:** at ~120 tasks the uncapped agent (5.5 min mean) uses 11.0 of 12 h, leaving ~29 s per
  task for set-up that counts against the pool and is unmeasured; a 10-min cap leaves ~57 s, a 6-min cap
  ~105 s. The cap is a safety margin, not a score gain; the draft says so.
- **Dataset licence (closed):** `agent_saw_data/LICENSE` is Apache-2.0 and README section "License"
  says so; the Kaggle page metadata "Unknown" is just missing metadata.
- **Read-through:** fixed a duplicated "i.e.", an abstract claim that overstated reproducibility (the
  sequential-run per-task files are private), and the stale "VERIFY" markers.
- **Still genuinely open:** official sandbox set-up time; whether the private tasks resemble the 71
  public ones in duration; run-to-run variance; full-text reading of cited papers.

### D28 (2026-10-14) LaTeX version
- `paper/paper.tex` (article class, MiKTeX pdflatex, 7 pages, no undefined refs) mirrors draft v0.3 with
  figures from `figures/`. Build: `cd paper && pdflatex paper.tex` (twice). The Markdown draft stays the
  source for Kaggle's Writeup editor; keep the two in sync by hand.
- Layout revised (same day): serif body, sans headings, key-results box, subsections, numeric tables
  (time table, cap table with slack column, window-cost table), running header; 9 pages. Fig. 2 now
  marks 6 min at 15.6 s/call instead of the 4.9-6.0 strip. "91%" (not 90%) is the 10-min-cap share
  of the final score (40.8/45.1 = 90.6%).
- User asked for classic LaTeX: `paper/paper.tex` is now plain `article`, 10pt, two-column, Computer
  Modern, black headings, full-width figures (6 pages). The styled report version is kept as
  `paper/paper_styled.tex`.
- User asked for IEEE double-column: `paper/paper.tex` is now `IEEEtran` (conference mode), 5 pages,
  Index Terms, roman-numbered sections, full-width figures. Plain two-column version kept as
  `paper/paper_classic.tex`, report-style as `paper/paper_styled.tex`.
- Fig. 1 now marks 6.0 min (pool average, ~120 tasks) as a dashed line instead of the 4.9-6.0 strip.
- Bibliography entries describe the cited papers by arXiv id and a short topic note; full titles/authors
  of the non-verified ones still need to be filled from the arXiv pages before final submission.

## 3. Statements I made earlier that turned out wrong or weaker

| Earlier claim | Status |
|---|---|
| Localization audit is "safe and feasible" | Superseded: already heavily covered (D2) |
| Harness-window cost predicts overflow | Refuted by pilot (D3) |
| "Retries help a bit (39→46%)" | True only when each retry gets the full budget. Under a *fixed total* budget, one long attempt beats k short ones at every budget tested (RESULTS.md §4) |
| "Median solved run takes 13 min vs 5 min allowed" | Withdrawn: concurrency-confounded (D5) |
| Routing time by predicted solvability is promising | Oracle bound is large, but the deployable predictor has no signal (D12) |

## 4. Files
See `README.md`. Exploration scripts that produced D3/D4 and the early headroom numbers are kept in
`analysis/exploration/` for provenance (they are exploratory, not the final pipeline).

## 5. Open items / next steps
1. Calibrate seconds-per-tool-call under sequential official hardware (Kaggle L4×4 notebook).
2. Confirm the per-task allowance by reading the scorer's time accounting, if exposed.
3. Related-work citations existence-checked (incl. EET 2601.05777, 2026-10-14); full texts not read.
4. Decide whether to add a second outcome source (own runs) for independence.
5. Re-check the prior-work landscape on the Code tab before submitting (it changes daily).

## D29 — Second sequential run (replicate), setup-time check, bibliography (2026-10-15)
- Launched replicate of shard 0 (36 tasks, same 31B/harness/budgets/order) as `abhids123/g4-full-31b-s0of2-r2`
  (`build_calibration.py <model> 0 2 r2`). Purpose: run-to-run variance and a paired same-harness check of the
  +5.8 pt difference to recorded runs. Half-size by design (quota: ~12 h left, full seed does not fit).
- Setup time: per-task `duration_s` minus last trace `elapsed_s` has median 3.6 s (n=71); inter-task gap in
  results.jsonl ~0.06 s. So subprocess set-up is already inside all durations. Official-container set-up remains unmeasured.
- Bibliography: titles/authors checked against arXiv API; two descriptions were wrong (Shu = TraceProbe diagnostics,
  Fan = harness-design component study); the claims in the text were re-checked against abstracts and stand.
- D29 result (replicate `-r2`, 36 tasks, complete, no failures): resolved 41.7% vs 44.4% in run 1; 33/36 outcomes agree
  (both 14, only-run1 2, only-run2 1, neither 19). Paired r2-r1 -2.8 pts [-11.1, 5.6]. Recorded mean on the same 36 tasks 35.3%:
  r1 +9.1 [2.0, 17.9], r2 +6.3 [-2.4, 15.1], mean of two +7.7 [1.2, 15.1] (task bootstrap, 5,000 reps). Pooled 13.5 s/call [11.2, 16.2]
  (run 1: 14.8 on same tasks). Reading: modest gain over recorded runs is suggestive; one task (never-class) flipped each way.
  Output in kaggle/output_full_s0_r2/ (private per-task labels; not published). Paper, md and 3 LaTeX versions updated.
