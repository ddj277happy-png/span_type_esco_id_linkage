# -*- coding: utf-8 -*-
"""
02_prep_spans.py
读 LKST 4 维标注 CSV,把 L/K/S/T 4 列里的 span 拆开 + 去重
产出 spans_unique.csv: span, type, count

输入:input_data/ 下的任意 *.csv(LKST 11 列,见 data/input_format.md)
输出:data/spans_unique.csv
"""
import csv
import os
import glob
from pathlib import Path

# 项目根目录(脚本在 pipeline/01_数据准备/,向上 2 级)
ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = ROOT / "data"  # 数据约定:输入 CSV 放在 data/ 下
OUT = ROOT / "data" / "spans_unique.csv"

# 优先用环境变量 SKILL_CSV 指定;否则自动找 data/ 下最新的 LKST 标注 csv
# (排除已知非输入文件 + 校验必须含 L/K/S/T 列)
KNOWN_NON_INPUT = {"esco_clean.csv", "spans_unique.csv", "input_sample.csv", "gold_sample.csv", "gold_validated.csv", "tier1_ac_match.csv", "postfix_match.csv"}
REQUIRED_COLS = {"L", "K", "S", "T"}

src_env = os.environ.get("SKILL_CSV")
if src_env:
    SRC = Path(src_env)
else:
    candidates = [p for p in INPUT_DIR.glob("*.csv") if p.name not in KNOWN_NON_INPUT]
    if not candidates:
        raise FileNotFoundError(
            f"data/ 下没找到 LKST 标注 csv(已知数据文件已排除)。"
            f"请把标注 CSV 放到 {INPUT_DIR},"
            f"或用环境变量 SKILL_CSV 指定路径(格式见 data/input_format.md)。"
        )
    # 按 mtime 倒序,逐个校验列名
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    SRC = None
    for c in candidates:
        try:
            with open(c, encoding="utf-8-sig") as f:
                header = f.readline().strip().split(",")
            if REQUIRED_COLS.issubset(set(header)):
                SRC = c
                break
        except Exception:
            continue
    if SRC is None:
        raise FileNotFoundError(
            f"data/ 下没找到含 L/K/S/T 列的 csv。已扫描:{[c.name for c in candidates]}"
        )

print(f"Source: {SRC}")

seen = {}  # (span, type) -> count

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
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["span","type","count"])
    for (s,t),c in sorted(seen.items(), key=lambda x: (x[0][1], -x[1])):
        w.writerow([s, t, c])
print(f"Saved: {OUT}")
