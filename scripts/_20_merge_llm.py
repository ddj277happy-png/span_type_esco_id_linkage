# -*- coding: utf-8 -*-
"""
20_merge_llm.py
把 DeepSeek 全量判定合到 final_match_v4 → v5
- LLM 选 1 → matched with top-1
- LLM 选 2 → matched with top-2
- LLM 选 3 → matched with top-3
- LLM 选 none → no_match
- LLM err → 保持原 status
"""
import os
import csv
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V4 = os.path.join(ROOT, "final_match_v4.csv")
LLM = os.path.join(ROOT, "llm_labels.csv")
OUT = os.path.join(ROOT, "final_match_v5.csv")

m = pd.read_csv(V4, encoding="utf-8-sig")
llm = pd.read_csv(LLM, encoding="utf-8-sig")
print(f"v4: {len(m)}, llm labels: {len(llm)}", flush=True)

# 索引 LLM
llm_idx = llm.set_index(["span", "type"])[["llm_choice", "llm_top_idx", "llm_reason"]]
print(f"LLM unique (span,type): {len(llm_idx)}", flush=True)

# 拆 top3
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

# 应用 LLM 判定
n_updated, n_none, n_err, n_match = 0, 0, 0, 0
for idx, r in m.iterrows():
    if r["status"] == "matched": continue
    key = (r["span"], r["type"])
    if key not in llm_idx.index: continue
    ll = llm_idx.loc[key]
    if isinstance(ll, pd.DataFrame): ll = ll.iloc[0]
    choice = ll["llm_choice"]
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
    # 选 top-N
    top_idx = int(ll["llm_top_idx"])
    if top_idx < 0:
        m.at[idx, "status"] = "no_match"
        n_none += 1
        continue
    top3 = parse_top3(r["top3"])
    if top_idx >= len(top3):
        m.at[idx, "status"] = "no_match"
        n_none += 1
        continue
    pick = top3[top_idx]
    m.at[idx, "esco_uri"] = pick["uri"]
    m.at[idx, "esco_label_en"] = pick["label"]
    m.at[idx, "score"] = pick["score"]
    m.at[idx, "status"] = "matched"
    n_updated += 1
    n_match += 1

print(f"\nLLM updated → matched: {n_updated}, → no_match: {n_none}, err skip: {n_err}", flush=True)
print(f"\nNew status dist:", flush=True)
print(m["status"].value_counts(), flush=True)
print(f"\nBy type:", flush=True)
print(pd.crosstab(m["type"], m["status"]), flush=True)

m.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)

# 也更新 long 表
SRC = os.path.join(ROOT, "step3_skill_annotation_20260810_012339.csv")
src = pd.read_csv(SRC, encoding="utf-8-sig")
m["key"] = m["span"].astype(str) + "||" + m["type"].astype(str)
m_idx = m.set_index("key")[["esco_uri","esco_label_en","score","status","top3"]]
out_rows = []
for _, r in src.iterrows():
    job_id = r["id"]; company = r["企业名称"]; title = r["招聘岗位"]
    city = r["工作城市"]; langs = r["匹配的语言"]
    for col in ["L","K","S","T"]:
        v = str(r.get(col) or "")
        if not v or v == "nan" or v == "-": continue
        for s in v.split("；"):
            s = s.strip()
            if not s: continue
            key = f"{s}||{col}"
            if key in m_idx.index:
                mm = m_idx.loc[key]
                if isinstance(mm, pd.DataFrame): mm = mm.iloc[0]
                out_rows.append({
                    "job_id": job_id, "company": company, "title": title,
                    "city": city, "matched_languages": langs,
                    "span": s, "type": col,
                    "esco_uri": mm["esco_uri"] if pd.notna(mm["esco_uri"]) else "",
                    "esco_label_en": mm["esco_label_en"] if pd.notna(mm["esco_label_en"]) else "",
                    "score": mm["score"], "status": mm["status"],
                })
            else:
                out_rows.append({
                    "job_id": job_id, "company": company, "title": title,
                    "city": city, "matched_languages": langs, "span": s, "type": col,
                    "esco_uri": "", "esco_label_en": "", "score": 0.0, "status": "no_match",
                })
df_long = pd.DataFrame(out_rows)
df_long.to_csv(os.path.join(ROOT, "final_match_long.csv"), index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
print(f"\nSaved: final_match_long.csv ({len(df_long)} rows)", flush=True)

# 简化版
df_simple = df_long[["span", "type", "esco_uri", "esco_label_en", "score", "status"]].copy()
df_simple.to_csv(os.path.join(ROOT, "spans_with_esco.csv"), index=False, encoding="utf-8-sig")
print(f"Saved: spans_with_esco.csv", flush=True)
print(df_simple["status"].value_counts(), flush=True)
