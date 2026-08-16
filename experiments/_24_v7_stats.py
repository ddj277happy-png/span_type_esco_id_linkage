# -*- coding: utf-8 -*-
import pandas as pd
v7 = pd.read_csv(r'D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\final_match_v7.csv', encoding='utf-8-sig')
long = pd.read_csv(r'D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\final_match_long.csv', encoding='utf-8-sig')

print('=== v7 unique span ===')
print(v7['status'].value_counts())
print()
print('By type x status:')
print(pd.crosstab(v7['type'], v7['status']))
print()

print('=== long 90625 rows ===')
print(long['status'].value_counts())
print()

print('=== URI prefix dist ===')
v7['uri_prefix'] = v7['esco_uri'].str.split(':').str[0]
print(v7['uri_prefix'].value_counts().head())
print()

print('=== Custom ID samples ===')
no_match_samples = v7[v7['status']=='no_match'][['span','type','esco_uri']].head(8)
for _, r in no_match_samples.iterrows():
    print(f'  [{r["type"]}] {str(r["span"])[:50]:50s} -> {r["esco_uri"]}')
