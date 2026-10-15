# Compute plan: do we need AWS?

Short answer: **not for the current paper**, and the one measurement that would most improve it is
better done on a free Kaggle L4×4 notebook than on EC2. Nothing was launched. No AWS credentials exist
on the working machine, and all prices below are from memory and unverified.

## What we most need to measure
Seconds per tool call for the official 31B W4A16 agent under the **sequential** official conditions.
It converts the anytime curve (calls) into minutes, and the paper's headline swings from ~6% to ~31%
with it (RESULTS §1).

## Options
| Option | Hardware | Fidelity to official scorer | Cost | Risk |
|---|---|---|---|---|
| **A. Kaggle notebook, competition attached** | 4×L4 (official) | exact | free, subject to GPU quota | needs the user's account to have accepted the rules; competition-only quota |
| B. EC2 g5.2xlarge (within the 8-vCPU quota) | 1×A10G 24 GB | low: 31B W4A16 barely fits, shorter context, different throughput | ~$1.2/h (unverified) | latency would not match 4×L4 TP=4, so it cannot calibrate the headline |
| C. EC2 g6.12xlarge (4×L4) | 4×L4 | high | ~$4–5/h (unverified); needs a quota raise from 8 to 48 vCPUs | would need the official `swegemma`/ADK stack installed by hand |

## Recommendation
Use **A**. The public dataset already ships the notebook builder and per-condition runner
(`agent_saw_data/code/kaggle/build_notebook.py`, `run_condition.py`) for exactly this harness.
A calibration run of ~10 tasks, **one task at a time**, recording per-call latency and tokens, would
replace the 20 s/call assumption with a measurement.

Use EC2 only if Kaggle quota blocks (A), and then request the 4×L4 quota (C), not option B.

## Budget if EC2 is used (C), unverified prices
| Item | Hours | $ |
|---|---|---|
| install + smoke test | 2 | ~10 |
| 10–30 sequential tasks | 3–5 | ~15–25 |
| reserve | | ≥ 30 |
Stop the instance after every job; set budget alerts at $40 and $80 before the first launch.

## What AWS would not fix
The sample is 71 tasks from two repositories. More compute on the same tasks does not change that;
only new tasks would (a larger engineering effort, see LOG D2 candidate 6).
