# -*- coding: utf-8 -*-
"""
10_tier1.py
在 embedding 之前,先做 Tier 1 字符串匹配:
- span 直接出现在 ESCO altLabel/preferredLabel (大小写不敏感)
- span 包含 altLabel 或被 altLabel 包含
命中:直接给 ESCO URI,score=1.0
"""
import os, csv, re
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
ESCO_CSV = os.path.join(ROOT, "esco_clean.csv")
SPANS_CSV = os.path.join(ROOT, "spans_unique.csv")
OUT = os.path.join(ROOT, "tier1_match.csv")

# 加载 ESCO
esco = pd.read_csv(ESCO_CSV, encoding="utf-8-sig")
print(f"ESCO: {len(esco)}", flush=True)

# 构造检索 index
# 方式 1: altLabel 拆开成 token → uri map (处理 "manage staff of music" 这种)
# 方式 2: 全字符串检索
def normalize(s):
    return re.sub(r"\s+", " ", s.lower().strip())

# 字典: token → [(uri, label, type), ...]
token_idx = {}
for _, r in esco.iterrows():
    uri = r["uri"]
    lbl = r["preferred_label"]
    lkst = r["lkst"]
    # 拆 altLabel
    alts = str(r.get("alt_labels","") or "").replace("\n","|").split("|")
    for a in alts + [lbl]:
        a = normalize(str(a))
        if not a: continue
        token_idx.setdefault(a, []).append((uri, lbl, lkst))
print(f"Token index: {len(token_idx)} unique tokens", flush=True)

# 加载 spans
spans = pd.read_csv(SPANS_CSV, encoding="utf-8-sig")
print(f"Spans: {len(spans)}", flush=True)

# 字符串匹配
matches = {}
miss = 0
for _, r in spans.iterrows():
    s = str(r["span"])
    sn = normalize(s)
    lkst = r["type"]
    cnt = r["count"]

    # 精确匹配
    if sn in token_idx:
        for uri, lbl, lkst_e in token_idx[sn]:
            if lkst_e == lkst:
                matches[(s, lkst)] = (uri, lbl, "exact", 1.0)
                break
        else:
            # fallback: 不分 lkst
            uri, lbl, lkst_e = token_idx[sn][0]
            matches[(s, lkst)] = (uri, lbl, "exact_cross_lkst", 1.0)
        continue
    miss += 1
print(f"Exact matches: {len(matches)}/{len(spans)}, miss: {miss}", flush=True)

# 看下 top miss 能否做部分匹配(简化版:只做"包含"匹配,span 是 ESCO token 的子串)
contain_matches = {}
for tok, candidates in token_idx.items():
    if len(tok) < 3: continue
    for _, r in spans.iterrows():
        s = str(r["span"])
        sn = normalize(s)
        if len(sn) < 2: continue
        if sn in tok or tok in sn:  # 包含关系
            for uri, lbl, lkst_e in candidates:
                if lkst_e == r["type"]:
                    contain_matches[(s, r["type"])] = (uri, lbl, "contain", 0.9)
                    break
print(f"Contain matches added: {len(contain_matches)}", flush=True)
matches.update(contain_matches)

# 写
out_rows = []
for (s, t), (uri, lbl, kind, sc) in matches.items():
    out_rows.append({"span": s, "type": t, "esco_uri": uri, "esco_label_en": lbl,
                     "score": sc, "match_kind": kind})
df = pd.DataFrame(out_rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"Saved: {OUT} ({len(df)} rows)", flush=True)
print(df["match_kind"].value_counts(), flush=True)
