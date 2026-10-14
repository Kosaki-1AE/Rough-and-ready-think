"""Compare v0.8 outputs; verify route-independent decisions and readout differences.

Usage: python compare_routes.py output_normal/gated_layer_timeline.csv output_bypass/gated_layer_timeline.csv --out route_comparison.json
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def compare(normal_path, bypass_path):
    a,b=read(normal_path),read(bypass_path)
    keys=('source','time_s','event','reason','novelty','reference_id')
    count_equal=len(a)==len(b)
    matches=sum(all(x.get(k)==y.get(k) for k in keys) for x,y in zip(a,b))
    differing_rooms=sum(x['room_after']!=y['room_after'] for x,y in zip(a,b))
    different_readouts=sum(x.get('room_output')!=y.get('room_output') for x,y in zip(a,b))
    return {
        'normal_rows':len(a),'bypass_rows':len(b),
        'same_row_count':count_equal,
        'identical_gate_rows':matches,
        'gate_decisions_identical':count_equal and matches==len(a),
        'different_room_rows':differing_rooms,
        'different_operator_output_rows':different_readouts,
        'normal_event_counts':dict(Counter(x['event'] for x in a)),
        'bypass_event_counts':dict(Counter(x['event'] for x in b)),
        'interpretation':'Independent gate is verified only for these inputs. Operators do not feed back.'
    }


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('normal',type=Path)
    ap.add_argument('bypass',type=Path)
    ap.add_argument('--out',type=Path,default=Path('route_comparison.json'))
    args=ap.parse_args()
    result=compare(args.normal,args.bypass)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
