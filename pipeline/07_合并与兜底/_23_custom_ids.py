# -*- coding: utf-8 -*-
"""
23_custom_ids.py
给 final_match_v6 里 status=no_match 的 span 造 custom:{type}/{hash} ID
- hash 用 SHA1(span+type) 截前 12 字符,稳定
- format: custom:skill/{hash}, custom:knowledge/{hash}, custom:language/{hash}, custom:transversal/{hash}
- 写 final_match_v7.csv + final_match_long.csv + spans_with_esco.csv
"""
import os, csv, hashlib
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V6 = os.path.join(ROOT, "final_match_v6.csv")
OUT = os.path.join(ROOT, "final_match_v7.csv")
SRC = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\input_data\step3_skill_annotation_20260810_012339.csv"

PREFIX = {
    "L": "custom:language/",
    "K": "custom:knowledge/",
    "S": "custom:skill/",
    "T": "custom:transversal/",
}

def make_custom_uri(span, lkst):
    h = hashlib.sha1(f"{span}|{lkst}".encode("utf-8")).hexdigest()[:12]
    return PREFIX[lkst] + h, h

m = pd.read_csv(V6, encoding="utf-8-sig")
print(f"v6 loaded: {len(m)}", flush=True)
print(f"Status dist before:", flush=True)
print(m["status"].value_counts(), flush=True)

# 给 no_match 造 ID
n = 0
for idx, r in m.iterrows():
    if r["status"] == "no_match" or (r["status"] == "review" and pd.isna(r.get("esco_uri")) or r.get("esco_uri")==""):
        uri, h = make_custom_uri(r["span"], r["type"])
        m.at[idx, "esco_uri"] = uri
        m.at[idx, "status"] = "no_match"  # 仍是 no_match
        m.at[idx, "esco_label_en"] = f"[CUSTOM] {r['span']} (self-defined)"
        n += 1
print(f"\nGenerated {n} custom IDs", flush=True)

# 验证 uniqueness
custom_uris = m[m["status"]=="no_match"]["esco_uri"]
print(f"Unique custom URIs: {custom_uris.nunique()}/{len(custom_uris)}", flush=True)

# 写 v7
m.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)

# 长表
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
print(f"Saved: final_match_long.csv ({len(df_long)} rows)", flush=True)

df_simple = df_long[["span", "type", "esco_uri", "esco_label_en", "score", "status"]].copy()
df_simple.to_csv(os.path.join(ROOT, "spans_with_esco.csv"), index=False, encoding="utf-8-sig")
print(f"Saved: spans_with_esco.csv", flush=True)
print(df_simple["status"].value_counts(), flush=True)
