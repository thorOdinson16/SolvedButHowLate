"""Sanity check: key numbers quoted in paper/draft_writeup.md vs results/*.json|csv. Exit 1 on mismatch."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import OUT  # noqa: E402

F = json.load(open(OUT / "full31b.json"))
R = json.load(open(OUT / "results.json"))
cap = pd.read_csv(OUT / "full31b_cap_table.csv").set_index("cap_min")
checks = {
    "new run resolved 45.1%": (F["resolved_new"][0], 0.451, 0.001),
    "paired diff +5.8 pts": (F["paired_diff_new_minus_recorded"][0], 0.058, 0.001),
    "sec per tool call 13.3": (F["sec_per_tool_call_pooled"][0], 13.3, 0.05),
    "resolved within 4.9 min 32%": (F["resolved_within_wall_minutes_new"]["4.9"][0], 0.324, 0.002),
    "resolved within 6 min 35%": (F["resolved_within_wall_minutes_new"]["6.0"][0], 0.352, 0.002),
    "cap 10 min resolved 40.8%": (cap.loc[10, "resolved"], 0.408, 0.001),
    "cap 10 min mean min 5.0": (cap.loc[10, "mean_min"], 5.0, 0.05),
    "cap 6 min mean min 4.3": (cap.loc[6, "mean_min"], 4.3, 0.05),
    "uncapped mean min 5.5": (F["mean_task_minutes_uncapped"], 5.5, 0.05),
    "overflow 10/71": (F["overflow_rate"][0], 10 / 71, 0.001),
}
bad = 0
for name, (got, want, tol) in checks.items():
    ok = abs(got - want) <= tol
    bad += not ok
    print(("ok   " if ok else "FAIL ") + f"{name}: got {got:.4f}, expected {want:.4f}")
sys.exit(1 if bad else 0)
