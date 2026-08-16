# -*- coding: utf-8 -*-
"""下载 bge-m3 模型 + 跑一个跨语种对齐 smoke test"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")
import time

print("=== Loading model BAAI/bge-m3 ===", flush=True)
t0 = time.time()
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3", device="cpu")
print(f"Loaded in {time.time()-t0:.1f}s", flush=True)
print(f"Model dim: {model.get_sentence_embedding_dimension()}", flush=True)

# 跨语种 smoke test
print("\n=== Smoke test: zh vs en ===", flush=True)
pairs = [
    ("英语四级", "English CET-4"),
    ("英语四级", "English language proficiency"),
    ("Python 编程", "Python programming"),
    ("沟通能力", "communication skills"),
    ("会计记账", "bookkeeping accounting"),
    ("液压系统", "hydraulic system"),
]
import numpy as np
zh = [p[0] for p in pairs]
en = [p[1] for p in pairs]
t1 = time.time()
ez = model.encode(zh, normalize_embeddings=True, show_progress_bar=False)
ee = model.encode(en, normalize_embeddings=True, show_progress_bar=False)
print(f"Encode {len(zh)+len(en)} texts in {time.time()-t1:.1f}s", flush=True)

# 1-1 对应 cos
print("\n1-1 对应 cos:")
for (z, e), vz, ve in zip(pairs, ez, ee):
    c = float(np.dot(vz, ve))
    flag = "✓" if c > 0.7 else ("≈" if c > 0.5 else "✗")
    print(f"  {flag} {c:.3f}  zh={z!r}  en={e!r}")

# 交叉矩阵看是否对角线最大
print("\n交叉矩阵 (行=zh, 列=en):")
sim = ez @ ee.T
for i, z in enumerate(zh):
    row = "  ".join(f"{sim[i,j]:.3f}" for j in range(len(en)))
    print(f"  {z:<12}  {row}")
