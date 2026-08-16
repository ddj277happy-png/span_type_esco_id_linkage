# -*- coding: utf-8 -*-
"""
11_finalize.py
把 final_match.csv (span+type 唯一键 → uri) 合并回原始 job CSV
产出最终 2 个交付:
1. final_match_long.csv  :  job_id, 企业, 岗位, 城市, 语言, span, type, esco_uri, esco_label_en, score, status
2. spans_with_esco.csv   :  仅 unique span 视角(原 final_match 增强版)
"""
import os, csv
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
SRC = os.path.join(ROOT, "step3_skill_annotation_20260810_012339.csv")  # 原始 job+span
MATCH = os.path.join(ROOT, "final_match.csv")  # span+type → uri

# 加载 match
m = pd.read_csv(MATCH, encoding="utf-8-sig")
m["key"] = m["span"].astype(str) + "||" + m["type"].astype(str)
m_idx = m.set_index("key")[["esco_uri","esco_label_en","score","status","top3"]]
print(f"Match unique keys: {len(m_idx)}", flush=True)

# 加载原始
src = pd.read_csv(SRC, encoding="utf-8-sig")
print(f"Source rows: {len(src)}", flush=True)

# 长表:对每行 job,把 L/K/S/T 列里的每个 span 拆开
out_rows = []
for _, r in src.iterrows():
    job_id = r["id"]
    company = r["企业名称"]
    title = r["招聘岗位"]
    city = r["工作城市"]
    langs = r["匹配的语言"]
    for col in ["L","K","S","T"]:
        v = str(r.get(col) or "")
        if not v or v == "nan" or v == "-": continue
        for s in v.split("；"):
            s = s.strip()
            if not s: continue
            key = f"{s}||{col}"
            if key in m_idx.index:
                mm = m_idx.loc[key]
                if isinstance(mm, pd.DataFrame): mm = mm.iloc[0]  # 多 match 取第一个
                out_rows.append({
                    "job_id": job_id,
                    "company": company,
                    "title": title,
                    "city": city,
                    "matched_languages": langs,
                    "span": s,
                    "type": col,
                    "esco_uri": mm["esco_uri"] if pd.notna(mm["esco_uri"]) else "",
                    "esco_label_en": mm["esco_label_en"] if pd.notna(mm["esco_label_en"]) else "",
                    "score": mm["score"],
                    "status": mm["status"],
                })
            else:
                out_rows.append({
                    "job_id": job_id, "company": company, "title": title, "city": city,
                    "matched_languages": langs, "span": s, "type": col,
                    "esco_uri": "", "esco_label_en": "", "score": 0.0, "status": "no_match",
                })
print(f"Long rows: {len(out_rows)}", flush=True)

df_long = pd.DataFrame(out_rows)
df_long.to_csv(os.path.join(ROOT, "final_match_long.csv"), index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
print(f"Saved: final_match_long.csv", flush=True)

# 统计
print("\n=== Status 分布 ===", flush=True)
print(df_long["status"].value_counts(), flush=True)
print("\n=== By type × status ===", flush=True)
print(pd.crosstab(df_long["type"], df_long["status"]), flush=True)

# 简化版给用户看的:只保留 span+type+esco_uri
df_simple = df_long[["span", "type", "esco_uri", "esco_label_en", "score", "status"]].copy()
df_simple.to_csv(os.path.join(ROOT, "spans_with_esco.csv"), index=False, encoding="utf-8-sig")
print(f"Saved: spans_with_esco.csv", flush=True)
