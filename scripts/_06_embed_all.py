# -*- coding: utf-8 -*-
"""
06_embed_all.py
按 LKST 分桶,把 ESCO + spans 各自 encode 后存成 .npy
- ESCO: 13,939 条 → 4 个 .npy
- Spans: 31,866 条 → 4 个 .npy
"""
import os, time, glob, numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
MODELS = os.path.join(ROOT, "models", "models")
MODEL_DIR = glob.glob(os.path.join(MODELS, "sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2", "snapshots", "*"))[0]

OUT_DIR = os.path.join(ROOT, "embeddings")
os.makedirs(OUT_DIR, exist_ok=True)

print("=== Loading model ===", flush=True)
t0 = time.time()
model = SentenceTransformer(MODEL_DIR, device="cpu")
print(f"Loaded in {time.time()-t0:.1f}s, dim={model.get_embedding_dimension()}", flush=True)

def encode_to_file(texts, out_path, batch_size=64):
    t1 = time.time()
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False,
                       batch_size=batch_size, convert_to_numpy=True)
    np.save(out_path, emb)
    elapsed = time.time() - t1
    print(f"  {len(texts)} texts → {out_path}  shape={emb.shape}  time={elapsed:.1f}s  speed={len(texts)/elapsed:.0f} t/s", flush=True)
    return emb

# ---------- ESCO ----------
print("\n=== ESCO embeddings (13,939) ===", flush=True)
esco = pd.read_csv(os.path.join(ROOT, "esco_clean.csv"), encoding="utf-8-sig")
# 构造 embedding 文本: prefLabel + altLabels(英文)
esco["text"] = esco["preferred_label"].fillna("") + " | " + esco["alt_labels"].fillna("").str.replace("|", " | ", regex=False)
esco["text"] = esco["text"].str.strip(" |")
print(f"ESCO unique texts: {esco['text'].nunique()}", flush=True)

# 按 lkst 分桶编码
for lkst in ["L", "K", "S", "T"]:
    sub = esco[esco["lkst"] == lkst]
    if len(sub) == 0:
        continue
    texts = sub["text"].tolist()
    uris = sub["uri"].tolist()
    pref = sub["preferred_label"].tolist()
    encode_to_file(texts, os.path.join(OUT_DIR, f"esco_{lkst}_emb.npy"))
    # 保存 uri 顺序,跟 embedding 对齐
    with open(os.path.join(OUT_DIR, f"esco_{lkst}_meta.tsv"), "w", encoding="utf-8") as f:
        for u, p in zip(uris, pref):
            f.write(f"{u}\t{p}\n")
    print(f"  meta saved: esco_{lkst}_meta.tsv ({len(uris)} rows)", flush=True)

# ---------- Spans ----------
print("\n=== Spans embeddings (31,866) ===", flush=True)
spans = pd.read_csv(os.path.join(ROOT, "spans_unique.csv"), encoding="utf-8-sig")
print(f"Total unique spans: {len(spans)}", flush=True)
print(f"By type: {spans['type'].value_counts().to_dict()}", flush=True)

for lkst in ["L", "K", "S", "T"]:
    sub = spans[spans["type"] == lkst]
    if len(sub) == 0:
        continue
    texts = sub["span"].tolist()
    counts = sub["count"].tolist()
    encode_to_file(texts, os.path.join(OUT_DIR, f"spans_{lkst}_emb.npy"))
    with open(os.path.join(OUT_DIR, f"spans_{lkst}_meta.tsv"), "w", encoding="utf-8") as f:
        for t, c in zip(texts, counts):
            f.write(f"{t}\t{c}\n")
    print(f"  meta saved: spans_{lkst}_meta.tsv ({len(texts)} rows)", flush=True)

print("\n=== All done ===", flush=True)
