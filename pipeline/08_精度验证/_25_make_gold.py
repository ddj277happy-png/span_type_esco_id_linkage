# -*- coding: utf-8 -*-
"""
25_make_gold.py
从 final_match_v7 抽 200 条 gold 评估样本
分层:L/K/S/T × {matched, no_match} = 8 桶,每桶 25 条 = 200
输出 gold_sample.csv 含:span, type, our_uri, our_label, job 上下文, 留空列让用户填 gold
"""
import os, csv
import pandas as pd
import numpy as np

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V7 = os.path.join(ROOT, "final_match_v7.csv")
SRC = os.path.join(ROOT, "input_data", "step3_skill_annotation_20260810_012339.csv")
OUT = os.path.join(ROOT, "gold_sample.csv")

v7 = pd.read_csv(V7, encoding="utf-8-sig")
src = pd.read_csv(SRC, encoding="utf-8-sig")
print(f"v7: {len(v7)}, src: {len(src)}", flush=True)

# 把 v7 span/type 跟原 step3 对齐,提取 job 上下文
# v7 的 span 来源于 step3, 可以通过 (job_id 中,这个 span 是否在该 job 里出现) 找
# 简化:用 src 的 (id, span_text) 索引

# 把 src 转成 dict: (id, l/k/s/t) -> 列内容
# 这样 gold 里能给每条 span 配 job 上下文
src_idx = src.set_index("id")[["企业名称","招聘岗位","工作城市","匹配的语言","标注文本"]].to_dict(orient="index")

# 给 v7 加 job_id 字段(通过 span 在原 job 里出现来定位)
# 简化:先只标注 span/type/job_id 引用,gold 表格里通过 v7 的 span 在 src 的 "标注文本"里查找
# 但跨多个 job,效率低。改用"出现频次最高"的 job 作为参考

np.random.seed(42)
samples = []
for lkst in ["L", "K", "S", "T"]:
    for status in ["matched", "no_match"]:
        sub = v7[v7["status"] == status]
        sub = sub[sub["type"] == lkst]
        if len(sub) == 0:
            print(f"  Skip {lkst}/{status} (empty)", flush=True)
            continue
        n = min(25, len(sub))
        s = sub.sample(n=n, random_state=42)
        samples.append(s)
        print(f"  {lkst}/{status}: {n} (from {len(sub)})", flush=True)

gold = pd.concat(samples, ignore_index=True)
print(f"\nTotal gold sample: {len(gold)}", flush=True)

# 写 gold CSV
out_rows = []
for idx, r in gold.iterrows():
    # 找原始 job(简单方式:这个 span 出现在 src 的哪个 job 的对应列里)
    # 走一遍 src,找到第一个匹配
    job_id = ""
    company = ""
    title = ""
    city = ""
    langs = ""
    context_text = ""
    s = str(r["span"])
    t = r["type"]
    # 优化:用随机抽样 + 第一个匹配
    for _, src_row in src.iterrows():
        col = src_row[t] if t in src_row else ""
        if pd.isna(col) or not col:
            continue
        if s in str(col).split("；"):
            job_id = src_row["id"]
            company = src_row["企业名称"]
            title = src_row["招聘岗位"]
            city = src_row["工作城市"]
            langs = src_row["匹配的语言"]
            context_text = str(src_row.get("标注文本", ""))[:200]  # 截 200 字
            break
    out_rows.append({
        "gold_id": idx + 1,
        "span": s,
        "type": t,
        "our_status": r["status"],
        "our_uri": r["esco_uri"],
        "our_label": r["esco_label_en"],
        "our_score": r["score"],
        "job_id": job_id,
        "company": company,
        "title": title,
        "city": city,
        "langs": langs,
        "context": context_text,
        # 留空让你填
        "judgment": "",   # Y / N / ?
        "gold_uri": "",    # 正确的 ESCO URI;如果无匹配填 NO_MATCH
        "gold_notes": "",  # 备注
    })

df_out = pd.DataFrame(out_rows)
df_out.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT} ({len(df_out)} rows)", flush=True)
print(f"Columns: {list(df_out.columns)}", flush=True)
print("\n=== Status × Type 分布 ===")
print(pd.crosstab(df_out["type"], df_out["our_status"]), flush=True)
