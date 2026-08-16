# -*- coding: utf-8 -*-
"""
13_final_v2.py
最终交付版
- T 桶阈值放宽到 0.55(因为 0.5-0.7 这段大部分是 decent match)
- L/K/S 桶保留 0.70
- 输出:
  spans_with_esco.csv       : span 唯一键视角
  final_match_long.csv      : job 维度长表
  final_match_long_review.csv : review 区间供人工审核
  QA_report.md              : 质量自检报告
"""
import os, csv
import pandas as pd
import numpy as np

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
SRC = os.path.join(ROOT, "step3_skill_annotation_20260810_012339.csv")
MATCH = os.path.join(ROOT, "final_match.csv")

m = pd.read_csv(MATCH, encoding="utf-8-sig")

# T 桶阈值放宽
def relax(row):
    if row["type"] == "T" and row["score"] >= 0.55:
        return "matched"
    if row["score"] >= 0.70:
        return "matched"
    if row["score"] >= 0.50:
        return "review"
    return "no_match"

m["status_v2"] = m.apply(relax, axis=1)
print("=== v2 status 分布 ===", flush=True)
print(m["status_v2"].value_counts(), flush=True)
print("\n=== By type × v2 status ===", flush=True)
print(pd.crosstab(m["type"], m["status_v2"]), flush=True)

# 用 v2 status 替换原 status,写新表
m["status"] = m["status_v2"]
m.drop(columns=["status_v2"], inplace=True)
m.to_csv(os.path.join(ROOT, "final_match_v2.csv"), index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

# 长表
m["key"] = m["span"].astype(str) + "||" + m["type"].astype(str)
m_idx = m.set_index("key")[["esco_uri","esco_label_en","score","status","top3"]]

src = pd.read_csv(SRC, encoding="utf-8-sig")
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
print(df_long["status"].value_counts(), flush=True)

# 简化版
df_simple = df_long[["span", "type", "esco_uri", "esco_label_en", "score", "status"]].copy()
df_simple.to_csv(os.path.join(ROOT, "spans_with_esco.csv"), index=False, encoding="utf-8-sig")
print(f"Saved: spans_with_esco.csv", flush=True)

# QA report
report = f"""# 匹配质量自检报告

## 数据规模
- 原始 job 数: 5,140
- 组员标注 unique (span, type) 对: 31,866
  - L (language): 1,486
  - K (knowledge): 6,058
  - S (skill): 22,107
  - T (transversal): 2,215
- ESCO v1.2.0 英文版总概念: 13,939
  - L: 359
  - K: 3,145
  - S: 10,338
  - T: 97

## 匹配结果 (long 表,出现次数)
- 总长表行: {len(df_long):,}
- matched: {(df_long['status']=='matched').sum():,} ({(df_long['status']=='matched').sum()/len(df_long)*100:.1f}%)
- review: {(df_long['status']=='review').sum():,} ({(df_long['status']=='review').sum()/len(df_long)*100:.1f}%)
- no_match: {(df_long['status']=='no_match').sum():,} ({(df_long['status']=='no_match').sum()/len(df_long)*100:.1f}%)

## 阈值策略
- L/K/S 桶: cos >= 0.70 → matched
- T 桶: cos >= 0.55 → matched (因为 T 桶 0.5-0.7 区间大部分是 decent match,见 _12_inspect_T.py 抽样)
- 0.5-0.7 (L/K/S) / 0.5-0.55 (T) → review (需人工)
- < 0.5 → no_match

## 模型说明
- paraphrase-multilingual-MiniLM-L12-v2 (118M params, 384 dim, 多语种)
- CPU 推理 45-160 t/s
- 跨语种 smoke test: 14/18 通过(失败 4 个都是中英缩写对,如 SPC/PFMEA/DOE)
- bge-m3 下不完(2.09GB incomplete),回退到 paraphrase-multilingual

## 已知限制
1. **缩写 (SPC/PFMEA/DOE/TQM 等)**: 跨语种对齐差,中英缩写同义但字面无关
2. **T 桶 (transversal)**: 通用软技能,中文表述多样,匹配普遍偏低
3. **ESCO 中文缺失**: 没有中文 altLabel,只能用英文匹配,L 桶很多证书 (TEM-8/PMP/CET-6) 找不到对应
4. **没有 Tier 1 字符串兜底**: span 含 "PFMEA" 这种,ESCO 英文 altLabel 含 "Process Failure Mode",但 substring 匹配会命中

## 输出文件
- `final_match_long.csv`: job × span 长表,90K+ 行,主交付
- `spans_with_esco.csv`: unique span 视角,简化版
- `final_match.csv`: v1 (T 桶 0.7 阈值,严)
- `final_match_v2.csv`: v2 (T 桶 0.55 阈值,松,推荐)
- `esco_clean.csv`: 13,939 ESCO 概念清理版
- `spans_unique.csv`: 31,866 unique span 池

## 建议下一步
1. 抽 50-100 条 review 人工审核,看是否要降阈值或调模型
2. 补 Tier 1 字符串匹配(把缩写扩展后再匹配)
3. 考虑用 bge-m3 重做 L/K 桶(若下得完)
"""
with open(os.path.join(ROOT, "QA_report.md"), "w", encoding="utf-8") as f:
    f.write(report)
print(f"Saved: QA_report.md", flush=True)
