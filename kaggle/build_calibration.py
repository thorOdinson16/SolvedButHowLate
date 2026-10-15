"""Build (do NOT push) a Kaggle notebook that calibrates seconds-per-tool-call for the official
31B agent under the CURRENT harness, one task at a time.

Base: the competition's pinned notebook "Getting Started - Gemma 4 Developer Agent"
(pulled to kaggle/official_starter/). Its install, model, vLLM and evaluator cells are reused
verbatim, so the notebook runs the current harness settings (compaction_interval=15,
gpu_memory_utilization=0.90, scheduler_reserve_full_isl=False, ...).

Modifications (each logged as LOG.md D19):
  M1  agent: single LlmAgent, no LoRA adapters, no analyzer sub-agent, official sample prompt and
      sampling.yaml. Matches the recorded study's agent definition (its preregistration:
      "single LlmAgent with the official starter system prompt") so outcomes are comparable.
  M2  budgets: 40 tool calls / 30 min / 100 turns / 120 s command timeout (recorded study's budgets;
      the sample's eval_config.yaml has 10 calls / 1 min, which is a smoke-test value).
  M3  tasks: 8 fixed tasks (below) instead of tasks[:2]; stop launching tasks after 150 min.
  M4  logging: per-task JSONL (resolved, tool/LLM calls, duration, timestamps) + traces packed to
      /kaggle/working/cal_results.tar.gz.
Concurrency is 1 by construction (official loop is sequential).
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\Users\AbhiDS\Documents\AgentPaperTrack")
PROJ = ROOT / "paper_project"
USER = "abhids123"
SLUG = None  # set after MODEL is known
OUT = None
STARTER = PROJ / "kaggle" / "official_starter" / "getting-started-gemma-4-developer-agent.ipynb"
import sys
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma-4-31b-it-qat-w4a16-ct"
TAG = {"gemma-4-31b-it-qat-w4a16-ct": "31b", "gemma-4-12b-it-qat-w4a16-ct": "12b", "gemma-4-e4b-it-qat-w4a16-ct": "e4b", "gemma-4-e2b-it-qat-w4a16-ct": "e2b"}[MODEL]

# ---- deterministic task choice: 3 always-solved, 3 mixed, 2 never-solved (recorded outcomes)
runs = pd.read_csv(PROJ / "derived" / "runs.csv")
obs = runs[runs.group == "obs"]
rate = obs.groupby("task").resolved.mean()
repo = obs.groupby("task").repo.first()
cls = pd.Series(["never" if r == 0 else "always" if r == 1 else "mixed" for r in rate], index=rate.index)
h = lambda t: hashlib.sha256(t.encode()).hexdigest()
IDS, per_repo = [], {}
for c, n in (("always", 3), ("mixed", 3), ("never", 2)):
    got = 0
    for t in sorted(cls[cls == c].index, key=h):
        if per_repo.get(repo[t], 0) >= 5:
            continue
        IDS.append(t); per_repo[repo[t]] = per_repo.get(repo[t], 0) + 1; got += 1
        if got == n:
            break

# ---- optional full run: argv[2]=shard index, argv[3]=number of shards -> all 71 tasks, hash order
SHARD = None
if len(sys.argv) > 3:
    SHARD, NSH = int(sys.argv[2]), int(sys.argv[3])
    IDS = [t for i, t in enumerate(sorted(rate.index, key=h)) if i % NSH == SHARD]
    REP = sys.argv[4] if len(sys.argv) > 4 else ""   # optional replicate tag, e.g. "r2" (LOG D29)
    SLUG = f"g4-full-{TAG}-s{SHARD}of{NSH}" + (f"-{REP}" if REP else "")
    OUT = PROJ / "kaggle" / "notebooks" / (f"full{TAG}-s{SHARD}" + (f"-{REP}" if REP else ""))
else:
    SLUG = f"g4-latency-calibration-{TAG}-seq"
    OUT = PROJ / "kaggle" / "notebooks" / f"cal{TAG}-seq"
RUN_MIN = 270 if SHARD is not None else 150      # stop launching tasks after this many minutes
WATCHDOG_H = 5 if SHARD is not None else 4
nb = json.load(open(STARTER, encoding="utf-8"))
src = lambda i: "".join(nb["cells"][i]["source"])
cell_install = src(2)
cell_data = src(4)
assert "MODEL_NAME = 'gemma-4-12b-it-qat-w4a16-ct'" in cell_data   # starter defaults to 12B
cell_data = cell_data.replace("MODEL_NAME = 'gemma-4-12b-it-qat-w4a16-ct'", f"MODEL_NAME = '{MODEL}'")
cell_data = cell_data.replace("SAMPLE_SUBMISSION_SRC = DATA_DIR / 'sample_submission'",
                              "SAMPLE_SUBMISSION_SRC = DATA_DIR / 'sample_submission'  # official starter agent (modified in next cell)")
cell_server = src(8)
cell_eval_head = src(10)

AGENT_YAML = f"""name: swe_baseline_agent
model: {MODEL}
instruction: !include prompts/system.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
  - get_code_neighbors
  - search_similar_code
  - get_code_subgraph
generate_content_config: !include configs/sampling.yaml
"""
EVAL_YAML = """evaluation:
  timeout_seconds: 120
  verification_timeout_seconds: 300
  max_tool_calls: 40
  max_time_minutes: 30
  max_turns: 100
"""
cell_modify = f'''
# --- M1/M2: calibration agent = single LlmAgent, no adapters/sub-agents, recorded-study budgets
AGENT_YAML = {json.dumps(AGENT_YAML)}
EVAL_YAML = {json.dumps(EVAL_YAML)}
(AGENT_DIR / 'agent.yaml').write_text(AGENT_YAML, encoding='utf-8')
(AGENT_DIR / 'eval_config.yaml').write_text(EVAL_YAML, encoding='utf-8')
shutil.rmtree(AGENT_DIR / 'adapters', ignore_errors=True)
shutil.rmtree(AGENT_DIR / 'sub_agents', ignore_errors=True)
import threading, time as _t\nNB_T0 = _t.time()\ndef _watchdog():\n    import tarfile, os\n    try:\n        with tarfile.open('/kaggle/working/cal_results.tar.gz', 'w:gz') as tf:\n            for p in ('/kaggle/working/results', '/kaggle/working/calibration'):\n                if os.path.exists(p): tf.add(p, arcname=os.path.basename(p))\n    finally:\n        print('WATCHDOG: wall limit reached, exiting', flush=True)\n        os._exit(0)\nthreading.Timer({WATCHDOG_H} * 3600, _watchdog).start()\nprint(sorted(str(p.relative_to(AGENT_DIR)) for p in AGENT_DIR.rglob('*') if p.is_file()))
'''

head, _ = cell_eval_head.split("# Select a small subset of tasks from the published dataset")
cell_run = head + f'''
# --- M3/M4: fixed task list, sequential loop with per-task JSONL logging
import json, time, tarfile
# (defined by the starter's skipped 'code graph demo' cell; needed by EvalConfig)
GRAPH_DIR = str(DATA_DIR / 'graphs')
EMBEDDINGS_DIR = str(DATA_DIR / 'embeddings')
CAL_IDS = {json.dumps(IDS)}
by_id = {{t.instance_id: t for t in tasks}}
SAMPLE_TASKS = [by_id[i] for i in CAL_IDS]
limits, gen_constraints = build_submission_limits()
eval_config = EvalConfig(
    tasks_path=TASKS_PATH, snapshots_dir=DATA_DIR / 'snapshots', results_dir=WORKING_DIR / 'results',
    submission_dir=AGENT_DIR, models=models, sandbox='subprocess', timeout_seconds=timeout_seconds,
    verification_timeout_seconds=verification_timeout_seconds, max_time_minutes=max_time_minutes,
    max_tool_calls=max_tool_calls, max_turns=max_turns, limits=limits, generation_constraints=gen_constraints,
    adapter_manifest=adapters,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                    token_threshold=14336, event_retention_size=5),
    graph_dir=GRAPH_DIR, embeddings_dir=EMBEDDINGS_DIR, wheels_dir=DATA_DIR / 'wheels', verbose=False)
evaluator = Evaluator(eval_config)
CAL = WORKING_DIR / 'calibration'; CAL.mkdir(exist_ok=True)
T_START = time.time(); DEADLINE = T_START + {RUN_MIN} * 60
print('limits:', dict(timeout=timeout_seconds, calls=max_tool_calls, minutes=max_time_minutes, turns=max_turns))
with open(CAL / 'results.jsonl', 'a') as logf:
    for idx, task in enumerate(SAMPLE_TASKS, start=1):
        rec = {{'instance_id': task.instance_id, 'repo': task.repo, 'order': idx, 'started_at': time.time()}}
        if time.time() > DEADLINE:
            rec['status'] = 'skipped_deadline'
        else:
            try:
                res = run_sync(evaluator.evaluate_task, task=task, task_index=idx, total_tasks=len(SAMPLE_TASKS))
                rec.update(status='done', resolved=bool(res.resolved), tool_calls=res.tool_calls,
                           llm_calls=getattr(res, 'total_llm_calls', None),
                           duration_s=round(res.duration_seconds, 1), error=res.error,
                           patch_chars=len(res.agent_patch or ''), test_exit_code=res.test_exit_code)
            except Exception as e:
                rec.update(status='exception', error=f'{{type(e).__name__}}: {{e}}')
        rec['finished_at'] = time.time()
        logf.write(json.dumps(rec) + '\\n'); logf.flush()
        print(json.dumps(rec), flush=True)
print('total minutes', round((time.time() - T_START) / 60, 1))
'''
cell_pack = '''
import tarfile, os
try:
    server_instance.stop()
except Exception as e:
    print('server stop:', e)
with tarfile.open('/kaggle/working/cal_results.tar.gz', 'w:gz') as tf:
    for p in ('/kaggle/working/results', '/kaggle/working/calibration'):
        if os.path.exists(p):
            tf.add(p, arcname=os.path.basename(p))
print('packed', round(os.path.getsize('/kaggle/working/cal_results.tar.gz') / 1e6, 1), 'MB')
'''
md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s}
code = lambda s: {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s.strip("\n")}
cells = [md(f"# Latency calibration, 31B, sequential\nBuilt from the official starter notebook; see paper_project/docs/LOG.md D19.\n\nTasks: {IDS}"),
         code(cell_install), code(cell_data), code(cell_modify), code(cell_server), code(cell_run), code(cell_pack)]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "notebook.ipynb").write_text(json.dumps({
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                 "language_info": {"name": "python"}}, "cells": cells}, indent=1), encoding="utf-8")
meta = json.load(open(STARTER.parent / "kernel-metadata.json"))
meta.update({"id": f"{USER}/{SLUG}", "title": SLUG, "code_file": "notebook.ipynb", "is_private": True,
             "enable_gpu": True, "enable_internet": False, "keywords": [],
             "model_sources": [f"google/gemma-4/Other/{MODEL}/2"]})
meta.pop("id_no", None)
(OUT / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print("built", OUT)
print("tasks:", IDS)
print("classes:", [cls[t] for t in IDS], "| repos:", [repo[t] for t in IDS])

