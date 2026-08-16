# -*- coding: utf-8 -*-
"""
14_review_sample.py
抽 review 桶的样本,生成手动审核文件
- 每 type 抽 40 条
- 格式: span, type, top-1 (label, score), top-2, top-3
- 留空列让用户标记 [Y/N/?]
"""
import os
import pandas as pd
import numpy as np

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
EMB = os.path.join(ROOT, "embeddings")
OUT = os.path.join(ROOT, "review_sample.md")

# 加载 v2 状态
m = pd.read_csv(os.path.join(ROOT, "final_match_v2.csv"), encoding="utf-8-sig")
review = m[m["status"] == "review"].copy()
print(f"Total review: {len(review)}", flush=True)

# 拆 top3 候选
def parse_top3(s):
    if not isinstance(s, str): return []
    parts = s.split(" || ")
    out = []
    for p in parts:
        try:
            uri, label, score = p.rsplit("|", 2)
            out.append((uri, label, float(score)))
        except Exception:
            continue
    return out

review["top3_parsed"] = review["top3"].apply(parse_top3)

# 加载 ESCO 候选 uri → label 映射(供 top2/top3 显示)
esco = pd.read_csv(os.path.join(ROOT, "esco_clean.csv"), encoding="utf-8-sig")
esco_idx = esco.set_index("uri")["preferred_label"].to_dict()

# 每 type 随机抽 40 条(若有)
np.random.seed(42)
samples = []
for lkst in ["L", "K", "S", "T"]:
    sub = review[review["type"] == lkst]
    n = min(40, len(sub))
    if n == 0:
        continue
    s = sub.sample(n=n, random_state=42)
    samples.append(s)
    print(f"  {lkst}: {n} sampled", flush=True)
sample_df = pd.concat(samples, ignore_index=True)

# 写 markdown 表格
md = ["# 人工审核样本 (review 状态,共 {} 条)\n".format(len(sample_df))]
md.append("**判定规则:**")
md.append("- [Y] 正确: top-1 是合理匹配")
md.append("- [N] 错误: top-1 不对,看 top-2/3 有没有对的")
md.append("- [?] 不确定: 难判断\n")
md.append("---\n")

for _, r in sample_df.iterrows():
    md.append(f"### {r['type']} | score={r['score']:.3f} | `[{r['span']}]` (×{r['span_count']} 出现)\n")
    t3 = r["top3_parsed"]
    if not t3: continue
    md.append(f"- **top-1** ({t3[0][2]:.3f}): {t3[0][1]}  → `{t3[0][0]}`")
    if len(t3) > 1:
        md.append(f"- top-2 ({t3[1][2]:.3f}): {t3[1][1]}  → `{t3[1][0]}`")
    if len(t3) > 2:
        md.append(f"- top-3 ({t3[2][2]:.3f}): {t3[2][1]}  → `{t3[2][0]}`")
    md.append(f"\n**判定**: [ ] Y / [ ] N / [ ] ?\n")
    md.append("---\n")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"\nSaved: {OUT}", flush=True)
print(f"Total reviewed: {len(sample_df)}", flush=True)
