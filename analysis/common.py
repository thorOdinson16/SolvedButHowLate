"""Shared paths and loaders. All analysis is offline and deterministic."""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\AbhiDS\Documents\AgentPaperTrack")
DATA = ROOT / "data"                 # competition data (not redistributed)
SAW = ROOT / "agent_saw_data"        # public 'What the Agent Saw' dataset (Apache-2.0)
PROJ = ROOT / "paper_project"
DER = PROJ / "derived"
OUT = PROJ / "results"
FIG = PROJ / "figures"
for _d in (DER, OUT, FIG):
    _d.mkdir(parents=True, exist_ok=True)


def jl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
