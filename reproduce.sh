#!/usr/bin/env bash
# Rebuild every table, number and figure. Needs ../data (competition files), ../agent_saw_data (public run
# tables) and, for step 5, the per-task result files of the sequential run (private; see README).
set -euo pipefail
cd "$(dirname "$0")"
python -I analysis/build_tables.py
python -I analysis/analyze.py
python -I analysis/replicate.py
# step 5 (optional, needs the sequential-run results.jsonl files):
if [ -f kaggle/output_full_s0/calibration/results.jsonl ] && [ -f kaggle/output_full_s1/calibration/results.jsonl ]; then
  python -I analysis/full_run.py kaggle/output_full_s0/calibration/results.jsonl kaggle/output_full_s1/calibration/results.jsonl > /dev/null
fi
python -I analysis/figures.py
python -I analysis/check_numbers.py
