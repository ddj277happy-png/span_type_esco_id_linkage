# -*- coding: utf-8 -*-
"""下载 ESCO v1.2.0 英文 CSV(只要这个,不要全语言版)"""
import os, urllib.request, zipfile, ssl

URL = "https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v1.2.0%20-%20classification%20-%20en%20-%20csv.zip"
TARGET_DIR = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\esco"
os.makedirs(TARGET_DIR, exist_ok=True)

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

out = os.path.join(TARGET_DIR, "esco_v1.2.0_en_csv.zip")
print(f"=== Downloading {URL} ===", flush=True)
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
    data = r.read()
    with open(out, "wb") as f:
        f.write(data)
print(f"  Saved: {out} ({len(data)/1e6:.2f} MB)", flush=True)

print("=== Unzipping ===", flush=True)
with zipfile.ZipFile(out, "r") as z:
    for n in z.namelist():
        print(f"  {n}", flush=True)
    z.extractall(TARGET_DIR)
print("Done.", flush=True)
