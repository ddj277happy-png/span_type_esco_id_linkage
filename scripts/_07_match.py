# -*- coding: utf-8 -*-
"""
07_match.py
对每个 span,在同 LKST 桶里 cos 找 top-1 ESCO
阈值: cos > 0.75 → matched; 0.5-0.75 → review; < 0.5 → no_match
输出 final_match.csv: span, type, esco_uri, esco_label_en, score, top3_candidates, status
"""
import os, numpy as np, pandas as pd, time, csv

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
EMB = os.path.join(ROOT, "embeddings")
OUT = os.path.join(ROOT, "final_match.csv")

THRESHOLD_HIGH = 0.70
THRESHOLD_LOW  = 0.50

def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            parts = line.split("\t", 1)
            rows.append(parts)
    return rows

all_results = []
for lkst in ["L", "K", "S", "T"]:
    print(f"\n=== {lkst} ===", flush=True)
    e_path = os.path.join(EMB, f"esco_{lkst}_emb.npy")
    s_path = os.path.join(EMB, f"spans_{lkst}_emb.npy")
    em_path = os.path.join(EMB, f"esco_{lkst}_meta.tsv")
    sm_path = os.path.join(EMB, f"spans_{lkst}_meta.tsv")
    if not (os.path.exists(e_path) and os.path.exists(s_path)):
        print(f"  skip (no data)", flush=True)
        continue

    esco_emb = np.load(e_path)
    span_emb = np.load(s_path)
    esco_meta = load_tsv(em_path)  # [[uri, label], ...]
    span_meta = load_tsv(sm_path)  # [[span, count], ...]
    print(f"  ESCO: {esco_emb.shape}, Spans: {span_emb.shape}", flush=True)

    # batch cos (内存 13K*22K=300M float32,一次算可能 OOM,分批)
    t1 = time.time()
    BATCH = 256
    topk = 3
    for i in range(0, len(span_emb), BATCH):
        sb = span_emb[i:i+BATCH]  # (B, 384)
        sim = sb @ esco_emb.T      # (B, N)
        # top-k indices
        idx_top = np.argpartition(-sim, kth=min(topk, sim.shape[1]-1), axis=1)[:, :topk]
        # 排序
        for b in range(sb.shape[0]):
            gi = idx_top[b]
            order = np.argsort(-sim[b, gi])
            gi = gi[order]
            top_scores = sim[b, gi]
            top_uris = [esco_meta[g][0] for g in gi]
            top_labels = [esco_meta[g][1] for g in gi]

            span = span_meta[i+b][0]
            cnt = span_meta[i+b][1]
            best = top_scores[0]
            best_uri = top_uris[0] if best >= THRESHOLD_LOW else ""
            best_label = top_labels[0] if best >= THRESHOLD_LOW else ""
            status = "matched" if best >= THRESHOLD_HIGH else ("review" if best >= THRESHOLD_LOW else "no_match")
            top3_str = " || ".join(f"{u}|{l}|{s:.3f}" for u,l,s in zip(top_uris, top_labels, top_scores))

            all_results.append({
                "span": span,
                "type": lkst,
                "esco_uri": best_uri,
                "esco_label_en": best_label,
                "score": round(float(best), 4),
                "status": status,
                "span_count": cnt,
                "top3": top3_str,
            })
        if (i // BATCH) % 10 == 0:
            print(f"  {i+sb.shape[0]}/{len(span_emb)}  ({time.time()-t1:.1f}s)", flush=True)
    print(f"  Done in {time.time()-t1:.1f}s", flush=True)

# 写
df = pd.DataFrame(all_results)
df.to_csv(OUT, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
print(f"\n=== Final ===", flush=True)
print(f"Total matched: {len(df)}", flush=True)
print(df["status"].value_counts(), flush=True)
print(f"Saved: {OUT}", flush=True)

# 高 confidence 统计
high = df[df["status"] == "matched"]
print(f"\nMatched (score>={THRESHOLD_HIGH}): {len(high)}/{len(df)} = {len(high)/len(df)*100:.1f}%", flush=True)
