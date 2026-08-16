# -*- coding: utf-8 -*-
"""下载 ESCO v1.2.0 RDF (走真正的 download 链接)"""
import os, urllib.request, zipfile, time, ssl

# 从 confirmation 页面提取的真实下载链接(全语言 RDF)
URL = "https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v1.2.0%20-%20classification%20-%20%20-%20rdf.zip"

TARGET_DIR = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\esco"
os.makedirs(TARGET_DIR, exist_ok=True)

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

def download(url, target):
    print(f"=== {url} ===", flush=True)
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600, context=SSL_CTX) as r:
        ct = r.headers.get("Content-Type", "")
        cl = r.headers.get("Content-Length", "?")
        print(f"  Content-Type: {ct}, Content-Length: {cl}", flush=True)
        got = 0
        with open(target, "wb") as f:
            while True:
                chunk = r.read(64 * 1024)
                if not chunk: break
                f.write(chunk)
                got += len(chunk)
                if cl != "?":
                    pct = got * 100 / int(cl)
                    print(f"\r  {got/1e6:.1f}/{int(cl)/1e6:.1f} MB ({pct:.1f}%)", end="", flush=True)
        print(f"\n  Done in {time.time()-t0:.1f}s, {got/1e6:.2f} MB", flush=True)

if __name__ == "__main__":
    out = os.path.join(TARGET_DIR, "esco_v1.2.0_rdf.zip")
    download(URL, out)
    print(f"Saved: {out}", flush=True)
    # 解压
    print("=== Unzipping ===", flush=True)
    with zipfile.ZipFile(out, "r") as z:
        for n in z.namelist():
            print(f"  {n}", flush=True)
        z.extractall(TARGET_DIR)
    print("Done.", flush=True)
