# -*- coding: utf-8 -*-
"""
17_merge.py
把 postfix_match 合并进 final_match_v2
"""
import os
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V2 = os.path.join(ROOT, "final_match_v2.csv")
POST = os.path.join(ROOT, "postfix_match.csv")
OUT = os.path.join(ROOT, "final_match_v3.csv")

m = pd.read_csv(V2, encoding="utf-8-sig")
p = pd.read_csv(POST, encoding="utf-8-sig")
print(f"v2: {len(m)}, postfix: {len(p)}", flush=True)

# 合并:postfix 的 hits 覆盖 v2 的 review/no_match
p_idx = p.set_index(["span", "type"])[["esco_uri", "esco_label_en", "score", "match_kind"]]

n_updated = 0
for idx, r in m.iterrows():
    if r["status"] in ["review", "no_match"]:
        key = (r["span"], r["type"])
        if key in p_idx.index:
            row = p_idx.loc[key]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            m.at[idx, "esco_uri"] = row["esco_uri"]
            m.at[idx, "esco_label_en"] = row["esco_label_en"]
            m.at[idx, "score"] = row["score"]
            m.at[idx, "status"] = "matched"
            m.at[idx, "top3"] = f"{row['esco_uri']}|{row['esco_label_en']}|{row['score']:.3f}  (postfix:{row['match_kind']})"
            n_updated += 1

print(f"Updated {n_updated} rows from review/no_match -> matched", flush=True)
print(f"\nNew status distribution:", flush=True)
print(m["status"].value_counts(), flush=True)

m.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)
