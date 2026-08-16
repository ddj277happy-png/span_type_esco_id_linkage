# -*- coding: utf-8 -*-
"""Tier 1 字符串匹配 - 高效版"""
import os, re
import pandas as pd
import numpy as np

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
ESCO_CSV = os.path.join(ROOT, "esco_clean.csv")
SPANS_CSV = os.path.join(ROOT, "spans_unique.csv")
OUT = os.path.join(ROOT, "tier1_match.csv")

esco = pd.read_csv(ESCO_CSV, encoding="utf-8-sig")
spans = pd.read_csv(SPANS_CSV, encoding="utf-8-sig")

# 展开 ESCO 词典:每个 altLabel/preferredLabel + type
esco_dict = {}  # norm_label -> (uri, label, lkst)
for _, r in esco.iterrows():
    lbl = str(r["preferred_label"] or "")
    alts = str(r.get("alt_labels","") or "").replace("\n","|").split("|")
    for a in [lbl] + alts:
        a = re.sub(r"\s+", " ", a.lower().strip())
        if not a: continue
        if a not in esco_dict:
            esco_dict[a] = (r["uri"], lbl, r["lkst"])
print(f"ESCO dict: {len(esco_dict)} entries", flush=True)

# 全部 token 列表(按长度倒序,优先匹配长的)
tokens = sorted(esco_dict.keys(), key=len, reverse=True)
print(f"Total tokens: {len(tokens)}", flush=True)

# 准备 spans 字符串列表 + lkst
span_texts = [str(s) for s in spans["span"].tolist()]
span_types = spans["type"].tolist()
span_counts = spans["count"].tolist()

# Tier 1: 扫 token,在 span_texts 里找包含它的(反之亦然)
# 高效:用 set 存 span 字符串,找交集
import time
t0 = time.time()

# 先做"span 包含 ESCO token" 匹配
# 把所有 span 转成 set
spans_set = set(span_texts)
hits = {}  # span -> (uri, label, lkst, kind)
# 遍历 ESCO tokens (短的先,因为短 token 是高密度)
for tok in tokens:
    uri, lbl, lkst_e = esco_dict[tok]
    # 找 span 是否包含 tok(做大小写不敏感)
    for s in span_texts:
        if tok in s.lower():
            # 检查 lkst 一致
            i = span_texts.index(s) if s in span_texts else -1
            if i < 0: continue
            lkst_s = span_types[i]
            if lkst_s == lkst_e and (s, lkst_s) not in hits:
                hits[(s, lkst_s)] = (uri, lbl, lkst_e, "contain", 0.95)
            elif (s, lkst_s) not in hits:
                # 跨 lkst 也记,但分数低
                hits[(s, lkst_s)] = (uri, lbl, lkst_e, "contain_cross", 0.7)
    # 进度
    if len(toks_done := [t for t in tokens if t in hits]) % 1000 == 0:
        pass  # 太慢
print(f"Token scan done in {time.time()-t0:.1f}s, hits: {len(hits)}", flush=True)

# 写
out_rows = []
for (s, t), (uri, lbl, lkst_e, kind, sc) in hits.items():
    out_rows.append({"span": s, "type": t, "esco_uri": uri, "esco_label_en": lbl,
                     "esco_lkst": lkst_e, "score": sc, "match_kind": kind})
df = pd.DataFrame(out_rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"Saved: {OUT} ({len(df)} rows)", flush=True)
print(df["match_kind"].value_counts(), flush=True)
