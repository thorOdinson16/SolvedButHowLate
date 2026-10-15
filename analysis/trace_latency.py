"""Per-run latency/throughput from ATIF-style traces of the calibration notebooks.

Usage: python -I analysis/trace_latency.py <traces dir> <label>
Reads trace_<instance>.json (steps[] with extra.elapsed_s, metrics, llm_call_count;
final_metrics.total_*_tokens). Writes results/trace_latency_<label>.json.
All numbers are for ONE model on 4xL4 TP=4, one task at a time.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import OUT  # noqa: E402

src, label = Path(sys.argv[1]), sys.argv[2]
rows = []
for f in sorted(src.glob("trace_*.json")):
    d = json.load(open(f, encoding="utf-8"))
    steps = d["steps"]
    fm = d["final_metrics"]
    el = [s.get("extra", {}).get("elapsed_s") for s in steps if s.get("extra", {}).get("elapsed_s") is not None]
    wall = max(el) if el else float("nan")
    llm_calls = sum(s.get("llm_call_count") or 0 for s in steps)
    tool_steps = sum(1 for s in steps if s.get("tool_calls"))
    gaps = np.diff([0] + [s["extra"]["elapsed_s"] for s in steps if s.get("tool_calls") and s.get("extra", {}).get("elapsed_s") is not None])
    rows.append({
        "task": f.stem.replace("trace_", ""), "wall_s": float(wall), "llm_calls": int(llm_calls),
        "tool_steps": int(tool_steps), "prompt_tokens": fm.get("total_prompt_tokens"),
        "completion_tokens": fm.get("total_completion_tokens"),
        "completion_tok_per_s": (fm.get("total_completion_tokens") or 0) / wall if wall and wall == wall else None,
        "median_gap_between_tool_steps_s": float(np.median(gaps)) if len(gaps) else None})
tot_c = sum(r["completion_tokens"] or 0 for r in rows)
tot_w = sum(r["wall_s"] for r in rows if r["wall_s"] == r["wall_s"])
summary = {"label": label, "n": len(rows), "pooled_completion_tok_per_s": tot_c / tot_w if tot_w else None,
           "median_gap_between_tool_steps_s": float(np.median([r["median_gap_between_tool_steps_s"] for r in rows if r["median_gap_between_tool_steps_s"]])),
           "completion_tokens_per_llm_call": tot_c / max(1, sum(r["llm_calls"] for r in rows)),
           "rows": rows}
json.dump(summary, open(OUT / f"trace_latency_{label}.json", "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
for r in rows:
    print(f"{r['task']:16s} wall={r['wall_s']:7.1f}s llm={r['llm_calls']:3d} tool_steps={r['tool_steps']:3d} "
          f"compl_tok={r['completion_tokens']:6d} tok/s={r['completion_tok_per_s']:.1f}")
