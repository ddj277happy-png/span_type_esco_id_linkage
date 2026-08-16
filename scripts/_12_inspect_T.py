# -*- coding: utf-8 -*-
"""T 桶专项看"""
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
m = pd.read_csv(f"{ROOT}/final_match.csv", encoding="utf-8-sig")
T = m[m["type"]=="T"].sort_values("score", ascending=False)

print(f"T 桶总数: {len(T)}", flush=True)
print(f"  matched (>=0.7): {(T['score']>=0.7).sum()}", flush=True)
print(f"  review (0.5-0.7): {((T['score']>=0.5)&(T['score']<0.7)).sum()}", flush=True)
print(f"  no_match (<0.5): {(T['score']<0.5).sum()}", flush=True)

print("\n=== T 桶 top 20 (高分) ===", flush=True)
for _, r in T.head(20).iterrows():
    print(f"  {r['score']:.3f}  {r['span']!r}  → {r['esco_label_en']!r}", flush=True)

print("\n=== T 桶 0.5-0.7 区间 30 条 ===", flush=True)
mid = T[(T['score']>=0.5)&(T['score']<0.7)].sort_values("score", ascending=False).head(30)
for _, r in mid.iterrows():
    print(f"  {r['score']:.3f}  {r['span']!r}  → {r['esco_label_en']!r}", flush=True)
