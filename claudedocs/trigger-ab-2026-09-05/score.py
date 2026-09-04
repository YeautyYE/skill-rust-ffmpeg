#!/usr/bin/env python3
"""Score routing results: recall on P/H, false-positive rate on N, per arm x model."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
queries = dict(json.loads((OUT / "queries.json").read_text()))
ARMS = ["old_full", "old_trunc", "new"]
MODELS = ["haiku", "sonnet", "fable"]

def load(arm, model):
    p = OUT / f"result_{arm}_{model}.json"
    if not p.exists():
        return None
    txt = p.read_text()
    start, end = txt.find("{"), txt.rfind("}")
    return json.loads(txt[start:end + 1])

table = {}
misses = {}
for model in MODELS:
    for arm in ARMS:
        r = load(arm, model)
        if r is None:
            table[(arm, model)] = "missing"
            continue
        pos = [q for q in queries if q.startswith("P")]
        hard = [q for q in queries if q.startswith("H")]
        neg = [q for q in queries if q.startswith("N")]
        hit = lambda ids: sum(1 for q in ids if r.get(q) == "rust-ffmpeg")
        table[(arm, model)] = (hit(pos), len(pos), hit(hard), len(hard), hit(neg), len(neg))
        misses[(arm, model)] = [f"{q}={r.get(q)}" for q in pos + hard if r.get(q) != "rust-ffmpeg"] + \
                               [f"{q}={r.get(q)}" for q in neg if r.get(q) == "rust-ffmpeg"]

print(f"{'arm':10} {'model':7} {'corpus P':>9} {'hard H':>7} {'false+ N':>9}")
for model in MODELS:
    for arm in ARMS:
        v = table[(arm, model)]
        if v == "missing":
            print(f"{arm:10} {model:7} missing")
            continue
        p, pn, h, hn, n, nn = v
        print(f"{arm:10} {model:7} {p:>5}/{pn:<3} {h:>4}/{hn:<2} {n:>5}/{nn:<3}")
print()
for k, v in misses.items():
    if v:
        print(k, "deviations:", ", ".join(v))
