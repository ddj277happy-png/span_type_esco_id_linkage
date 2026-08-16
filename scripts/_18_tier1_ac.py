# -*- coding: utf-8 -*-
"""
18_tier1_ac.py
Tier 1 字符串 substring 兜底,用 Aho-Corasick 多模式匹配
- 把 ESCO altLabel 全部塞进 AC automaton
- 扫每个 span,返回命中的所有 (token, uri, label, lkst)
- 对每个 span 取最长的命中(避免 "use" 这种短词污染)
"""
import os, csv, re
import pandas as pd
import ahocorasick

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
ESCO = os.path.join(ROOT, "esco_clean.csv")
MATCH = os.path.join(ROOT, "final_match_v3.csv")  # 已经合并 postfix
OUT = os.path.join(ROOT, "tier1_ac_match.csv")

# 加载 ESCO,只挑短 token (3-15 char),避免长描述污染
esco = pd.read_csv(ESCO, encoding="utf-8-sig")
print(f"ESCO rows: {len(esco)}", flush=True)

# 构造 Aho-Corasick automaton
A = ahocorasick.Automaton()
# 跳过纯符号 / 数字 / 太短 / 太通用
SKIP = {
    "a", "an", "and", "or", "in", "on", "at", "to", "of", "for", "by", "the", "is", "be",
    # 通用名词(易 substring 误命中)
    "plan", "plans", "planning", "process", "processes", "processes",
    "engineering", "engineer", "engineers", "system", "systems", "design", "designs",
    "management", "manage", "manages", "operation", "operations", "operating",
    "production", "product", "products", "service", "services", "project", "projects",
    "quality", "test", "testing", "report", "reports", "reporting", "data",
    "software", "application", "applications", "method", "methods", "methodology",
    "standard", "standards", "regulation", "regulations", "requirement", "requirements",
    "development", "develop", "analysis", "analyse", "analyse", "analyzing", "analyse",
    "technic", "technics", "technical", "technique", "techniques", "technology",
    "control", "controls", "monitoring", "monitor", "safety", "security",
    "training", "train", "trainer", "trainers", "communication", "communicate",
    "team", "teams", "teamwork", "leadership", "leading",
    "use", "uses", "using", "used", "apply", "applies", "applying", "applied",
    "perform", "performs", "performing", "performed", "work", "works", "working", "worked",
    "knowledge", "know", "knows", "knowing", "knew", "skill", "skills", "competence",
    "language", "languages", "professional", "professionals",
    "industry", "industries", "industrial", "sector", "sectors",
    "company", "companies", "business", "businesses", "enterprise", "enterprises",
    "human", "people", "person", "persons", "personnel", "staff", "employee", "employees",
    "computer", "computers", "digital", "electronic", "electrical",
    "building", "buildings", "construction", "construct",
    "machinery", "machine", "machines", "equipment",
    "customer", "customers", "client", "clients", "supplier", "suppliers",
    "sales", "sale", "sell", "selling", "sells",
    "research", "researching", "study", "studies", "studying",
    "good", "great", "best", "better", "high", "low", "new", "old",
    "implement", "implementation", "implements", "implementing",
    "identify", "identifies", "identifying", "identified", "identification",
    "ensure", "ensures", "ensuring", "ensured",
    "understand", "understands", "understanding", "understood",
    "create", "creates", "creating", "created", "creation",
    "develop", "develops", "developing", "developed",
    "improve", "improves", "improving", "improved", "improvement",
    "maintain", "maintains", "maintaining", "maintained", "maintenance",
    "support", "supports", "supporting", "supported",
    "cooperate", "cooperates", "cooperating", "cooperation",
    "coordinate", "coordinates", "coordinating", "coordination",
    "collaborate", "collaboration",
    "handle", "handles", "handling", "managed", "managing",
    "provide", "provides", "providing", "provided",
    "establish", "establishes", "establishing", "established",
    "international", "global", "national", "regional", "local",
    "english", "chinese", "japanese", "french", "german", "spanish", "portuguese", "russian", "italian", "korean", "arabic",
    "vietnamese", "thai", "indonesian", "malay", "hindi", "turkish", "dutch", "polish", "greek",
}

added = 0
for _, r in esco.iterrows():
    lbl = str(r["preferred_label"] or "")
    alts = str(r.get("alt_labels","") or "").replace("\n","|").split("|")
    lkst = r["lkst"]
    uri = r["uri"]
    seen_in_this_row = set()
    for a in [lbl] + alts:
        a = re.sub(r"\s+", " ", a.strip().lower())
        if not a or len(a) < 4 or len(a) > 15: continue
        if a in SKIP: continue
        if not re.search(r"[a-z]", a): continue  # 跳过纯数字/符号
        if a in seen_in_this_row: continue
        seen_in_this_row.add(a)
        # 用 (uri, label, lkst) 作为 value
        try:
            A.add_word(a, (uri, lbl, lkst, a))
            added += 1
        except ValueError:
            pass  # duplicate

A.make_automaton()
print(f"AC automaton: {added} patterns (after dedup)", flush=True)

# 加载 v3 状态
m = pd.read_csv(MATCH, encoding="utf-8-sig")
todo = m[m["status"].isin(["review", "no_match"])].copy()
print(f"To scan: {len(todo)}", flush=True)

# 扫
hits = {}  # (span, type) -> (uri, label, lkst, token, score)
for _, r in todo.iterrows():
    s = str(r["span"])
    lkst = r["type"]
    s_low = s.lower()
    found = []  # list of (end, token, uri, label, t_lkst)
    for end_idx, (uri, lbl, t_lkst, tok) in A.iter(s_low):
        found.append((end_idx, tok, uri, lbl, t_lkst))
    if not found: continue
    # 取最长的 token(避免短词覆盖)
    found.sort(key=lambda x: -len(x[1]))
    end_idx, tok, uri, lbl, t_lkst = found[0]
    # 优先同 lkst
    same_lkst = [f for f in found if f[4] == lkst]
    if same_lkst:
        end_idx, tok, uri, lbl, t_lkst = same_lkst[0]
    # word-boundary 检查: match 前后是字母/数字 → 嵌入词内,丢弃
    start_idx = end_idx - len(tok) + 1
    if start_idx > 0 and s_low[start_idx-1].isalnum():
        continue  # 前是字母数字,说明 tok 是更长英文词的子串
    if end_idx+1 < len(s_low) and s_low[end_idx+1].isalnum():
        continue  # 后是字母数字,同上
    # 加分阈值: 至少 5 字符 + 同 lkst 才有底,否则不收
    if len(tok) < 5 and t_lkst != lkst:
        continue
    hits[(s, lkst)] = (uri, lbl, t_lkst, tok, 0.75 if t_lkst == lkst else 0.55)

print(f"\nTier 1 hits: {len(hits)}", flush=True)
# 统计 lkst
from collections import Counter
lkst_dist = Counter(v[2] for v in hits.values())
print(f"By target lkst: {lkst_dist}", flush=True)

# 写
rows = []
for (s, t), (uri, lbl, t_lkst, tok, sc) in hits.items():
    rows.append({"span": s, "type": t, "esco_uri": uri, "esco_label_en": lbl,
                 "target_lkst": t_lkst, "matched_token": tok, "score": sc, "match_kind": "tier1_ac"})
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT} ({len(df)} rows)", flush=True)
