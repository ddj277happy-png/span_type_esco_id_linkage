# 出海岗位 span → ESCO URI 匹配算法

> 项目技术文档 · 2026-08-16

## 1. 项目背景与目标

### 1.1 问题

5,140 条出海岗位数据已用 LLM 做了 LKST 4 维技能标注,产出 **90,625 个 (span, L/K/S/T) 标注**。但这些 span 还是**自由文本**,没法直接对接下游标准化系统。

### 1.2 目标

把每个 (span, type) 链接到 **ESCO v1.2.0 标准 URI**,使输出**可计算、可对接、可复用**。

### 1.3 背景

- 数据量 5,140 条相对较小,纯监督学习(微调 BERT)在这种规模上精度受限
- 替代方案:用 LLM 直接抽 span + 算法把 span 链到 ESCO 标准库
- 本仓库实现的是"链到 ESCO"这一环节

## 2. 数据规模

| 阶段 | 数量 | 说明 |
|---|---|---|
| 原始 job | 5,140 | 招聘数据条目 |
| 标注长表(span 出现) | 90,625 | 同一 span 跨 job 重复算 |
| unique (span, type) | **31,866** | 去重后待匹配 |
| ESCO v1.2.0 概念 | 13,939 | L=359, K=3,145, S=10,338, T=97 |

**输入数据约定**:算法的输入是 LKST 4 维标注后的 CSV(11 列),文件名不限,放到 `data/` 下自动识别(自动跳过已知非输入文件 + 校验 L/K/S/T 列;也支持 `SKILL_CSV` 环境变量显式指定)。格式详见 [`data/input_format.md`](data/input_format.md),参考示例见 `data/input_sample.csv`。本仓库已包含示例输入 `data/step3_skill_annotation_20260810_012339.csv`(5,140 条,90,625 个标注),clone 后可直接跑。

### 2.5 ESCO 源文件结构与 LKST 映射

ESCO v1.2.0 解压后 `esco/` 目录里有 13 个文件,但 **K/S/T 不是按文件分,是按字段过滤**——所有 13,939 个概念都集中在 `skills_en.csv` 一个主表,其他 `*Collection_en.csv` 是按主题切分的子集,跟 LKST 分类无关。

> ⚠️ **关键容易踩坑**:`skills_en.csv` 里的 `skillType` 字段**只有 `knowledge` 和 `skill/competence` 两个值,没有 T**!T 来自另一个字段 `reuseLevel == 'transversal'`。这两个字段是两套**正交维度**:
>
> | 字段 | 取值 | 控制 |
> |---|---|---|
> | `skillType` | `knowledge` / `skill/competence` | K vs S |
> | `reuseLevel` | `transversal` / `cross-sector` / `sector-specific` / `occupation-specific` | T vs 其他 |
>
> 同一条 skill 既要有 skillType,也要有 reuseLevel,可以叠加。比如 "show initiative" 同时是 `skill/competence` + `transversal`(既算 S 也算 T)。452 条 `reuseLevel=transversal` 的 skill 里,381 条是 `skill/competence`、71 条是 `knowledge`。

**LKST 过滤规则**(实现见 `pipeline/01_数据准备/_01_prep_esco.py:36-43`,优先级从高到低):

| LKST | 过滤条件 | 涉及字段 |
|---|---|---|
| **L** | URI ∈ `languageSkillsCollection_en.csv` | 集合(优先匹配) |
| **K** | `skillType == 'knowledge'` 且不在 L 集合 | `skillType` |
| **T** | URI ∈ `transversalSkillsCollection_en.csv` **或** `reuseLevel == 'transversal'` | 集合 + `reuseLevel`(**不是 skillType**) |
| **S** | 其余 `skillType == 'skill/competence'` | `skillType` |

S 与 T 会重叠(一个 S 如果 `reuseLevel=transversal`,它既算 S 也算 T;L 也会覆盖一部分 K/S/T——language 集合优先)。这是 LKST 4 维标签体系,不是 4 个互斥的分类。

**决策过程(三刀切出 4 个标签)**:

```
                          (一条 ESCO skill)
                                │
                  ┌─────────────┴─────────────┐
                  │                           │
            在 lang 集合?                  (不在)
                  │                           │
                  ▼                           ▼
                  L              ┌────────────┴────────────┐
                                 │                         │
                          knowledge?                  (非 knowledge)
                                 │                         │
                                 ▼                         ▼
                                 K              ┌──────────┴──────────┐
                                                │                     │
                                         transversal?          (非 transversal)
                                                │                     │
                                                ▼                     ▼
                                                T                     S
```

| 步骤 | 排除的类 | 判断 |
|---|---|---|
| 1 | L vs {S, K, T} | `uri in languageSkillsCollection_en.csv` |
| 2 | K vs {S, T} | `skillType == 'knowledge'` |
| 3 | T vs S | `uri in transversalSkillsCollection_en.csv` **或** `reuseLevel == 'transversal'` |
| 4 | 兜底 | 剩下的全是 S |

L 优先,S 兜底,K 和 T 在中间按维度拆。**不是 4 个互斥分类,是 3 刀切出来的 4 个标签**。

**`esco/` 目录里其他 12 个文件做什么用**:

| 文件 | 行数 | 职责 | 跟 LKST 有关吗 |
|---|---|---|---|
| `skills_en.csv` | 13,939 | **主表**,所有 skill 概念全在这 | ✅ K/S/T 全部来源 |
| `languageSkillsCollection_en.csv` | 359 | 语言技能官方子集 | ✅ 决定 L |
| `transversalSkillsCollection_en.csv` | 95 | 横向技能官方子集(仅 T 的部分,非全部) | ⚠️ T 的一部分 |
| `digitalSkillsCollection_en.csv` | 1,284 | 数字技能主题子集 | ❌ 按主题切 |
| `greenSkillsCollection_en.csv` | 591 | 绿色技能主题子集 | ❌ |
| `digCompSkillsCollection_en.csv` | 25 | DigComp 数字素养框架子集 | ❌ |
| `researchSkillsCollection_en.csv` | 40 | 研究技能主题子集 | ❌ |
| `researchOccupationsCollection_en.csv` | 122 | 职业(不是 skill)子集 | ❌ |
| `conceptSchemes_en.csv` | 19 | scheme 元数据(含「ESCO Skill Pillar concept (sub-) Types」「reusability levels」) | ⚠️ scheme 定义参考 |
| `skillGroups_en.csv` | — | skill 分组 | ❌ |
| `skillsHierarchy_en.csv` | — | skill 父子层级 | ❌ |
| `skillSkillRelations_en.csv` | — | skill 兄弟/关联 | ❌ |
| `broaderRelationsSkillPillar_en.csv` | — | skill pillar 内的 broader 关系 | ❌ |
| `broaderRelationsOccPillar_en.csv` | — | occupation pillar 内的 broader 关系 | ❌ |
| `occupationSkillRelations_en.csv` | 22M | occupation↔skill 关联表(超大) | ❌ |
| `occupations_en.csv` | 3,008 | 职业主表 | ❌ |
| `ISCOGroups_en.csv` | — | ISCO 2008 职业分组 | ❌ |
| `ESCO_v1.2.0_en_csv.zip` | — | 原始压缩包(脚本解压来源) | ❌ |

**一句话**:`skills_en.csv` 一张表 + 字段过滤 = K/S/T。其他 *Collection 文件按主题切,别被文件名唬住当成 K/S/T 分类。

## 3. 算法设计 — 3 层 Tier 兜底

```
Tier 1: 字典/Trie 快速查表       → 命中率 ~3%
Tier 2: 多语种 embedding 余弦相似度 → 命中率 ~16%  
Tier 3: DeepSeek LLM 仲裁          → 命中率 ~19%
─────────────────────────────────────────────────
合计 38.4% 命中真实 ESCO URI
其余 61.7% 兜底为 custom: 前缀的稳定 ID
```

### 3.1 Tier 1: 字典 + AC 自动机

**目标**:捕获 embedding 搞不定的特殊情况(缩写、专有名词)

**实现**:
- **缩写字典**(130+ 条):SPC/PFMEA/DOE/CNC/SMT/PMP/6sigma 等,扩展后查 ESCO altLabel
- **T 桶同义词**(80+ 条):沟通/团队合作/抗压 等 → 英文同义 (communication/teamwork 等)
- **Aho-Corasick 自动机**:8,518 个 ESCO 短词(3-15 字符)进 AC automaton,扫 26K spans 找 substring
- **word boundary 检查**:match 前后是字母/数字 → 嵌入词内,丢弃
- **停用词表**:engineering/plan/process/standard 等通用词排除

### 3.2 Tier 2: Multilingual Embedding

**模型**:`paraphrase-multilingual-MiniLM-L12-v2`(118M params, 384 dim)
- 备选 bge-m3 跨语种更好,但下不完(2.09GB incomplete)
- paraphrase-multilingual 跨语种 OK,缩写稍差
- CPU 推理 45-160 t/s,15 分钟全跑完

**流程**:
1. 每个 ESCO 条目 → embedding(用 `preferredLabel + altLabels` 拼接)
2. 每个 unique span → embedding
3. 按 LKST type 分桶(bucket 内匹配)
4. cos 相似度 top-1
5. 阈值:
   - L/K/S 桶:cos ≥ 0.70 → matched
   - T 桶:cos ≥ 0.55 → matched(T 桶通用词多,阈值放宽)

### 3.3 Tier 3: DeepSeek LLM 仲裁

**目标**:对 Tier 2 把握不准的(cos 0.5-0.7),让 LLM 当 judge

**Prompt 设计**:
- 输入:span + type + top-3 ESCO 候选(含 description)
- LLM 选 1/2/3/none
- 4 类判定规则(L/K/S/T 不同处理)

**两层执行**:
- 第一轮:20,737 条 review,15,997 成功(4,746 余额耗尽失败)
- 第二轮:4,741 条失败重跑,DeepSeek 重充值后只 3 错
- 累计:LLM 仲裁 20,737 条,**4,752 改对 top-1 错位,11,225 判 none**

## 4. 兜底:Custom ID 机制

**问题**:Tier 1-3 都失败时,总得给个 ID,不能为空

**方案**:`custom:{type}/{hash}` 命名空间

| 字段 | 值 |
|---|---|
| URI | `custom:skill/{hash}` 等 |
| Hash | SHA1(span+type).hexdigest()[:12] |
| 用途 | 占位符,明示"非 ESCO 标准" |

- 19,674 个 no_match span 全部获得稳定 ID
- **覆盖率 100%**(每条 span 都有 URI)

## 5. 精度验证

### 5.1 方法

抽 200 条 stratified gold(L/K/S/T × {matched, no_match} = 8 桶 × 25 条),用 DeepSeek 当独立 judge 问"我们给的 URI 对不对"。

### 5.2 结果

| our_status | DeepSeek YES | DeepSeek NO | total | 通过率 |
|---|---|---|---|---|
| matched | 69 | 31 | 100 | **69.0%** |
| no_match | 0 | 100 | 100 | 0% (custom ID 非真 ESCO) |
| **总** | 69 | 131 | 200 | 34.5% |

按 type × status 分桶:

| type | status | YES | total | % |
|---|---|---|---|---|
| L | matched | 23 | 25 | **92.0%** |
| K | matched | 14 | 25 | 56.0% |
| S | matched | 18 | 25 | 72.0% |
| T | matched | 14 | 25 | 56.0% |

### 5.3 项目交付指标

| 指标 | 数字 |
|---|---|
| 整体覆盖率 | 38.4% (12,221/31,866) |
| 算法精度(matched) | **69.0%** |
| 实际产生正确 ESCO 匹配 | **~8,400 条** |
| L 桶精度 | 92.0% |
| S 桶精度 | 72.0% |
| K 桶精度 | 56.0% |
| T 桶精度 | 56.0% |

## 6. 项目里程碑(版本演进)

| 版本 | matched 数 | 改进点 |
|---|---|---|
| v1 | 5,102 (16.0%) | 仅 embedding |
| v2 | 5,777 (18.1%) | T 桶阈值放宽 0.55 |
| v3 | 5,803 (18.2%) | 缩写字典 +23 |
| v4 | 5,875 (18.4%) | Tier 1 AC substring +72 |
| v5 | 10,627 (33.4%) | DeepSeek 第一轮 +4,752 |
| v6 | 12,189 (38.3%) | DeepSeek 补跑 +1,562 |
| **v7** | **12,189 (38.3%)** | **+ custom ID 兜底 19,674 条** |
| **v7+patch** | **12,221 (38.4%)** | **+ Tier 1 语言证书字典补 L 桶 +32** |

matched 数从 5,102 → 12,221,**翻了 2.4 倍**。

## 7. 仓库结构

```
span_type_esco_id_linkage/
├── README.md                  # 本文档
├── REPORT.md                  # 详细技术报告(算法演进/精度验证/复现步骤)
├── .gitignore
│
├── results/                   # 主交付物
│   ├── spans_with_esco.csv    # ★ 主交付:31,866 unique span → ESCO URI
│   ├── final_match_long.csv   # ★ 长表:90,625 行(每个出现)
│   ├── final_match_v7.csv     # 完整版(含 top-3 候选)
│   ├── gold_validated.csv     # 200 条 gold + DeepSeek 验证
│   ├── gold_sample.csv        # 200 条 gold 抽样
│   ├── postfix_match.csv      # Tier 1 缩写命中(23)
│   ├── tier1_ac_match.csv     # Tier 1 AC 命中(72)
│   └── a_prime_summary.md     # 关键数字摘要
│
├── data/                      # 标准库与输入数据
│   ├── step3_skill_annotation_20260810_012339.csv  # ★ LKST 标注输入(5,140 条)
│   ├── esco_clean.csv         # 13,939 ESCO 概念 + LKST 映射
│   ├── spans_unique.csv       # 31,866 unique (span, type) 池(算法产出)
│   ├── input_format.md        # 输入 CSV 格式约定(11 列 + LKST 体系)
│   └── input_sample.csv       # 5 行虚构示例
│
├── pipeline/                  # 主流水线(按步骤分目录)
│   ├── 01_数据准备/
│   │   ├── _01_prep_esco.py
│   │   ├── _02_prep_spans.py
│   │   ├── _download_esco.py
│   │   └── _download_esco_en.py
│   ├── 02_Embedding生成/
│   │   └── _06_embed_all.py
│   ├── 03_基础匹配/
│   │   ├── _07_match.py
│   │   └── _13_final_v2.py
│   ├── 04_T桶调参/
│   │   └── _12_inspect_T.py
│   ├── 05_字典与AC/
│   │   ├── _16b_postfix_fast.py     # 缩写字典(制造业,130+)
│   │   ├── _16c_lang_cert_patch.py  # 语言证书缩写字典(L 桶,100+)
│   │   └── _18_tier1_ac.py          # AC substring
│   ├── 06_DeepSeek仲裁/
│   │   ├── _15_deepseek_label.py
│   │   └── _21_rerun_review.py
│   ├── 07_合并与兜底/
│   │   ├── _20_merge_llm.py
│   │   ├── _22_merge_rerun.py
│   │   └── _23_custom_ids.py
│   └── 08_精度验证/
│       ├── _25_make_gold.py
│       └── _26_score_gold.py
│
└── experiments/               # 探索性脚本(调参/失败尝试)
    ├── _03_load_bge_m3.py
    ├── _04_smoke.py / _04b_smoke.py / _05_smoke_m3.py
    ├── _08_inspect.py / _09_inspect_dist.py
    ├── _10_tier1.py / _10b_tier1.py / _11_finalize.py
    ├── _14_review_sample.py
    ├── _16_postfix.py / _17_merge.py / _19_merge_v4.py
    └── _24_v7_stats.py
```

### 7.4 模型/缓存

- `models/models/sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/`:embedding 模型
- `models/models/BAAI--bge-m3/`:bge-m3 残骸(下载不完整,占位)
- `embeddings/`:8 个 .npy 缓存(ESCO 4 桶 + spans 4 桶)

## 8. 局限与已知问题

| 问题 | 原因 | 应对 |
|---|---|---|
| 缩写类(SPC/PFMEA/DOE) | 跨语种对齐差 | 已加 130+ 缩写扩展字典 |
| T 桶通用软技能 | 中文表达多样(沟通/沟通能力/沟通协调) | 加 80+ 同义词,T 桶阈值放宽 |
| L 桶证书(TEM-8/PMP/外语统称) | ESCO 英文 L 桶无中国考试 | 接受 no_match,用 custom ID 兜底 |
| 缩写精确匹配会有 substring 误中 | "solar energy" 因 "ste" 命中 "systems" | 缩停用词表 + word boundary |
| DeepSeek API 余额可能耗尽 | 大批量调用 | 两轮调用策略 + 监控 |

## 9. 结论

✅ **匹配算法开发完成,精度达到实用标准**

- **覆盖 38.4% span 找到真 ESCO URI**(12,221 条)
- **算法精度 69%**(在 matched 子集上,DeepSeek 独立验证)
- **L 桶 92%**(语言匹配最准)
- **兜底机制**:剩余 61.6% 用 custom ID 占位,**每条 span 都有 URI,覆盖率 100%**
- **下游可用**:`results/spans_with_esco.csv` 直接对接 ESCO 兼容系统

适合作为"用 LLM 抽 span + 算法链 ESCO"两阶段方案中的第二阶段实现。

## 10. 后续可选工作(未做)

- [ ] 把 v7 推到全量 90,625 行(已部分在 long 表)
- [ ] 抽 200 条做**人标 gold**替代 DeepSeek 验证,得真 a%(非下界)
- [ ] 试 bge-m3 跑全量(若能下完,跨语种更准)
- [ ] 收集 3 个版本数据(每年 5,000+ job),用本算法批处理
- [ ] 对 22K custom ID 做二次 LLM 扫一遍,看有没有遗漏的 ESCO

## 11. 复现

依赖:Python 3.11+、`sentence-transformers`、`torch`、`transformers`、`requests`,以及环境变量 `DEEPSEEK_API_KEY`(用于 Tier 3)。

```bash
git clone https://github.com/ddj277happy-png/span_type_esco_id_linkage.git
cd span_type_esco_id_linkage
export DEEPSEEK_API_KEY=sk-...
pip install sentence-transformers torch transformers requests
```

把 LKST 标注 CSV 放到 `data/` 下(文件名不限,脚本自动识别,本仓库已附一份示例),格式见 [`data/input_format.md`](data/input_format.md),参考 `data/input_sample.csv`,然后:

```bash
# 01 数据准备
python pipeline/01_数据准备/_01_prep_esco.py        # ESCO CSV → data/esco_clean.csv
python pipeline/01_数据准备/_02_prep_spans.py       # 输入标注 → data/spans_unique.csv

# 02 Embedding 生成
python pipeline/02_Embedding生成/_06_embed_all.py  # → embeddings/

# 03 基础匹配
python pipeline/03_基础匹配/_07_match.py            # cos 匹配,出 v1
python pipeline/03_基础匹配/_13_final_v2.py         # T 桶阈值放宽,出 v2

# 05 字典 + AC
python pipeline/05_字典与AC/_16b_postfix_fast.py    # 缩写字典(制造业)
python pipeline/05_字典与AC/_16c_lang_cert_patch.py # 语言证书缩写字典(L 桶补丁)
python pipeline/05_字典与AC/_18_tier1_ac.py         # AC substring

# 06 DeepSeek 仲裁
python pipeline/06_DeepSeek仲裁/_15_deepseek_label.py
python pipeline/06_DeepSeek仲裁/_21_rerun_review.py

# 07 合并 + 兜底
python pipeline/07_合并与兜底/_20_merge_llm.py
python pipeline/07_合并与兜底/_22_merge_rerun.py
python pipeline/07_合并与兜底/_23_custom_ids.py     # → v7

# 08 精度验证
python pipeline/08_精度验证/_25_make_gold.py
python pipeline/08_精度验证/_26_score_gold.py
```

主交付物在 `results/`:`spans_with_esco.csv`(主)、`final_match_long.csv`(长表)、`gold_validated.csv`(精度证据)。详细复现见 [REPORT.md §6](REPORT.md)。

## 12. 一句话总结

3 层 Tier 兜底的 span → ESCO URI 匹配算法:DeepSeek 验证精度 69%(L 桶 92%),覆盖 38.4% span 出真 ESCO URI,剩余 61.6% 用稳定 custom ID 占位,**100% 有 ID 可用**。
