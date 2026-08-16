# -*- coding: utf-8 -*-
"""bge-m3 跨语种 smoke test + 速度估算"""
import os, time, glob
ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\models\models"
candidates = glob.glob(os.path.join(ROOT, "BAAI--bge-m3", "snapshots", "*"))
if not candidates:
    raise SystemExit("bge-m3 not found")
MODEL_DIR = candidates[0]
print(f"Model: {MODEL_DIR}", flush=True)

t0 = time.time()
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(MODEL_DIR, device="cpu")
print(f"Loaded in {time.time()-t0:.1f}s, dim={model.get_embedding_dimension()}", flush=True)

pairs = [
    ("英语四级", "English CET-4"),
    ("Python 编程", "Python programming"),
    ("沟通能力", "communication skills"),
    ("SPC", "statistical process control"),
    ("PFMEA", "process failure mode and effects analysis"),
    ("精益六西格玛", "lean six sigma"),
    ("DOE", "design of experiments"),
    ("英语六级", "College English Test Band 6"),
    ("液压系统", "hydraulic system"),
    ("日语 N1", "Japanese Language Proficiency Test N1"),
]
zh = [p[0] for p in pairs]
en = [p[1] for p in pairs]

t1 = time.time()
ez = model.encode(zh, normalize_embeddings=True, show_progress_bar=False, batch_size=8)
ee = model.encode(en, normalize_embeddings=True, show_progress_bar=False, batch_size=8)
elapsed = time.time()-t1
print(f"Encode {len(zh)+len(en)} texts in {elapsed:.1f}s, speed: {(len(zh)+len(en))/elapsed:.0f} t/s\n", flush=True)

sim = ez @ ee.T
ok = 0
for i, (z, e) in enumerate(pairs):
    c = float(sim[i, i])
    if c > 0.5: ok += 1
    flag = "[+]" if c > 0.7 else ("[~]" if c > 0.5 else "[-]")
    print(f"  {flag} {c:.3f}  {z!r} <-> {e!r}", flush=True)
print(f"\n  > 0.5: {ok}/{len(pairs)}", flush=True)

print(f"\n预估全量时间: 45000 文本 / {(len(zh)+len(en))/elapsed:.0f} t/s = {45000/((len(zh)+len(en))/elapsed)/60:.1f} 分钟", flush=True)
