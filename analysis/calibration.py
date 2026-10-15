"""Ingest Kaggle calibration output and (1) measure sequential seconds per call,
(2) compare against the recorded concurrent runs of the same tasks/seed (harness-drift check),
(3) re-express the anytime-curve official band in minutes using the MEASURED latency.

Usage: python -I analysis/calibration.py <dir containing results.jsonl> [label]
Input dir is the unpacked 'calibration' folder from cal_results.tar.gz (results.jsonl inside).
Output: results/calibration_<label>.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import DER, OUT  # noqa: E402

src = Path(sys.argv[1])
label = sys.argv[2] if len(sys.argv) > 2 else src.parent.name
rows = [json.loads(l) for l in open(src / "results.jsonl", encoding="utf-8") if l.strip()]
cal = pd.DataFrame(rows)
done = cal[cal.status == "done"].copy()
R = {"label": label, "n_rows": int(len(cal)), "n_done": int(len(done)),
     "status_counts": cal.status.value_counts().to_dict()}
if len(done):
    done["sec_per_tool_call"] = done.duration_s / done.tool_calls.clip(lower=1)
    done["sec_per_llm_call"] = done.duration_s / done.llm_calls.clip(lower=1)
    R["sec_per_tool_call_median"] = float(done.sec_per_tool_call.median())
    R["sec_per_tool_call_iqr"] = np.percentile(done.sec_per_tool_call, [25, 75]).round(1).tolist()
    R["sec_per_llm_call_median"] = float(done.sec_per_llm_call.median())
    R["duration_s_median"] = float(done.duration_s.median())
    R["tool_calls_median"] = float(done.tool_calls.median())
    R["resolved"] = int(done.resolved.sum())
    # pooled (total time / total calls) is less sensitive to short runs
    R["sec_per_tool_call_pooled"] = float(done.duration_s.sum() / done.tool_calls.clip(lower=1).sum())

    runs = pd.read_csv(DER / "runs.csv")
    rec = runs[(runs.cell == "base_s1") & runs.task.isin(done.instance_id)].set_index("task")
    cmp = done.set_index("instance_id")[["resolved", "tool_calls", "llm_calls", "duration_s"]].join(
        rec[["resolved", "tool_calls", "llm_calls", "duration_s"]], rsuffix="_recorded")
    R["drift_table"] = cmp.reset_index().to_dict(orient="records")
    both = cmp.dropna()
    if len(both):
        R["drift_summary"] = {
            "n": int(len(both)),
            "resolved_now": int(both.resolved.sum()), "resolved_recorded": int(both.resolved_recorded.sum()),
            "tool_calls_median_now": float(both.tool_calls.median()),
            "tool_calls_median_recorded": float(both.tool_calls_recorded.median()),
            "duration_ratio_now_over_recorded_median": float((both.duration_s / both.duration_s_recorded).median()),
            "sec_per_call_recorded_median": float((both.duration_s_recorded / both.llm_calls_recorded).median()),
            "sec_per_call_now_median": float((both.duration_s / both.llm_calls).median())}

    # official band in calls, at the measured per-tool-call latency
    s = R["sec_per_tool_call_pooled"]
    cur = pd.read_csv(OUT / "anytime_curves.csv")
    band = {}
    for lo_m, hi_m in ((4.9, 6.0),):
        lo_k, hi_k = int(lo_m * 60 / s), int(hi_m * 60 / s)
        band = {"sec_per_call_used": s, "calls": [lo_k, hi_k],
                "in_place": [float(cur.obs_all__in_place.iloc[min(lo_k, 40)]), float(cur.obs_all__in_place.iloc[min(hi_k, 40)])],
                "completed": [float(cur.obs_all__completed.iloc[min(lo_k, 40)]), float(cur.obs_all__completed.iloc[min(hi_k, 40)])]}
    R["official_band_at_measured_latency"] = band

json.dump(R, open(OUT / f"calibration_{label}.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k != "drift_table"}, indent=1, default=str))
