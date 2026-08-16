# -*- coding: utf-8 -*-
"""
19_merge_v4.py
合并 postfix + tier1 到 final_match_v3
"""
import os
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V3 = os.path.join(ROOT, "final_match_v3.csv")
TIER1 = os.path.join(ROOT, "tier1_ac_match.csv")
OUT = os.path.join(ROOT, "final_match_v4.csv")

m = pd.read_csv(V3, encoding="utf-8-sig")
t1 = pd.read_csv(TIER1, encoding="utf-8-sig")
print(f"v3: {len(m)}, tier1: {len(t1)}", flush=True)

# 把 tier1 的 hits 加进 v3
t1_idx = t1.set_index(["span", "type"])[["esco_uri", "esco_label_en", "score"]]

n = 0
for idx, r in m.iterrows():
    if r["status"] in ["review", "no_match"]:
        key = (r["span"], r["type"])
        if key in t1_idx.index:
            row = t1_idx.loc[key]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            m.at[idx, "esco_uri"] = row["esco_uri"]
            m.at[idx, "esco_label_en"] = row["esco_label_en"]
            m.at[idx, "score"] = row["score"]
            m.at[idx, "status"] = "matched"
            m.at[idx, "top3"] = f"{row['esco_uri']}|{row['esco_label_en']}|{row['score']:.3f}  (tier1_ac)"
            n += 1

print(f"Updated {n} rows via tier1", flush=True)
print(f"\nNew status dist:", flush=True)
print(m["status"].value_counts(), flush=True)

m.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)
