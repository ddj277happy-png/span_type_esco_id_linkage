# -*- coding: utf-8 -*-
"""
04_smoke.py
用已下的 bge-small-zh-v1.5 跑跨语种 smoke test
看 bge 实际能不能把中文 span 和英文 ESCO 拉近
"""
import os, time, numpy as np
from sentence_transformers import SentenceTransformer

MODEL_DIR = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\models\models\BAAI--bge-small-zh-v1.5\snapshots\master"
print("=== Loading model ===", flush=True)
t0 = time.time()
model = SentenceTransformer(MODEL_DIR, device="cpu")
print(f"Loaded in {time.time()-t0:.1f}s, dim={model.get_sentence_embedding_dimension()}", flush=True)

# 跨语种
print("\n=== Cross-lingual smoke test ===", flush=True)
pairs = [
    ("英语四级", "English CET-4"),
    ("英语四级", "English language proficiency"),
    ("英语口语", "spoken English"),
    ("Python 编程", "Python programming"),
    ("沟通能力", "communication skills"),
    ("团队协作", "teamwork"),
    ("会计记账", "bookkeeping"),
    ("液压系统", "hydraulic system"),
    ("SPC", "statistical process control"),
    ("PFMEA", "process failure mode and effects analysis"),
    ("精益六西格玛", "lean six sigma"),
    ("8D 报告", "8D report"),
    ("英语六级", "College English Test Band 6"),
    ("日语 N1", "Japanese Language Proficiency Test N1"),
    ("韩语", "Korean language"),
]
zh = [p[0] for p in pairs]
en = [p[1] for p in pairs]
t1 = time.time()
ez = model.encode(zh, normalize_embeddings=True, show_progress_bar=False, batch_size=8)
ee = model.encode(en, normalize_embeddings=True, show_progress_bar=False, batch_size=8)
print(f"Encode {len(zh)+len(en)} texts in {time.time()-t1:.1f}s", flush=True)
print(f"Speed: {len(zh)/(time.time()-t1)*2:.1f} texts/sec\n", flush=True)

# 1-1 cos
print("1-1 对应 cos (期望越高越好):", flush=True)
sim = ez @ ee.T
diagonal_max = 0
for i, (z, e) in enumerate(pairs):
    c = float(sim[i, i])
    diagonal_max += 1 if np.argmax(sim[i]) == i else 0
    flag = "[+]" if c > 0.7 else ("[~]" if c > 0.5 else "[-]")
    print(f"  {flag} {c:.3f}  {z!r} <-> {e!r}", flush=True)
print(f"\n对角线最大: {diagonal_max}/{len(pairs)}", flush=True)
