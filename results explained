9 个文件,按"主交付 / 中间产物 / 验证 / 报告"四类来分:

## 1. 主交付物(给下游用,3 个)

### ★ `spans_with_esco.csv` — 简化版
- **90,626 行**(≈ 90,625 long 表 + 1 表头)
- 列:`span, type, esco_uri, esco_label_en, score, status`
- 用法:**直接读这个就行**,列最少最干净
- 适合:做下游"出海岗位技能分布"统计 / 喂给 BI 工具

### ★ `final_match_v7.csv` — 完整版
- **31,867 行**(31,866 unique + 1 表头)
- 比 spans_with_esco **多两列**:`span_count`(出现次数)、`top3`(top-3 候选)
- `top3` 字段长这样:`uri_1|Portuguese|0.703 || uri_2|English|0.620 || uri_3|write English|0.577`
- 用法:**人工 review 候选匹配**——看 top-3 决定要不要换主选

### ★ `final_match_long.csv` — 长表(带岗位上下文)
- **90,626 行**
- 列:`job_id, company, title, city, matched_languages, span, type, esco_uri, esco_label_en, score, status`
- 把 unique 层的匹配**展开回 90,625 行**——每行都是一次"在某具体岗位上,某个 span 匹配到某 ESCO URI"
- 用法:**"按城市/公司/岗位类型统计技能需求"**——这种 job 级分析只能用这个

> **怎么选**:做 unique 维度分析 → `spans_with_esco.csv`;看 top-3 候选 → `final_match_v7.csv`;做岗位维度分析 → `final_match_long.csv`。三选一别混。

## 2. 中间产物(算法演进产物,2 个)

### `postfix_match.csv` — 缩写字典命中
- **27 行**
- 来源:`_16b_postfix_fast.py`——一张手工/半自动的"行业缩写 → ESCO 概念"字典(SPC=统计过程控制、FTA=失效分析等)
- `match_kind` 列:全是 `abbrev_K` / `abbrev_S` 这类
- 用法:看 v3 → v3+postfix 这步多出来的命中

### `tier1_ac_match.csv` — AC 字符串兜底
- **73 行**(v4 那 +72 hits 就在这)
- 来源:`_18_tier1_ac.py`——用 Aho-Corasick 在 ESCO altLabel 里查 span 是不是字符串命中
- 关键列:`matched_token`(实际命中的 token,比如 "PRINCE2" 命中了 "prince2")
- 用法:看 v3+postfix → v4 增量

## 3. 验证集(2 个,配套用)

### `gold_sample.csv` — 200 条 gold 抽样
- 抽 200 条 unique span,带原始上下文(job 标题、公司、job 文本片段)
- `judgment` / `gold_uri` / `gold_notes` 列是**人标结果**(你或团队标的标准答案)
- 用法:**人标 gold 的原始数据**

### `gold_validated.csv` — 200 条 + DeepSeek 验证
- 列比 sample **多了** `llm_judgment` / `llm_reason`
- DeepSeek 当独立 judge 跑了 200 条,给"算法匹配得对不对"的二次判断
- 用法:**生成 `a_prime_summary.md` 的源数据**

## 4. 报告(2 个 md)

### `a_prime_summary.md` — 算法精度报告
- 核心数字:**matched 子集 69.0%**(L=92%, S=72%, K=56%, T=56%)
- 整体覆盖率 **38.3%**
- 有效匹配率 **26.4%**(= 38.3% × 69%)
- 实际产生正确匹配 **~8,400 条**
- 还给了**对外交付话术模板**

### `no_match_analysis.md` — 200 条典型 no_match
- 按 L/K/S/T 桶 no_match 数量**等比抽样**
- L 桶抽 7 / K 抽 36 / S 抽 145 / T 抽 12
- 每条带:span / URI(实际是 custom 占位)/ 出处岗位 / 上下文
- 用途:**找规律**——为什么没匹配上,L 桶主要是 ESCO 没收录小语种,S 桶主要是中文业务词 / 复合长句

## 快速对照表

| 文件 | 行数 | 粒度 | 关键特征 | 何时用 |
|---|---|---|---|---|
| spans_with_esco.csv | 90,626 | 长表 | 列最简 | **下游用** |
| final_match_v7.csv | 31,867 | unique | 带 top-3 | **人工 review** |
| final_match_long.csv | 90,626 | 长表+上下文 | 带 job 信息 | **岗位级分析** |
| gold_sample.csv | 200 | gold 抽样 | 人标 | 验证基准 |
| gold_validated.csv | 200 | + DeepSeek | 双层标注 | 算精度 |
| postfix_match.csv | 27 | 中间产物 | 缩写命中 | 看 v3 增量 |
| tier1_ac_match.csv | 73 | 中间产物 | AC 字符串 | 看 v4 增量 |
| a_prime_summary.md | — | 报告 | 69%/92%/72%/56%/56% | **对外汇报** |
| no_match_analysis.md | 200 | 报告 | no_match 案例 | **找改进方向** |
