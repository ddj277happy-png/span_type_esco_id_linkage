# -*- coding: utf-8 -*-
"""
16c_lang_cert_patch.py
Tier 1 补丁:语言证书缩写字典(LANG_CERT_ABBREV)

目的:解决 L 桶 no_match 中"语言证书缩写无法被 embedding 抓住"的问题
(例: DALF-C1/CATTI笔译二级/TOPIK5级/TEM-8 等,字面跟语言名无相似度)

输入: results/spans_with_esco.csv
处理: 对 L 桶 status=no_match 的行,查 LANG_CERT_ABBREV 字典,
      命中后查 ESCO L 桶的 preferredLabel,得到 URI,status 改为 matched
输出: 就地更新 results/spans_with_esco.csv

设计:
- 字典 100+ 条,覆盖中国/欧洲/亚洲主流语言证书
- 查表时先尝试原样,再尝试 .upper() (兼顾大小写)
- 命中后 uri 来自 ESCO L 桶(经 L_URI 索引),非空字符串
- 多次运行安全(status 已是 matched 的不会被改)
"""
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
ESCO_CSV = BASE / 'data' / 'esco_clean.csv'
SPANS_CSV = BASE / 'results' / 'spans_with_esco.csv'

# === 语言证书缩写字典(span -> ESCO L 桶 preferredLabel 英文) ===
LANG_CERT_ABBREV = {
    # 法语
    'DALF': 'french', 'DALF-C1': 'french', 'DALF-C2': 'french',
    'DELF': 'french', 'DELF-A1': 'french', 'DELF-A2': 'french',
    'DELF-B1': 'french', 'DELF-B2': 'french',
    'TCF': 'french', 'TEF': 'french', 'TEFAQ': 'french',
    # 英语(主流考试)
    'IELTS': 'english', 'TOEFL': 'english', 'TOEFL-iBT': 'english',
    'PTE': 'english', 'CAE': 'english', 'FCE': 'english',
    'KET': 'english', 'PET': 'english',
    'BEC': 'english', 'BEC-Preliminary': 'english', 'BEC-Vantage': 'english', 'BEC-Higher': 'english',
    'BULATS': 'english', 'TOEIC': 'english', 'GRE': 'english', 'GMAT': 'english',
    'LSAT': 'english', 'SAT': 'english', 'ACT': 'english',
    # 英语(中国本土)
    'CATTI': 'english', 'CATTI笔译': 'english', 'CATTI口译': 'english',
    'CATTI笔译二级': 'english', 'CATTI笔译三级': 'english',
    'CATTI口译二级': 'english', 'CATTI口译三级': 'english',
    'CATTI笔译证书': 'english', 'CATTI口译证书': 'english',
    '全国翻译资格水平考试': 'english',
    '专四': 'english', '专八': 'english', '英语专四': 'english', '英语专八': 'english',
    '英语专四证书': 'english', '英语专八证书': 'english',
    'TEM-4': 'english', 'TEM-8': 'english', 'TEM4': 'english', 'TEM8': 'english',
    'TEM4级': 'english', 'TEM8级': 'english',
    'CET-4': 'english', 'CET-6': 'english', 'CET4': 'english', 'CET6': 'english',
    'CET6级': 'english', 'CET4级': 'english',
    '大学英语四级': 'english', '大学英语六级': 'english',
    '大学英语4级': 'english', '大学英语6级': 'english',
    '英语CET-6级': 'english', '英语CET-4': 'english', '英语CET6级': 'english',
    '英语CET 6级': 'english',
    # 日语
    'JLPT': 'japanese', 'JLPT-N1': 'japanese', 'JLPT-N2': 'japanese',
    'JLPT-N3': 'japanese', 'JLPT-N4': 'japanese', 'JLPT-N5': 'japanese',
    'JLPT 1级': 'japanese', 'JLPT 2级': 'japanese',
    'JLPT 1': 'japanese', 'JLPT 2': 'japanese',
    'BJT': 'japanese',
    # 韩语
    'TOPIK': 'korean', 'TOPIK1级': 'korean', 'TOPIK2级': 'korean',
    'TOPIK3级': 'korean', 'TOPIK4级': 'korean', 'TOPIK5级': 'korean', 'TOPIK6级': 'korean',
    'TOPIK-Ⅰ': 'korean', 'TOPIK-Ⅱ': 'korean',
    'TOPIK 6级证书': 'korean', 'Topik 6级证书': 'korean',
    'KIIP': 'korean',
    # 西班牙语
    'DELE': 'spanish', 'DELE-A1': 'spanish', 'DELE-A2': 'spanish',
    'DELE-B1': 'spanish', 'DELE-B2': 'spanish', 'DELE-C1': 'spanish', 'DELE-C2': 'spanish',
    'SIELE': 'spanish',
    # 德语
    'TestDaF': 'german', 'Test-DaF': 'german',
    'Goethe': 'german', '歌德': 'german', '歌德B1': 'german', '歌德B2': 'german',
    # 俄语
    'TORFL': 'russian', 'ТРКИ': 'russian',
    # 意大利语
    'CILS': 'italian', 'CELI': 'italian', 'PLIDA': 'italian',
    # 葡萄牙语
    'CELPE-Bras': 'portuguese', 'CAPLE': 'portuguese',
    # 阿拉伯语
    'ALPT': 'arabic',
    # 中文(HSK)
    'HSK': 'chinese', 'HSK-1': 'chinese', 'HSK-2': 'chinese',
    'HSK-3': 'chinese', 'HSK-4': 'chinese', 'HSK-5': 'chinese', 'HSK-6': 'chinese',
    'HSKK': 'chinese', '汉语水平考试': 'chinese',
    '普通话': 'chinese', '普通话二甲': 'chinese', '普通话二乙': 'chinese',
    '普通话一甲': 'chinese', '普通话一乙': 'chinese',
    # 越南语
    'VSTEP': 'vietnamese',
    # 泰语
    'CU-TFL': 'thai',
}


def build_l_uri_index():
    """建 ESCO L 桶 preferredLabel/altLabels -> URI 的索引"""
    L_URI = {}
    with open(ESCO_CSV, encoding='utf-8-sig') as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            if r['lkst'] != 'L':
                continue
            lbl = (r.get('preferred_label') or '').strip()
            alts = (r.get('alt_labels') or '').replace('\n', '|').split('|')
            for s in [lbl] + alts:
                s = s.strip().lower()
                if s and s not in L_URI:
                    L_URI[s] = (r['uri'], lbl)
    return L_URI


def patch():
    L_URI = build_l_uri_index()
    rows = []
    with open(SPANS_CSV, encoding='utf-8-sig') as f:
        rdr = csv.DictReader(f)
        fieldnames = rdr.fieldnames
        for r in rdr:
            rows.append(r)

    # patch 前统计
    L_matched_before = sum(1 for r in rows if r['type'] == 'L' and r['status'] == 'matched')

    # patch
    patched = 0
    unmatched_examples = []
    for r in rows:
        if r['type'] == 'L' and r['status'] == 'no_match':
            span = r['span'].strip()
            lang = LANG_CERT_ABBREV.get(span) or LANG_CERT_ABBREV.get(span.upper())
            if lang:
                hit = L_URI.get(lang.lower())
                if hit:
                    uri, lbl = hit
                    r['esco_uri'] = uri
                    r['esco_label_en'] = lbl
                    r['score'] = '0.95'
                    r['status'] = 'matched'
                    patched += 1
                else:
                    unmatched_examples.append((span, lang))
            else:
                unmatched_examples.append((span, 'NO_DICT'))

    # patch 后统计
    L_matched_after = sum(1 for r in rows if r['type'] == 'L' and r['status'] == 'matched')

    # 写回
    with open(SPANS_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # 输出
    print(f'L bucket: matched {L_matched_before} -> {L_matched_after} (+{L_matched_after - L_matched_before})')
    print(f'Patched (L no_match -> matched) rows: {patched}')
    print(f'Saved: {SPANS_CSV}')

    # 写 unmatched 例子
    with open(BASE / '_L_nomatch_after_dict.txt', 'w', encoding='utf-8') as f:
        f.write(f'PATCH 后 L 桶 unmatched 例子({len(unmatched_examples)}):\n')
        f.write('=' * 60 + '\n')
        seen = set()
        for s, l in unmatched_examples:
            if s not in seen:
                seen.add(s)
                f.write(f'{s!r}  ({l})\n')


if __name__ == '__main__':
    patch()
