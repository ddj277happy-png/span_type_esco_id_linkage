# -*- coding: utf-8 -*-
"""
21_rerun_review.py
只重跑 v5 里 review 状态的 4,741 条(原来是 DeepSeek 余额耗尽失败的)
- 输入: final_match_v5.csv (status=review) + 已有 llm_labels.csv
- 输出: 新的 llm_labels_v2.csv,只含 4,741 review 的新结果
"""
import os, time, json, sys
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
V5 = os.path.join(ROOT, "final_match_v5.csv")
OLD = os.path.join(ROOT, "llm_labels.csv")
ESCO = os.path.join(ROOT, "esco_clean.csv")
OUT = os.path.join(ROOT, "llm_labels_v2.csv")

API_KEY = os.environ.get("DEEPSEEK_API_KEY")  # 需在环境变量里设置,不要硬编码
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

m = pd.read_csv(V5, encoding="utf-8-sig")
old = pd.read_csv(OLD, encoding="utf-8-sig")

# 取 review
todo = m[m["status"] == "review"].copy()
print(f"v5 review to rerun: {len(todo)}", flush=True)

# 也跳过旧 labels 里已经成功的(避免重复)
old_idx = old.set_index(["span", "type"])["llm_choice"]
to_skip = set()
for idx, r in todo.iterrows():
    key = (r["span"], r["type"])
    if key in old_idx.index:
        ch = old_idx.loc[key]
        if isinstance(ch, pd.Series): ch = ch.iloc[0]
        if ch != "err":
            to_skip.add(key)
print(f"Already labeled (skip): {len(to_skip)}", flush=True)

todo = todo[~todo.apply(lambda r: (r["span"], r["type"]) in to_skip, axis=1)].copy()
print(f"Actually rerun: {len(todo)}", flush=True)

# 加载 ESCO 描述
esco = pd.read_csv(ESCO, encoding="utf-8-sig")
esco_idx = esco.set_index("uri")[["preferred_label", "description"]].to_dict(orient="index")

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

PROMPT_TPL = """你是一个招聘技能标注专家(LKST 体系: L=语言、K=知识、S=技能、T=通用软技能)。

请判断: 给定一个中文 span 和 3 个 ESCO 英文候选,哪个最匹配?

【判定规则】
- 如果有任一候选的语义/外延与 span 实质相同,选它
- 多个候选近似等价时,选概念最宽的那个(覆盖 span)
- 如果所有候选都不对(没有真正匹配),返回 none
- L 类型: 语言名称 / 证书 / 语言能力
- K 类型: 学科知识/法规/标准/工具体系
- S 类型: 可执行的动作/方法
- T 类型: 通用软技能
- 警惕: ESCO 英文 L 桶只有欧洲+东亚语种,"外语/小语种/多语种"统称→none

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
    if not top3: return {"choice": "none", "reason": "no candidates"}
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
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content)
    except Exception as e:
        return {"choice": "err", "reason": f"{type(e).__name__}: {str(e)[:80]}"}

def process_one(idx, row):
    top3 = parse_top3(row["top3"])
    res = call_llm(row["span"], row["type"], top3)
    return idx, res

results = {}
print("=== Calling DeepSeek ===", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(process_one, i, r): i for i, (_, r) in enumerate(todo.iterrows())}
    done = 0
    for fut in as_completed(futures):
        i, res = fut.result()
        results[i] = res
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(todo)}  ({time.time()-t0:.1f}s, {done/(time.time()-t0):.1f} req/s)", flush=True)

print(f"\n=== Done in {time.time()-t0:.1f}s ({len(results)} results) ===", flush=True)

# 合并到 v5
def map_choice(c):
    if c == 1: return 0
    if c == 2: return 1
    if c == 3: return 2
    return -1

# 写到 llm_labels_v2.csv
out_rows = []
for i, (_, r) in enumerate(todo.iterrows()):
    res = results.get(i, {"choice": "err", "reason": "no result"})
    out_rows.append({
        "span": r["span"], "type": r["type"],
        "score": r["score"], "status": r["status"],
        "top3": r["top3"],
        "llm_choice": res.get("choice", "err"),
        "llm_top_idx": map_choice(res.get("choice", "err")),
        "llm_reason": res.get("reason", ""),
    })
new_df = pd.DataFrame(out_rows)
new_df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"Saved: {OUT} ({len(new_df)} rows)", flush=True)
print("\n=== LLM 判定分布 ===", flush=True)
print(new_df["llm_choice"].value_counts(), flush=True)
err_n = (new_df["llm_choice"] == "err").sum()
print(f"\nError rate: {err_n/len(new_df)*100:.1f}%", flush=True)
