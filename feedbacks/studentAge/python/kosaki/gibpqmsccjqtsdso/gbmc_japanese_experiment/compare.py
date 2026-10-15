from pathlib import Path
from collections import Counter
import csv

path = Path(__file__).with_name('pairs.csv')
with path.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print(f'比較対象: {len(rows)}組')
for k, v in Counter(row['判定'] for row in rows).items():
    print(f'{k}: {v}組')
for row in rows:
    print(f"\n[{row['番号']}] {row['判定']} / {row['題材']}")
    print('共通条件:', row['共通意味条件'])
    print('差分:', row['意味差分'])
