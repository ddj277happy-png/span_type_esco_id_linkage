# -*- coding: utf-8 -*-
"""用 paraphrase-multilingual-MiniLM-L12-v2 跑跨语种测试"""
import os, time, numpy as np
from sentence_transformers import SentenceTransformer

# 找模型路径
ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\models\models"
import glob
candidates = glob.glob(os.path.join(ROOT, "sentence-transformers*paraphrase*", "snapshots", "master"))
if not candidates:
    raise SystemExit("Model not found")
MODEL_DIR = candidates[0]
print(f"Model: {MODEL_DIR}", flush=True)

print("=== Loading model ===", flush=True)
t0 = time.time()
model = SentenceTransformer(MODEL_DIR, device="cpu")
print(f"Loaded in {time.time()-t0:.1f}s, dim={model.get_embedding_dimension()}", flush=True)

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
    ("故障处理", "troubleshooting"),
    ("工艺流程", "manufacturing process"),
    ("DOE", "design of experiments"),
]
zh = [p[0] for p in pairs]
en = [p[1] for p in pairs]
t1 = time.time()
ez = model.encode(zh, normalize_embeddings=True, show_progress_bar=False, batch_size=16)
ee = model.encode(en, normalize_embeddings=True, show_progress_bar=False, batch_size=16)
elapsed = time.time()-t1
print(f"Encode {len(zh)+len(en)} texts in {elapsed:.1f}s, speed: {(len(zh)+len(en))/elapsed:.0f} t/s\n", flush=True)

sim = ez @ ee.T
print("1-1 cos:", flush=True)
ok = 0
for i, (z, e) in enumerate(pairs):
    c = float(sim[i, i])
    flag = "[+]" if c > 0.7 else ("[~]" if c > 0.5 else "[-]")
    if c > 0.5: ok += 1
    print(f"  {flag} {c:.3f}  {z!r} <-> {e!r}", flush=True)
print(f"\n  > 0.5: {ok}/{len(pairs)}", flush=True)
