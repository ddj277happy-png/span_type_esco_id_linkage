# -*- coding: utf-8 -*-
"""
15_deepseek_label.py
用 DeepSeek API 给 review 状态 span 标 top-1/top-2/top-3 的对错
- 输入: span, type, top1_label, top2_label, top3_label (带 description)
- 输出: best_idx (1/2/3/none), confidence
- 跑通后输出 final_match_llm.csv
"""
import os, csv, time, json, sys
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
MATCH = os.path.join(ROOT, "final_match_v2.csv")
ESCO = os.path.join(ROOT, "esco_clean.csv")
OUT = os.path.join(ROOT, "llm_labels.csv")

API_KEY = os.environ.get("DEEPSEEK_API_KEY")  # 需在环境变量里设置,不要硬编码
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# 加载数据
m = pd.read_csv(MATCH, encoding="utf-8-sig")
esco = pd.read_csv(ESCO, encoding="utf-8-sig")
esco_idx = esco.set_index("uri")[["preferred_label", "description"]].to_dict(orient="index")

# 准备待标的数据
review = m[m["status"] == "review"].copy()
print(f"Review to label: {len(review)}", flush=True)

# 默认先标全部 20K,可通过命令行参数限制
N_LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else len(review)
review = review.head(N_LIMIT).copy()
print(f"Will label: {len(review)}", flush=True)

# 拆 top3 → 列出 label + description
def parse_top3(s):
    if not isinstance(s, str): return []
    out = []
    for p in s.split(" || "):
        try:
            uri, label, score = p.rsplit("|", 2)
            desc = esco_idx.get(uri, {}).get("description", "")[:150]
            out.append({"uri": uri, "label": label, "score": float(score), "description": desc})
        except Exception:
            continue
    return out

# Prompt 模板
PROMPT_TPL = """你是一个招聘技能标注专家(LKST 体系: L=语言、K=知识、S=技能、T=通用软技能)。

请判断: 给定一个中文 span 和 3 个 ESCO 英文候选,哪个最匹配?

【判定规则】
- 如果有任一候选的语义/外延与 span 实质相同,选它
- 多个候选近似等价时,选概念最宽的那个(覆盖 span)
- 如果所有候选都不对(没有真正匹配),返回 none
- L 类型: 语言名称 / 证书 / 语言能力(如"英语"→English, "TEM-4"→English 证书类)
- K 类型: 学科知识/法规/标准/工具体系(如"液压系统"→hydraulics)
- S 类型: 可执行的动作/方法(如"团队建设"→build team spirit)
- T 类型: 通用软技能(沟通/抗压/协作等)
- 警惕: ESCO 英文 L 桶只有欧洲+东亚语种,"外语/小语种/多语种"这种统称→返回 none

【输入】
span: {span}
type: {lkst}

候选:
1. {c1_label}  (cos={c1_score:.3f})
   描述: {c1_desc}
2. {c2_label}  (cos={c2_score:.3f})
   描述: {c2_desc}
3. {c3_label}  (cos={c3_score:.3f})
   描述: {c3_desc}

【输出格式】只返回 1 个 JSON:
{{"choice": 1 或 2 或 3 或 "none", "reason": "一句话理由"}}
"""

def call_llm(span, lkst, top3):
    if not top3:
        return {"choice": "none", "reason": "no candidates"}
    # 补全到 3 个
    while len(top3) < 3:
        top3.append({"uri":"","label":"(none)","score":0.0,"description":""})
    prompt = PROMPT_TPL.format(
        span=span, lkst=lkst,
        c1_label=top3[0]["label"], c1_score=top3[0]["score"], c1_desc=top3[0]["description"] or "(no desc)",
        c2_label=top3[1]["label"], c2_score=top3[1]["score"], c2_desc=top3[1]["description"] or "(no desc)",
        c3_label=top3[2]["label"], c3_score=top3[2]["score"], c3_desc=top3[2]["description"] or "(no desc)",
    )
    try:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role":"user","content":prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=30,
        )
        if r.status_code != 200:
            return {"choice": "err", "reason": f"HTTP {r.status_code}: {r.text[:100]}"}
        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()
        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content)
        return result
    except Exception as e:
        return {"choice": "err", "reason": f"{type(e).__name__}: {str(e)[:80]}"}

# 多线程并发
def process_one(idx, row):
    top3 = parse_top3(row["top3"])
    res = call_llm(row["span"], row["type"], top3)
    return idx, res

results = {}
print("=== Calling DeepSeek ===", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(process_one, i, r): i for i, (_, r) in enumerate(review.iterrows())}
    done = 0
    for fut in as_completed(futures):
        i, res = fut.result()
        results[i] = res
        done += 1
        if done % 50 == 0:
            print(f"  {done}/{len(review)}  ({time.time()-t0:.1f}s, {done/(time.time()-t0):.1f} req/s)", flush=True)

print(f"\n=== Done in {time.time()-t0:.1f}s ({len(results)} results) ===", flush=True)

# 合并到 review DataFrame
def map_choice(c):
    if c == 1: return 0  # top1 命中
    if c == 2: return 1  # top2 命中
    if c == 3: return 2  # top3 命中
    return -1  # none or err

review["llm_choice"] = [results.get(i, {}).get("choice", "err") for i in range(len(review))]
review["llm_reason"] = [results.get(i, {}).get("reason", "") for i in range(len(review))]
review["llm_top_idx"] = review["llm_choice"].apply(map_choice)

# 写
review_out = review[["span","type","score","status","top3","llm_choice","llm_top_idx","llm_reason"]]
review_out.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT}", flush=True)
print("\n=== LLM 判定分布 ===", flush=True)
print(review_out["llm_choice"].value_counts(), flush=True)

# 错误率
err_rate = (review_out["llm_choice"] == "err").mean()
print(f"\nError rate: {err_rate*100:.1f}%", flush=True)
