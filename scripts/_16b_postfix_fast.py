# -*- coding: utf-8 -*-
"""
16b_postfix_fast.py
issue 1+2 only (no Tier 1 substring 慢循环)
+ Tier 1 用长度+频次过滤,只查高价值 token
"""
import os, csv, re
import pandas as pd
from collections import Counter

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
ESCO = os.path.join(ROOT, "esco_clean.csv")
MATCH = os.path.join(ROOT, "final_match_v2.csv")
OUT = os.path.join(ROOT, "postfix_match.csv")

# === 缩写字典(简化版,只保留最常见的) ===
ABBREV = {
    "SPC": "statistical process control",
    "PFMEA": "process failure mode and effects analysis",
    "DFMEA": "design failure mode and effects analysis",
    "FMEA": "failure mode and effects analysis",
    "DOE": "design of experiments",
    "TQM": "total quality management",
    "TPM": "total productive maintenance",
    "CNC": "computer numerical control",
    "CAPP": "computer aided process planning",
    "OEE": "overall equipment effectiveness",
    "PDCA": "plan do check act",
    "5S": "5s sort set in order shine standardize",
    "8D": "eight disciplines problem solving",
    "6sigma": "six sigma",
    "六西格玛": "six sigma",
    "精益六西格玛": "lean six sigma",
    "精益": "lean",
    "IE": "industrial engineering",
    "QC": "quality control",
    "QA": "quality assurance",
    "IQC": "incoming quality control",
    "OQC": "outgoing quality control",
    "IPQC": "in-process quality control",
    "AQL": "acceptable quality level",
    "BOM": "bill of materials",
    "ERP": "enterprise resource planning",
    "MES": "manufacturing execution system",
    "WMS": "warehouse management system",
    "SCADA": "supervisory control and data acquisition",
    "PLC": "programmable logic controller",
    "HMI": "human machine interface",
    "DCS": "distributed control system",
    "DNC": "distributed numerical control",
    "SMED": "single minute exchange of die",
    "VSM": "value stream mapping",
    "KPI": "key performance indicator",
    "MTTR": "mean time to repair",
    "MTBF": "mean time between failures",
    "QCC": "quality control circle",
    "RCA": "root cause analysis",
    "DMAIC": "define measure analyze improve control",
    "SOP": "standard operating procedure",
    "PPAP": "production part approval process",
    "APQP": "advanced product quality planning",
    "FMEA": "failure mode and effects analysis",
    "FTA": "fault tree analysis",
    "ECN": "engineering change notice",
    "BPR": "business process reengineering",
    "PCB": "printed circuit board",
    "PCBA": "printed circuit board assembly",
    "SMT": "surface mount technology",
    "IC": "integrated circuit",
    "ASIC": "application specific integrated circuit",
    "FPGA": "field programmable gate array",
    "EMI": "electromagnetic interference",
    "EMC": "electromagnetic compatibility",
    "ESD": "electrostatic discharge",
    "AGV": "automated guided vehicle",
    "AMR": "autonomous mobile robot",
    "IoT": "internet of things",
    "AI": "artificial intelligence",
    "ML": "machine learning",
    "DL": "deep learning",
    "RPA": "robotic process automation",
    "API": "application programming interface",
    "SDK": "software development kit",
    "DevOps": "devops",
    "Agile": "agile",
    "Scrum": "scrum",
    "Kanban": "kanban",
    "MVP": "minimum viable product",
    "SQL": "structured query language",
    "NoSQL": "nosql",
    "HTML": "html",
    "CSS": "css",
    "JS": "javascript",
    "TS": "typescript",
    "PHP": "php",
    "Java": "java",
    "Python": "python",
    "C++": "c plus plus",
    "C#": "c sharp",
    "Go": "go",
    "Rust": "rust",
    "Kotlin": "kotlin",
    "Swift": "swift",
    "React": "react",
    "Vue": "vue",
    "Angular": "angular",
    "Node": "node.js",
    "Django": "django",
    "Flask": "flask",
    "Spring": "spring",
    "MySQL": "mysql",
    "PostgreSQL": "postgresql",
    "MongoDB": "mongodb",
    "Redis": "redis",
    "Kafka": "kafka",
    "Hadoop": "hadoop",
    "Spark": "spark",
    "TensorFlow": "tensorflow",
    "PyTorch": "pytorch",
    "NLP": "natural language processing",
    "CV": "computer vision",
    "LLM": "large language model",
    "AWS": "amazon web services",
    "GCP": "google cloud platform",
    "ROI": "return on investment",
    "ROE": "return on equity",
    "ROA": "return on assets",
    "EBITDA": "earnings before interest taxes depreciation amortization",
    "CFO": "chief financial officer",
    "CEO": "chief executive officer",
    "COO": "chief operating officer",
    "CTO": "chief technology officer",
    "CMO": "chief marketing officer",
    "HR": "human resources",
    "PR": "public relations",
    "R&D": "research and development",
    "B2B": "business to business",
    "B2C": "business to consumer",
    "SEO": "search engine optimization",
    "SEM": "search engine marketing",
    "CRM": "customer relationship management",
    "GMV": "gross merchandise volume",
    "SKU": "stock keeping unit",
    "FTC": "failure mode and effects analysis",
}

T_SYNONYMS = {
    "沟通": "communication", "沟通能力": "communication", "沟通协调": "communication",
    "沟通技巧": "communication", "交流": "communication", "表达能力": "communication",
    "口头表达": "communication", "人际沟通": "communication",
    "团队": "teamwork", "团队合作": "teamwork", "团队协作": "teamwork",
    "团队工作": "teamwork", "团队精神": "teamwork", "团队意识": "teamwork",
    "合作": "teamwork", "协作": "teamwork", "teamwork": "teamwork",
    "抗压": "stress tolerance", "抗压能力": "stress tolerance", "承压": "stress tolerance",
    "承压能力": "stress tolerance", "压力承受": "stress tolerance", "心理素质": "stress tolerance",
    "学习": "learning", "学习能力": "learning", "学习意愿": "learning",
    "学习态度": "learning", "主动学习": "learning", "持续学习": "learning", "自学": "learning",
    "责任心": "responsibility", "责任感": "responsibility", "责任感强": "responsibility",
    "担当": "responsibility", "有担当": "responsibility",
    "诚信": "integrity", "诚实": "integrity", "信用": "integrity", "守信": "integrity",
    "主动性": "initiative", "积极主动": "initiative", "主动意识": "initiative",
    "工作主动": "initiative", "自驱": "initiative", "自驱力": "initiative",
    "创新": "innovation", "创新意识": "innovation", "创新能力": "innovation", "创造力": "innovation",
    "解决问题": "problem solving", "问题解决": "problem solving", "解决问题能力": "problem solving",
    "逻辑思维": "logical thinking", "逻辑思考": "logical thinking",
    "分析能力": "analytical thinking", "逻辑分析": "analytical thinking", "分析问题": "analytical thinking",
    "执行力": "execution", "执行": "execution", "执行能力": "execution",
    "细节": "attention to detail", "注重细节": "attention to detail", "细致": "attention to detail", "严谨": "attention to detail",
    "自我管理": "self management", "自我约束": "self management",
    "时间管理": "time management", "时间观念": "time management",
    "适应能力": "adaptability", "适应性": "adaptability", "应变": "adaptability", "应变能力": "adaptability",
    "抗挫折": "resilience", "韧性": "resilience", "抗逆力": "resilience",
    "客户意识": "customer orientation", "客户导向": "customer orientation",
    "服务意识": "customer orientation", "客户服务": "customer orientation",
    "保密": "confidentiality", "保密意识": "confidentiality",
    "安全意识": "safety awareness",
    "成本意识": "cost consciousness",
    "效率意识": "efficiency awareness",
    "结果导向": "results orientation", "目标导向": "results orientation",
    "系统性": "systematic thinking", "系统思维": "systematic thinking",
    "全局观": "holistic thinking", "大局观": "holistic thinking",
    "人际": "interpersonal skills", "人际关系": "interpersonal skills", "人际关系处理": "interpersonal skills",
    "协调能力": "coordination", "统筹": "coordination", "组织协调": "coordination",
    "领导力": "leadership", "领导能力": "leadership", "管理能力": "leadership",
    "管理经验": "management",
    "组织能力": "organisational skills",
}

def normalize(s):
    return re.sub(r"\s+", " ", s.lower().strip())

# 加载 ESCO,按 lkst 分桶索引
esco = pd.read_csv(ESCO, encoding="utf-8-sig")
esco_idx = {}
for _, r in esco.iterrows():
    lkst = r["lkst"]
    lbl = str(r["preferred_label"] or "")
    alts = str(r.get("alt_labels","") or "").replace("\n","|").split("|")
    d = esco_idx.setdefault(lkst, {})
    for a in [lbl] + alts:
        a = normalize(a)
        if a and a not in d:
            d[a] = (r["uri"], lbl)
print(f"ESCO indexed: {sum(len(d) for d in esco_idx.values())}", flush=True)

# 加载 v2 状态
m = pd.read_csv(MATCH, encoding="utf-8-sig")
todo = m[m["status"].isin(["review", "no_match"])].copy()
print(f"To post-process: {len(todo)}", flush=True)

# 跑 issue 1+2
hits = {}
abbrev_hits, t_syn_hits = 0, 0
for _, r in todo.iterrows():
    s = str(r["span"])
    lkst = r["type"]

    # 1) 缩写
    expansion = ABBREV.get(s) or ABBREV.get(s.strip())
    if expansion:
        en = normalize(expansion)
        # 同 lkst
        for k_lkst in [lkst, "S", "K", "T", "L"]:  # 优先同 lkst
            d = esco_idx.get(k_lkst, {})
            if en in d:
                uri, lbl = d[en]
                hits[(s, lkst)] = (uri, lbl, f"abbrev_{k_lkst}", 0.95)
                abbrev_hits += 1
                break
        if (s, lkst) in hits: continue

    # 2) T 同义
    if lkst == "T":
        syn = T_SYNONYMS.get(s) or T_SYNONYMS.get(s.strip())
        if syn:
            en = normalize(syn)
            d = esco_idx.get("T", {})
            if en in d:
                uri, lbl = d[en]
                hits[(s, lkst)] = (uri, lbl, "t_synonym", 0.9)
                t_syn_hits += 1

print(f"\nAbbrev hits: {abbrev_hits}", flush=True)
print(f"T syn hits: {t_syn_hits}", flush=True)
print(f"Total hits: {len(hits)}", flush=True)

# 写
rows = []
for (s, t), (uri, lbl, kind, sc) in hits.items():
    rows.append({"span": s, "type": t, "esco_uri": uri, "esco_label_en": lbl,
                 "score": sc, "match_kind": kind})
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT} ({len(df)} rows)", flush=True)
print(df["match_kind"].value_counts().head(10), flush=True)
