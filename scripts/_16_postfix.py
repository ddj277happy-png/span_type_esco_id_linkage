# -*- coding: utf-8 -*-
"""
16_postfix.py
issue 1+2+4 联合修复:
- issue 1: 缩写扩展字典 (SPC/PFMEA/DOE 等)
- issue 2: T 桶软技能同义词典
- issue 4: Tier 1 字符串 substring 兜底(用 dict 索引,O(N+M) 不是 O(N*M))

流程:
1. 对每个未 matched / no_match 的 span:
   a) 缩写扩展 → 用扩展后的英文去 ESCO 查
   b) T 桶同义 → 用英文同义去 ESCO T 查
   c) substring 兜底 → span 含 ESCO altLabel 或被含
2. 命中 → 给 URI, score=1.0
3. 输出 postfix_match.csv
"""
import os, csv, re
import pandas as pd

ROOT = r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage"
ESCO = os.path.join(ROOT, "esco_clean.csv")
MATCH = os.path.join(ROOT, "final_match_v2.csv")
OUT = os.path.join(ROOT, "postfix_match.csv")

# === 缩写扩展字典(Issue 1) ===
ABBREV = {
    # 制造/质量
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
    "5S": "5s methodology sort set in order shine standardize sustain",
    "8D": "eight disciplines problem solving",
    "6sigma": "six sigma",
    "六西格玛": "six sigma lean",
    "精益六西格玛": "lean six sigma",
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
    "VAVE": "value analysis value engineering",
    "PPH": "pieces per hour",
    "UPH": "units per hour",
    "JPH": "jobs per hour",
    "CT": "cycle time",
    "TAKT": "takt time",
    "SMED": "single minute exchange of die",
    "VSM": "value stream mapping",
    "KPI": "key performance indicator",
    "KPO": "key process output",
    "MTTR": "mean time to repair",
    "MTBF": "mean time between failures",
    "MTTF": "mean time to failure",
    "QCC": "quality control circle",
    "QCD": "quality cost delivery",
    "DPMO": "defects per million opportunities",
    "DPMU": "defects per million units",
    "RCA": "root cause analysis",
    "DMAIC": "define measure analyze improve control",
    "DMADV": "define measure analyze design verify",
    "FIFO": "first in first out",
    "LCA": "life cycle assessment",
    "LCC": "life cycle cost",
    "ABC": "activity based costing",
    "BSC": "balanced scorecard",
    "OKR": "objectives and key results",
    "KPI": "key performance indicator",
    "SOP": "standard operating procedure",
    "WI": "work instruction",
    "ECN": "engineering change notice",
    "ECR": "engineering change request",
    "BPR": "business process reengineering",
    "CRM": "customer relationship management",
    "SCM": "supply chain management",
    "SRM": "supplier relationship management",
    "BI": "business intelligence",
    "DSS": "decision support system",
    "CAD": "computer aided design",
    "CAM": "computer aided manufacturing",
    "CAE": "computer aided engineering",
    "FEA": "finite element analysis",
    "CFD": "computational fluid dynamics",
    "GIS": "geographic information system",
    "GPS": "global positioning system",
    "AGV": "automated guided vehicle",
    "AMR": "autonomous mobile robot",
    "IoT": "internet of things",
    "AI": "artificial intelligence",
    "ML": "machine learning",
    "DL": "deep learning",
    "RPA": "robotic process automation",
    "API": "application programming interface",
    "SDK": "software development kit",
    "IDE": "integrated development environment",
    "CI": "continuous integration",
    "CD": "continuous deployment",
    "DevOps": "devops",
    "Agile": "agile",
    "Scrum": "scrum",
    "Kanban": "kanban",
    "MVP": "minimum viable product",
    "BOM": "bill of materials",
    "PCB": "printed circuit board",
    "PCBA": "printed circuit board assembly",
    "SMT": "surface mount technology",
    "IC": "integrated circuit",
    "ASIC": "application specific integrated circuit",
    "FPGA": "field programmable gate array",
    "DSP": "digital signal processor",
    "MCU": "microcontroller unit",
    "EMI": "electromagnetic interference",
    "EMC": "electromagnetic compatibility",
    "ESD": "electrostatic discharge",
    "PPAP": "production part approval process",
    "APQP": "advanced product quality planning",
    "FTC": "failure tree analysis",
    "FTA": "fault tree analysis",
    # IT/数据
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
    "RAG": "retrieval augmented generation",
    "AWS": "amazon web services",
    "GCP": "google cloud platform",
    "Azure": "azure",
    "SaaS": "software as a service",
    "PaaS": "platform as a service",
    "IaaS": "infrastructure as a service",
    "VPN": "virtual private network",
    "DNS": "domain name system",
    "HTTP": "http",
    "HTTPS": "https",
    "REST": "rest",
    "API": "application programming interface",
    "OAuth": "oauth",
    "JWT": "json web token",
    "SQL": "sql",
    "ODBC": "open database connectivity",
    "JDBC": "java database connectivity",
    # 财务/管理
    "P&L": "profit and loss",
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
    "IT": "information technology",
    "PR": "public relations",
    "R&D": "research and development",
    "OD": "organizational development",
    # 商务/营销
    "B2B": "business to business",
    "B2C": "business to consumer",
    "C2C": "consumer to consumer",
    "SEO": "search engine optimization",
    "SEM": "search engine marketing",
    "CRM": "customer relationship management",
    "USP": "unique selling proposition",
    "SWOT": "strengths weaknesses opportunities threats",
    "PEST": "political economic social technological",
    "4P": "marketing mix product price place promotion",
    "4C": "marketing 4c consumer cost convenience communication",
    "CPC": "cost per click",
    "CPM": "cost per mille",
    "CTR": "click through rate",
    "GMV": "gross merchandise volume",
    "SKU": "stock keeping unit",
}

# === T 桶同义词典 (Issue 2) ===
T_SYNONYMS = {
    "沟通": "communication",
    "沟通能力": "communication",
    "沟通协调": "communication",
    "沟通技巧": "communication",
    "交流": "communication",
    "表达能力": "communication",
    "口头表达": "communication",
    "团队": "teamwork",
    "团队合作": "teamwork",
    "团队协作": "teamwork",
    "团队工作": "teamwork",
    "团队精神": "teamwork",
    "团队意识": "teamwork",
    "团队管理": "teamwork",
    "合作": "teamwork",
    "协作": "teamwork",
    "抗压": "stress tolerance",
    "抗压能力": "stress tolerance",
    "承压": "stress tolerance",
    "承压能力": "stress tolerance",
    "压力承受": "stress tolerance",
    "心理素质": "stress tolerance",
    "学习": "learning",
    "学习能力": "learning",
    "学习意愿": "learning",
    "学习态度": "learning",
    "主动学习": "learning",
    "持续学习": "learning",
    "责任心": "responsibility",
    "责任感": "responsibility",
    "责任感强": "responsibility",
    "担当": "responsibility",
    "诚信": "integrity",
    "诚实": "integrity",
    "信用": "integrity",
    "守信": "integrity",
    "主动性": "initiative",
    "积极主动": "initiative",
    "主动意识": "initiative",
    "工作主动": "initiative",
    "自驱": "initiative",
    "自驱力": "initiative",
    "创新": "innovation",
    "创新意识": "innovation",
    "创新能力": "innovation",
    "创造力": "innovation",
    "解决问题": "problem solving",
    "问题解决": "problem solving",
    "解决问题能力": "problem solving",
    "逻辑思维": "logical thinking",
    "逻辑思考": "logical thinking",
    "分析能力": "analytical thinking",
    "逻辑分析": "analytical thinking",
    "执行力": "execution",
    "执行": "execution",
    "执行能力": "execution",
    "细节": "attention to detail",
    "注重细节": "attention to detail",
    "细致": "attention to detail",
    "严谨": "attention to detail",
    "自我管理": "self management",
    "自我约束": "self management",
    "时间管理": "time management",
    "时间观念": "time management",
    "适应能力": "adaptability",
    "适应性": "adaptability",
    "应变": "adaptability",
    "应变能力": "adaptability",
    "抗挫折": "resilience",
    "韧性": "resilience",
    "抗逆力": "resilience",
    "客户意识": "customer orientation",
    "客户导向": "customer orientation",
    "服务意识": "customer orientation",
    "客户服务": "customer orientation",
    "保密": "confidentiality",
    "保密意识": "confidentiality",
    "安全意识": "safety awareness",
    "成本意识": "cost consciousness",
    "效率意识": "efficiency awareness",
    "结果导向": "results orientation",
    "目标导向": "results orientation",
    "系统性": "systematic thinking",
    "系统思维": "systematic thinking",
    "全局观": "holistic thinking",
    "大局观": "holistic thinking",
    "人际": "interpersonal skills",
    "人际关系": "interpersonal skills",
    "人际关系处理": "interpersonal skills",
    "协调能力": "coordination",
    "统筹": "coordination",
    "组织协调": "coordination",
    "领导力": "leadership",
    "领导能力": "leadership",
    "管理能力": "leadership",
    "管理经验": "management",
    "组织能力": "organisational skills",
}

def normalize_for_match(s):
    return re.sub(r"\s+", " ", s.lower().strip())

# 加载 ESCO
esco = pd.read_csv(ESCO, encoding="utf-8-sig")
# 构造: lkst → { norm_label: uri }
esco_idx = {}  # lkst -> {norm_label: (uri, label)}
for _, r in esco.iterrows():
    lkst = r["lkst"]
    lbl = str(r["preferred_label"] or "")
    alts = str(r.get("alt_labels","") or "").replace("\n","|").split("|")
    d = esco_idx.setdefault(lkst, {})
    for a in [lbl] + alts:
        a = normalize_for_match(a)
        if not a: continue
        if a not in d:
            d[a] = (r["uri"], lbl)
print(f"ESCO indexed: {sum(len(d) for d in esco_idx.values())} entries across 4 buckets", flush=True)

# 加载 v2 状态
m = pd.read_csv(MATCH, encoding="utf-8-sig")
# 只对 review 和 no_match 跑
todo = m[m["status"].isin(["review", "no_match"])].copy()
print(f"To post-process: {len(todo)}", flush=True)

# 对每个 span 试 issue 1+2+4
hits = {}  # key -> (uri, label, kind, score)
for _, r in todo.iterrows():
    s = str(r["span"])
    sn = normalize_for_match(s)
    lkst = r["type"]

    # 1) 缩写扩展
    expansion = ABBREV.get(s) or ABBREV.get(s.strip())
    if expansion:
        en = normalize_for_match(expansion)
        if lkst in esco_idx and en in esco_idx[lkst]:
            uri, lbl = esco_idx[lkst][en]
            hits[(s, lkst)] = (uri, lbl, "abbrev_expand", 0.95)
            continue
        # 跨 lkst 兜底
        for k_lkst, d in esco_idx.items():
            if en in d:
                uri, lbl = d[en]
                hits[(s, lkst)] = (uri, lbl, f"abbrev_expand_cross_{k_lkst}", 0.7)
                break
        else:
            # 缩写扩展后,substring 匹配英文展开
            for k_lkst, d in esco_idx.items():
                for tok, (uri, lbl) in d.items():
                    if len(tok) < 4: continue
                    if tok in en or en in tok:
                        hits[(s, lkst)] = (uri, lbl, f"abbrev_substr_{k_lkst}", 0.65)
                        break
                if (s, lkst) in hits: break

    if (s, lkst) in hits: continue

    # 2) T 桶同义
    if lkst == "T":
        syn = T_SYNONYMS.get(s) or T_SYNONYMS.get(s.strip())
        if syn:
            en = normalize_for_match(syn)
            if lkst in esco_idx and en in esco_idx[lkst]:
                uri, lbl = esco_idx[lkst][en]
                hits[(s, lkst)] = (uri, lbl, "t_synonym", 0.85)
                continue

    if (s, lkst) in hits: continue

    # 4) Tier 1 substring 兜底(同 lkst)
    if lkst in esco_idx:
        d = esco_idx[lkst]
        # 中文 span 包含 ESCO 英文 token (要小写比)
        for tok, (uri, lbl) in d.items():
            if len(tok) < 4: continue
            if tok in sn:
                hits[(s, lkst)] = (uri, lbl, "tier1_contain", 0.8)
                break
        if (s, lkst) not in hits:
            # 反过来: ESCO token 包含 span
            for tok, (uri, lbl) in d.items():
                if len(sn) < 3: continue
                if sn in tok:
                    hits[(s, lkst)] = (uri, lbl, "tier1_contained", 0.7)
                    break

print(f"\nHits by tier:", flush=True)
from collections import Counter
kinds = Counter(v[2] for v in hits.values())
for k, c in kinds.most_common():
    print(f"  {k}: {c}", flush=True)

# 写
rows = []
for (s, t), (uri, lbl, kind, sc) in hits.items():
    rows.append({"span": s, "type": t, "esco_uri": uri, "esco_label_en": lbl,
                 "score": sc, "match_kind": kind})
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved: {OUT} ({len(df)} rows)", flush=True)
