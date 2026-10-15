import json, sys, os, collections, statistics as st, glob
D = sys.argv[1]
tasks = [json.loads(l) for l in open(os.path.join(D, "tasks.jsonl"), encoding="utf-8")]
print("tasks:", len(tasks), "keys:", list(tasks[0].keys()))
print("per repo:", collections.Counter(t["repo"] for t in tasks))
def q(xs):
    xs = sorted(xs); return dict(min=xs[0], med=xs[len(xs)//2], p90=xs[int(len(xs)*.9)], max=xs[-1])
print("problem_statement chars:", q([len(t["problem_statement"]) for t in tasks]))
print("hints non-empty:", sum(1 for t in tasks if t["hints_text"].strip()))
def files(p):
    return [l[6:].split("\t")[0] for l in p.splitlines() if l.startswith("+++ b/")]
pf = [len(files(t["patch"])) for t in tasks]
print("files changed in gold patch:", q(pf), "single-file:", sum(1 for x in pf if x == 1))
pl = [sum(1 for l in t["patch"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")) for t in tasks]
print("gold patch changed lines:", q(pl))
print("test_patch files:", q([len(files(t["test_patch"])) for t in tasks]))
print("created_at range:", min(t["created_at"] for t in tasks), max(t["created_at"] for t in tasks))
print("unique base_commits:", len({(t["repo"], t["base_commit"]) for t in tasks}))
# graphs
gdir = os.path.join(D, "graphs")
gs = sorted(glob.glob(os.path.join(gdir, "*.json")))
print("graph files:", len(gs))
by_repo = collections.defaultdict(list)
etypes = collections.Counter()
rows = []
for t in tasks:
    p = os.path.join(gdir, t["repo"].split("/")[1].lower() + "_" + t["base_commit"] + ".json")
    if not os.path.exists(p): continue
    g = json.load(open(p, encoding="utf-8"))
    n, e = len(g["nodes"]), len(g["edges"])
    rows.append((t["instance_id"], n, e))
    for ed in g["edges"]: etypes[ed["type"]] += 1
    # does gold-patch file appear among nodes?
rows.sort(key=lambda r: r[1])
print("nodes per graph:", q([r[1] for r in rows]))
print("edges per graph:", q([r[2] for r in rows]))
print("edge types:", etypes.most_common())
g = json.load(open(gs[len(gs)//2], encoding="utf-8"))
print("sample graph keys:", list(g.keys()), "graph attrs:", g["graph"])
print("sample node:", {k: (v[:120] if isinstance(v, str) else v) for k, v in g["nodes"][0].items()})
print("sample edge:", g["edges"][0])
print("node text chars:", q([len(n.get("text", "")) for n in g["nodes"]]))
# embeddings
import numpy as np
ez = os.path.join(D, "embeddings", os.path.basename(gs[len(gs)//2])[:-5] + ".npz")
z = np.load(ez, allow_pickle=False)
ks = list(z.keys())
print("npz entries:", len(ks), "sample key:", ks[0], "shape:", z[ks[0]].shape, z[ks[0]].dtype)
gid = {n["id"] for n in g["nodes"]}
print("embedded keys in graph nodes:", sum(1 for k in ks if k in gid), "/", len(ks), "graph nodes:", len(gid))
m = np.stack([z[k] for k in ks[:2000]])
nrm = np.linalg.norm(m, axis=1)
print("norm mean/min/max:", nrm.mean().round(3), nrm.min().round(3), nrm.max().round(3))
# gold-file localisation: does the patched function/file appear as graph nodes?
hit = tot = 0
for t in tasks:
    p = os.path.join(gdir, t["repo"].split("/")[1].lower() + "_" + t["base_commit"] + ".json")
    if not os.path.exists(p): continue
    ids = [n["id"] for n in json.load(open(p, encoding="utf-8"))["nodes"]]
    for f in files(t["patch"]):
        mod = f[:-3].replace("/", ".")
        tot += 1
        if any(i == mod or i.startswith(mod + ".") for i in ids): hit += 1
print("gold patch files present as graph modules:", hit, "/", tot)

