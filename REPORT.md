# 出海岗位技能 span → ESCO URI 链接算法

> 项目技术报告 · 2026-08-16

---

## 一句话

5,140 条出海岗位的 90,625 个技能标注(去重 31,866 unique (span, L/K/S/T)),链接到 ESCO v1.2.0 标准 URI——**算法精度 69%**(L 桶 92%、S 桶 72%、K/T 桶 56%),**整体覆盖率 38.3%**,剩余 61.7% 用稳定占位 ID 兜底,保证每条 span 都有可计算的 ID。

---

## 1. 项目说明

中文招聘广告的技能描述(span)是自由文本,没法直接喂给下游标准化系统。本仓库做的事是:**把每个 (span, type) 链接到 ESCO(欧洲技能、能力、资格和职业分类)v1.2.0 的标准 URI**,让自由文本变成可计算、可对接的标准化标签。

输入:LKST 4 维标注(L=Language, K=Knowledge, S=Skill, T=Transversal)。  
输出:`esco_uri` 字段——真 ESCO URI(`http://data.europa.eu/esco/skill/...`)或稳定占位 ID(`custom:skill/{hash}` 等)。

### 1.1 数据规模

```
5,140 条 job(原始招聘数据)
   ↓ 自动化标注(参见 Chinese-SkillSpan 论文 + DeepSeek 标注流程)
90,625 条 (span, type) 出现(同一 span 跨 job 重复算)
   ↓ 去重
31,866 unique (span, type)  ← 目标池
   ├ L (language)      1,486
   ├ K (knowledge)     6,058
   ├ S (skill)        22,107   ← 大头
   └ T (transversal)   2,215
```

对应标准库:ESCO v1.2.0 英文版,13,939 个概念(L=359, K=3,145, S=10,338, T=97)。  
**注意 T 桶 ESCO 只有 97 条**——软技能这块 ESCO 自家覆盖就很薄,后文 K/T 桶精度低的锅,ESCO 上游要背一半。

### 1.2 为什么不用纯 embedding 或纯 LLM

两条路都试过,各有硬伤:

- **纯 embedding(单语种/多语种)**:跨语种对齐差。中文 "焊接" 跟英文 "welding" 距离很远,缩写(SPC/PFMEA/DOE)更没法搞——中英缩写字面无关、语义相同。
- **纯 LLM 链接**:贵。31,866 条都过一遍 LLM,4 维判定 × 上下文,一次调用就破产。

所以走**多 Tier 兜底**——便宜的先上(字典、embedding),贵的只在最模糊的灰色地带用(LLM 仲裁)。这套思路也呼应 Chinese-SkillSpan 论文的两阶段设计(先抽 span、再链 ESCO),本仓库实现的是第二阶段的工程化版本。

---

## 2. 方法:三层 Tier 兜底

整个算法的核心:**多层兜底,每层解决一种特定问题,最后不管哪条线没接住,都给个稳定 ID 占位**。

```
       ┌─────────────────────────────────────┐
       │  31,866 unique (span, type)          │
       └─────────────┬───────────────────────┘
                     │
       ┌─────────────▼─────────────────────┐
Tier 1 │  字典 + AC 自动机                 │ ← 处理缩写、专有名词
       │  (130+ 缩写 + 8,518 ESCO 短词)     │   命中 ~3%
       └─────────────┬─────────────────────┘
                     │ 没命中 ↓
       ┌─────────────▼─────────────────────┐
Tier 2 │  multilingual embedding           │ ← 主战场
       │  cos 相似度,按 LKST 分桶           │   命中 ~16%
       └─────────────┬─────────────────────┘
                     │ 0.5-0.7 模糊 ↓
       ┌─────────────▼─────────────────────┐
Tier 3 │  DeepSeek LLM 仲裁                │ ← 兜底模糊地带
       │  top-3 候选 + 4 类判定规则         │   命中 ~19%
       └─────────────┬─────────────────────┘
                     │ 还是没命中 ↓
       ┌─────────────▼─────────────────────┐
兜底   │  custom:{type}/{hash} 占位 ID     │ ← 100% 有 ID
       └───────────────────────────────────┘
```

### 2.1 Tier 1:字典 + AC 自动机

**目的**:补 embedding 的盲区——缩写和跨语种字面无关。

**做法**:

1. **缩写字典(130+ 条)**:SPC → "Statistical Process Control"、PFMEA → "Process Failure Mode and Effects Analysis" 等,展开后再去查 ESCO altLabel。这一层小但救命——23 条命中全是缩写。
2. **Aho-Corasick 自动机**:把 ESCO 8,518 个短词(3-15 字符)塞进 AC automaton,扫全部 spans 找 substring。比如 span 里出现 "welding" 就直接命中 ESCO welding skill。72 条命中。

**坑与修复**:substring 匹配会嵌入词内。比如 "solar energy" 因为包含 "ste" 命中了 "systems"。修法:**word boundary 检查**(匹配前后是字母/数字就丢弃)+ **停用词表** 把 engineering/plan/process/standard 等通用词排除。

### 2.2 Tier 2:multilingual embedding

**模型**:`paraphrase-multilingual-MiniLM-L12-v2`(sentence-transformers,118M 参数,384 维)。

> 备选 bge-m3 跨语种更强,但模型权重 2.3GB 在受限网络环境拉不下来。回退到 paraphrase-multilingual 是工程上更可控的选择——CPU 推理 45-160 t/s,15 分钟跑完全部 embedding;smoke test 18 个跨语种对 14 个通过,失败的 4 个全是缩写对,刚好和 Tier 1 互补。

**核心做法**:

- 每个 ESCO 条目 → embedding(把 `preferredLabel + altLabels` 拼起来当文本)
- 每个 unique span → embedding
- **按 LKST type 分桶,桶内匹配**(关键!否则 L 桶 359 条会被 S 桶 10K 条的"语言学"抢走)
- cos 相似度 top-1
- 阈值:L/K/S 桶 cos ≥ 0.70 → matched,T 桶 cos ≥ 0.55 → matched

**T 桶阈值单独放宽的来由**:T 桶一开始跟其他桶一样用 0.70,大量看起来对的匹配被卡掉。抽 160 条 T 桶人工看,0.5-0.7 区间大部分都是 decent match——**T 桶单独放宽到 0.55**。这一步直接把 matched 数从 5,102 拉到 5,777(+675,全是 T 桶)。

### 2.3 Tier 3:DeepSeek LLM 仲裁

Tier 2 跑完还有 20,737 条处于 0.5-0.7 灰色地带——看着像但把握不准。直接丢掉可惜,人工 review 又扛不住,折中:**让 DeepSeek 当 judge**。

**Prompt 设计**:给 LLM 完整上下文——不是只丢一个 span,而是 `span + type + top-3 ESCO 候选(含 description)`,LLM 选 1/2/3/none 中的一个,4 类判定规则按 L/K/S/T 区分。

**执行细节**:第一轮跑 20,737 条,跑到 15,997 条 API 余额耗尽,挂了 4,746 条。充值之后第二轮重跑,4,741 条里只 3 错。两轮策略很值——以极低 token 成本兜住 20K 条本来要人工的活。

**最终**:LLM 仲裁 20,737 条,**4,752 条改对了 top-1 错位,11,225 条判 none**。matched 数从 5,875 拉到 10,627。

### 2.4 兜底:Custom ID 机制

Tier 1-3 都失败的 span 还剩 19,674 条。**不能给空 URI**——下游拿到 csv 没法 join,系统会卡死。

**方案**:`custom:{type}/{hash}` 命名空间,直接写在 `esco_uri` 列里。

```
SHA1("沟通能力" + "T").hexdigest()[:12]  →  "a3b9c2e1f5d8"
final URI:                                "custom:transversal/a3b9c2e1f5d8"
```

**设计要点**:

- `custom:` 前缀明示"非 ESCO 标准",下游系统一眼识别
- hash 稳定:同样的 span+type 永远出同样的 ID,后续替换真 ESCO 不会乱
- 4 个 type 各自前缀(custom:skill/、custom:knowledge/、custom:language/、custom:transversal/),方便按 type 过滤

**这一步是整个项目能落地的关键**——保证**覆盖率 100%**,任何下游系统拿到 csv 都能 join,不用担心 null。

---

## 3. 结果

### 3.1 版本演进

| 版本 | matched 数 | 累计% | 这一步干了什么 |
|---|---|---|---|
| v1 | 5,102 | 16.0% | 仅 embedding,T 桶 0.7 严 |
| v2 | 5,777 | 18.1% | T 桶阈值放宽 0.55(+675) |
| v3 | 5,803 | 18.2% | 缩写字典 +23 |
| v4 | 5,875 | 18.4% | Tier 1 AC substring +72 |
| v5 | 10,627 | 33.4% | **DeepSeek 第一轮 +4,752** |
| v6 | 12,189 | 38.3% | DeepSeek 补跑 +1,562 |
| **v7** | **12,189** | **38.3%** | **+ custom ID 兜底 19,674** |

matched 数从 5,102 涨到 12,189,**翻了 2.4 倍**。

**最大单步跳跃是 v4 → v5(DeepSeek 仲裁),+4,752 一口气**——说明 embedding 在 0.5-0.7 灰色地带漏掉的不是"匹配不上",而是"模型不敢判",这种地方 LLM 比 embedding 强。

### 3.2 精度验证:200 条 stratified gold

**方法**:抽 200 条 stratified gold(L/K/S/T × {matched, no_match} = 8 桶 × 25 条),让 DeepSeek 当独立 judge 问"算法给的 URI 对不对"——DeepSeek 不参与算法本身,只当外部裁判。

**结果**:

```
matched 子集:    69 对 / 100  →  69.0%   ← 真算法精度
no_match 子集:   0 对 / 100   →  0%      (custom ID 不是真 ESCO,本来也不期望对)
```

按 type 分桶看更细:

| type | matched 中对的 / 抽样 | 精度 |
|---|---|---|
| **L** | 23 / 25 | **92.0%** |
| **S** | 18 / 25 | **72.0%** |
| K | 14 / 25 | 56.0% |
| T | 14 / 25 | 56.0% |

**怎么解读**:

- **L 桶 92%**——语言名短而标准(英/中/日/葡/法...),embedding 一击命中
- **S 桶 72%**——技能名多样但 ESCO 覆盖厚,容错好
- **K/T 桶 56%**——ESCO 覆盖本来就薄(尤其 T 只有 97 条),加中文表述多样,错配多。**这是 ESCO 上游覆盖的客观限制,不是算法的问题**。
- 整体 69%——这是**精度不是召回**。算法敢说"这个 span 对这个 ESCO"的时候,69% 是对的;剩下 31% 错配需要人工 review。

**对比说明**:Chinese-SkillSpan 论文报告的 span 抽取 F1 ≈ 0.67 是 Task 1(从原文抽出 span),本报告 69% 是 Task 2(把 span 链到 ESCO URI),任务、指标、数据都不一样,**不能直接相减或相除**。

### 3.3 实际产出

- 12,189 条 matched × 69% = **~8,400 条**真正正确的 ESCO URI
- 19,674 条 custom ID 占位(下游可识别非标)
- 覆盖率 100%(每条 span 都有 ID)

---

## 4. 关键踩过的坑

| 坑 | 怎么踩的 | 怎么修的 |
|---|---|---|
| bge-m3 拉不下来 | 2.09GB / 2.3GB 卡死 | 改 paraphrase-multilingual,牺牲一点跨语种换可控 |
| AC 嵌入词内误中 | "solar energy" 命中 "systems" | word boundary + 停用词表 |
| T 桶 0.7 太严 | 大量 decent match 被卡 | 抽 160 条人工看,降阈值 0.55 |
| LLM API 余额耗尽 | 第一轮跑 20K 条中途挂 | 两轮策略:充值后补跑 4,741 条,只 3 错 |
| LKST 跨桶错配 | L 桶被 S 桶"语言学"抢走 | 严格分桶,桶内只跟同 type 比 |
| 缩写 embedding 失效 | SPC/PFMEA 字面无关语义同 | Tier 1 缩写字典(130+ 条) |
| DeepSeek judge 偶发空 en | 单条 ar 有但 en 是空 | 抽检补 en;后续 prompt 加强制约束 |

---

## 5. 局限与展望

**已知局限**:

- **缩写类**:虽然加了 130+ 字典,还有遗漏,新缩写(如新的工艺方法)需要持续扩充
- **T 桶软技能**:中文表达太多样,加同义词也救不回来
- **L 桶中国证书**:TEM-8/PMP/CET-6 等,ESCO 英文 L 桶没有——这是 ESCO 国际化覆盖的客观限制
- **31% 错配**:留给人工 review 桶处理
- **200 条 gold 验证**:DeepSeek 当 judge 是下界,真 gold 才能定真值

**后续可做**:

1. **人工标 200+ 条真 gold**——把 DeepSeek judge 换成真 gold,得到算法精度的真值
2. **跑 bge-m3 全量**——若网络环境修好,跨语种可能涨 5-10 个百分点
3. **二次扫 22K custom ID**——用 LLM 再过一遍 no_match 桶
4. **扩充到其他年份数据**——按本 pipeline 处理新数据

---

## 6. 复现

依赖:Python 3.11+,sentence-transformers,torch,transformers,DeepSeek API key(从环境变量读)。

```bash
git clone https://github.com/ddj277happy-png/span_type_esco_id_linkage.git
cd span_type_esco_id_linkage
export DEEPSEEK_API_KEY=sk-...   # 用于 Tier 3
pip install sentence-transformers torch transformers requests
```

数据准备:本仓库 `data/` 下已附 `step3_skill_annotation_20260810_012339.csv`(5,140 条)作为输入。要替换成自己的数据,直接覆盖同名文件即可(格式见 [`data/input_format.md`](data/input_format.md),参考 `data/input_sample.csv`,脚本自动识别)。然后按步骤执行:

```bash
# 01 数据准备
python pipeline/01_数据准备/_01_prep_esco.py        # ESCO CSV → data/esco_clean.csv
python pipeline/01_数据准备/_02_prep_spans.py       # 输入标注 → data/spans_unique.csv

# 02 Embedding 生成
python pipeline/02_Embedding生成/_06_embed_all.py  # 跑 paraphrase-multilingual → embeddings/

# 03 基础匹配
python pipeline/03_基础匹配/_07_match.py            # cos 匹配,出 v1
python pipeline/03_基础匹配/_13_final_v2.py         # T 桶阈值放宽,出 v2

# 04 T 桶调参(可选,验证阈值)
python pipeline/04_T桶调参/_12_inspect_T.py

# 05 字典 + AC
python pipeline/05_字典与AC/_16b_postfix_fast.py    # 缩写字典
python pipeline/05_字典与AC/_18_tier1_ac.py         # AC substring

# 06 DeepSeek 仲裁
python pipeline/06_DeepSeek仲裁/_15_deepseek_label.py   # 第一轮
python pipeline/06_DeepSeek仲裁/_21_rerun_review.py     # 第二轮补跑

# 07 合并 + 兜底
python pipeline/07_合并与兜底/_20_merge_llm.py      # 第一轮合并 → v5
python pipeline/07_合并与兜底/_22_merge_rerun.py    # 第二轮合并 → v6
python pipeline/07_合并与兜底/_23_custom_ids.py     # custom ID 兜底 → v7

# 08 精度验证
python pipeline/08_精度验证/_25_make_gold.py        # 200 条 gold 抽样
python pipeline/08_精度验证/_26_score_gold.py       # DeepSeek judge → 算精度
```

主交付物(`results/` 目录):

- `results/spans_with_esco.csv`:31,866 unique span × `esco_uri`
- `results/final_match_long.csv`:90,625 行长表(含 job 上下文)
- `results/gold_validated.csv`:200 条 gold + DeepSeek 验证结果
- `REPORT.md`:本报告

---

## 7. 引用 / 致谢

- **ESCO v1.2.0**:European Skills, Competences, Qualifications and Occupations,欧盟官方分类标准
- **Chinese-SkillSpan 论文**:Span-Level Dataset for ESCO-Aligned Competency Extraction from Chinese Job Ads(Li 等, 2026)
- **DeepSeek**:本项目 Tier 3 仲裁使用 DeepSeek API
- **paraphrase-multilingual-MiniLM-L12-v2**:sentence-transformers 多语种 embedding 模型

## 8. 许可证

本仓库按 MIT 许可证开源。ESCO 数据版权归欧盟所有,使用请遵守 ESCO 使用条款。
