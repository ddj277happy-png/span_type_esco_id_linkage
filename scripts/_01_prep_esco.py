# -*- coding: utf-8 -*-
"""
01_prep_esco.py
读 ESCO 英文 CSV,产出干净版 esco_clean.csv
列:uri, preferred_label, alt_labels (join), description, skill_type, reuse_level, lkst_mapping
"""
import csv, os
DIR = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\esco"
OUT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\esco_clean.csv"

def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

# 主表:skills_en.csv (含 skill + knowledge)
rows = load(os.path.join(DIR, "skills_en.csv"))
print(f"skills_en.csv: {len(rows)} rows")

# 集合类:语言和横向能力
lang = {r["conceptUri"] for r in load(os.path.join(DIR, "languageSkillsCollection_en.csv"))}
trans = {r["conceptUri"] for r in load(os.path.join(DIR, "transversalSkillsCollection_en.csv"))}
print(f"language URIs: {len(lang)}")
print(f"transversal URIs: {len(trans)}")

# 构建 clean 表
out_rows = []
for r in rows:
    uri = r["conceptUri"]
    pref = r["preferredLabel"].strip()
    alts = r.get("altLabels", "").replace("\n", " | ").strip()
    desc = r.get("description", "").strip()
    st = r.get("skillType", "").strip()
    rl = r.get("reuseLevel", "").strip()

    # 映射到 LKST
    if uri in lang:
        lkst = "L"
    elif st == "knowledge":
        lkst = "K"
    elif uri in trans or rl == "transversal":
        lkst = "T"
    else:
        lkst = "S"

    out_rows.append({
        "uri": uri,
        "preferred_label": pref,
        "alt_labels": alts,
        "description": desc,
        "skill_type": st,
        "reuse_level": rl,
        "lkst": lkst,
    })

# 统计 LKST 分布
dist = {}
for r in out_rows:
    dist[r["lkst"]] = dist.get(r["lkst"], 0) + 1
print(f"LKST 分布: {dist}")

# 写
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["uri","preferred_label","alt_labels","description","skill_type","reuse_level","lkst"])
    w.writeheader()
    w.writerows(out_rows)
print(f"Saved: {OUT} ({len(out_rows)} rows)")
