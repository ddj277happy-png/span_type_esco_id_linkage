# -*- coding: utf-8 -*-
"""
22_merge_rerun.py
把 llm_labels_v2 (4741 条新 DeepSeek 判定) 合到 final_match_v5 → v6
"""
import os, csv
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V5 = os.path.join(ROOT, "final_match_v5.csv")
NEW = os.path.join(ROOT, "llm_labels_v2.csv")
OUT = os.path.join(ROOT, "final_match_v6.csv")

m = pd.read_csv(V5, encoding="utf-8-sig")
new = pd.read_csv(NEW, encoding="utf-8-sig")
print(f"v5: {len(m)}, new labels: {len(new)}", flush=True)

new_idx = new.set_index(["span", "type"])[["llm_choice", "llm_top_idx", "llm_reason"]]

def parse_top3(s):
    if not isinstance(s, str): return []
    out = []
    for p in s.split(" || "):
        try:
            uri, label, score = p.rsplit("|", 2)
            out.append({"uri": uri, "label": label, "score": float(score)})
        except Exception:
            continue
    return out

n_updated, n_none, n_err = 0, 0, 0
for idx, r in m.iterrows():
    if r["status"] != "review": continue
    key = (r["span"], r["type"])
    if key not in new_idx.index: continue
    nl = new_idx.loc[key]
    if isinstance(nl, pd.DataFrame): nl = nl.iloc[0]
    choice = nl["llm_choice"]
    if choice == "err":
        n_err += 1
        continue
    if choice == "none":
        m.at[idx, "status"] = "no_match"
        m.at[idx, "score"] = 0.0
        m.at[idx, "esco_uri"] = ""
        m.at[idx, "esco_label_en"] = ""
        n_none += 1
        continue
    top_idx = int(nl["llm_top_idx"])
    top3 = parse_top3(r["top3"])
    if top_idx < 0 or top_idx >= len(top3):
        m.at[idx, "status"] = "no_match"
        n_none += 1
        continue
    pick = top3[top_idx]
    m.at[idx, "esco_uri"] = pick["uri"]
    m.at[idx, "esco_label_en"] = pick["label"]
    m.at[idx, "score"] = pick["score"]
    m.at[idx, "status"] = "matched"
    n_updated += 1

print(f"\nLLM updated → matched: {n_updated}, → no_match: {n_none}, err: {n_err}", flush=True)
print(f"\nNew status dist:", flush=True)
print(m["status"].value_counts(), flush=True)
print(f"\nBy type:", flush=True)
print(pd.crosstab(m["type"], m["status"]), flush=True)

m.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)
