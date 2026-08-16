# -*- coding: utf-8 -*-
"""
02_prep_spans.py
读组员的 step3 CSV,把 L/K/S/T 4 列里的 span 拆开 + 去重
产出 spans_unique.csv: span, type, count
"""
import csv
SRC = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\step3_skill_annotation_20260810_012339.csv"
OUT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\spans_unique.csv"

seen = {}  # (span, type) -> count
empty_in_col = {"-": True, "": True, None: True}

with open(SRC, encoding="utf-8-sig") as f:
    rdr = csv.DictReader(f)
    n_rows = 0
    for r in rdr:
        n_rows += 1
        for t in ("L","K","S","T"):
            v = (r.get(t) or "").strip()
            if not v or v == "-":
                continue
            for s in v.split("；"):  # 中文分号
                s = s.strip()
                if s:
                    key = (s, t)
                    seen[key] = seen.get(key, 0) + 1

print(f"Source rows: {n_rows}")
print(f"Unique (span, type) pairs: {len(seen)}")

# 按 type 统计
by_t = {}
for (s,t),c in seen.items():
    by_t[t] = by_t.get(t,0) + 1
print(f"By type: {by_t}")

# Top 10 高频
top = sorted(seen.items(), key=lambda x: -x[1])[:10]
print("Top 10:")
for (s,t),c in top:
    print(f"  {t}: {s!r}  ×{c}")

# 写
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["span","type","count"])
    for (s,t),c in sorted(seen.items(), key=lambda x: (x[0][1], -x[1])):
        w.writerow([s, t, c])
print(f"Saved: {OUT}")
