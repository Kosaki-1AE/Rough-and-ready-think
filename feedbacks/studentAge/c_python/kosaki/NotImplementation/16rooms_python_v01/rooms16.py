# -*- coding: utf-8 -*-
"""16Rooms demonstrator: standard library only, Python 2.7 / 3 syntax.

The rules and numeric scores are provisional engineering choices, not learned
logic, measured dance quality, or proven 30-ms real-time performance.
"""
from __future__ import print_function
import argparse
import json
import os

NAMES = ['Input', 'Buffer', 'Pool', 'Queue', 'Motion', 'Stack',
         'Coherence', 'Capacity', 'Jab', 'Quality', 'Twist',
         'Stillness', 'Depth', 'Straight', 'Output', 'Genesis']
MAIN = [15] + list(range(12))
THRESHOLDS = dict((name, 0.5) for name in NAMES)
THRESHOLDS.update({'Coherence': 0.7, 'Capacity': 0.5,
                   'Quality': 0.75, 'Stillness': 0.5, 'Output': 1.0})


def pack_register(slot, output, room, input_bit):
    """BB|O|RRRR|I. Slot is a 2-bit shortlist slot, not full memory."""
    if not (0 <= slot <= 3 and output in (0, 1) and
            0 <= room <= 15 and input_bit in (0, 1)):
        raise ValueError('Invalid 8-bit control register field')
    return (slot << 6) | (output << 5) | (room << 1) | input_bit


def unpack_register(value):
    if not 0 <= value <= 255:
        raise ValueError('Register value out of range')
    return {'slot': (value >> 6) & 3, 'output': (value >> 5) & 1,
            'room': (value >> 1) & 15, 'input': value & 1}


class Backrooms(object):
    """Confirmed, referenceable symbolic chunks, not waveform storage."""
    def __init__(self, filename=None):
        self.filename = filename
        self.chunks = {}
        if filename and os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.chunks = data

    def get(self, context, symbol):
        return self.chunks.get(context + '|' + symbol)

    def observe(self, context, symbol, path, verified):
        # Three independent verified experiences grant reuse; errors never do.
        key = context + '|' + symbol
        entry = self.chunks.get(key)
        if entry is None:
            entry = {'context': context, 'symbol': symbol, 'successes': 0,
                     'reusable': False, 'path': [], 'failures': 0}
            self.chunks[key] = entry
        if verified:
            entry['successes'] += 1
            entry['path'] = list(path)
            if entry['successes'] >= 3:
                entry['reusable'] = True
        else:
            entry['failures'] += 1
            entry['reusable'] = False  # conflicting evidence suspends reuse
            entry['successes'] = 0
        return dict(entry)

    def save(self):
        if self.filename:
            with open(self.filename, 'w') as f:
                json.dump(self.chunks, f, indent=2, sort_keys=True)


def run_one(symbol, context, expected=None, memory=None, thresholds=None,
            force_deep=False, input_bit=1):
    """Run one *symbolic event*, not a whole video/frame stream.

    Context and labels are supplied by a caller. 'tan' and 'ta' are just
    names; the program makes no unsupported duration/strength assumptions.
    """
    if memory is None:
        memory = Backrooms()
    if thresholds is None:
        thresholds = THRESHOLDS
    trace, passed = [], {}
    candidate = memory.get(context, symbol)
    # At most four active candidates are addressable by the BB field.
    slot = 0
    result = None
    explanation = []
    status = 'HOLD'
    reason = ''
    path = MAIN + ([12, 13, 14] if (force_deep or not (candidate and candidate.get('reusable'))) else [14])
    # 16 room visits for deep branch, 14 visits for direct branch.
    if len(path) > 16:
        raise AssertionError('16Rooms budget exceeded')
    for room in path:
        name = NAMES[room]
        absolute = True
        score = 1.0
        why = 'Basic precondition satisfied'
        if name == 'Genesis':
            absolute = (context is not None)
            why = 'Keep preceding context identifier'
        elif name == 'Input':
            absolute = isinstance(symbol, str) and len(symbol) > 0
            why = 'Accept one symbolic input event'
        elif name == 'Buffer':
            absolute = len(symbol) <= 64 if isinstance(symbol, str) else False
            why = 'Validate event representation'
        elif name == 'Pool':
            why = 'Hold candidate or unknown identifier'
        elif name == 'Queue':
            why = 'Place candidate in work queue'
        elif name == 'Motion':
            why = 'Propose action associated with input/context'
        elif name == 'Stack':
            why = 'Compare proposal against previous chunk'
        elif name == 'Coherence':
            score = 1.0 if candidate and candidate.get('reusable') else 0.75
            why = 'Context-symbol consistency (provisional score)'
        elif name == 'Capacity':
            score = 1.0 if len(memory.chunks) < 10000 else 0.0
            why = 'Local chunk capacity budget (10,000 entries)'
        elif name == 'Jab':
            why = 'Tentative fallback proposal'
        elif name == 'Quality':
            # In a supervised demonstration a known label is essential for
            # verifiable acceptance. Unknown outcomes are held, not invented.
            score = 1.0 if expected is not None and expected == symbol else 0.0
            why = 'Does supervised target match observed symbol?'
        elif name == 'Twist':
            why = 'Alternative candidate considered (placeholder)'
        elif name == 'Stillness':
            why = 'Review quality, coherence and capacity gates'
        elif name == 'Depth':
            why = 'Inspect unresolved candidate pool'
        elif name == 'Straight':
            why = 'Try direct candidate from pool'
        elif name == 'Output':
            score = 1.0 if (passed.get('Coherence') and
                            passed.get('Capacity') and
                            passed.get('Quality')) else 0.0
            why = 'Release only if all three gates passed'
        threshold = float(thresholds.get(name, 0.5))
        ok = absolute and score >= threshold
        passed[name] = ok
        reg = pack_register(slot, 1 if name == 'Output' and ok else 0,
                            room, input_bit)
        trace.append({'room': room, 'name': name, 'score': score,
                      'threshold': threshold, 'absolute': absolute,
                      'pass': ok, 'register': reg, 'explanation': why})
        explanation.append('%s: %s [score %.2f / %.2f]' %
                           (name, why, score, threshold))
        if not absolute:
            status = 'FAIL'
            reason = 'Absolute condition failed at ' + name
            break
        if not ok:
            status = 'HOLD'
            reason = 'Below evaluation gate at ' + name
            break
    else:
        status = 'PASS'
        result = symbol
        reason = 'Output accepted after mandatory checks'
    chunk = None
    if expected is not None:
        # Store verified observations only on accepted predictions; a false
        # expected symbol also counts as conflicting evidence for that key.
        chunk = memory.observe(context, symbol,
                               [x['room'] for x in trace],
                               status == 'PASS' and symbol == expected)
    return {'symbol': symbol, 'context': context, 'expected': expected,
            'status': status, 'result': result, 'reason': reason,
            'path': [x['name'] for x in trace], 'trace': trace,
            'steps': len(trace), 'explanation': explanation, 'chunk': chunk}


def demo(filename=None):
    memory = Backrooms(filename)
    scenarios = [('tan', 'flow_A', 'tan', False),
                 ('tan', 'flow_A', 'tan', False),
                 ('tan', 'flow_A', 'tan', False),
                 ('tan', 'flow_A', 'tan', False),
                 ('ta', 'flow_A', None, True),
                 ('tan', 'flow_A', 'ta', False)]
    for i, (symbol, context, expected, deep) in enumerate(scenarios):
        out = run_one(symbol, context, expected, memory, force_deep=deep)
        print('case %d | event=%s | expected=%s | %s | rooms=%d' %
              (i + 1, symbol, expected, out['status'], out['steps']))
        print(' path: ' + ' > '.join(out['path']))
        print(' reason: ' + out['reason'])
        if out['chunk']:
            print(' verified=%d reusable=%s' %
                  (out['chunk']['successes'], out['chunk']['reusable']))
    memory.save()


def tests():
    for v in range(256):
        bits = unpack_register(v)
        assert pack_register(bits['slot'], bits['output'],
                             bits['room'], bits['input']) == v
    m = Backrooms()
    for i in range(3):
        r = run_one('tan', 'flow_A', 'tan', m)
        assert r['status'] == 'PASS'
        assert r['steps'] <= 16
        assert 'Depth' in r['path']
        assert r['chunk']['reusable'] == (i == 2)
    r = run_one('tan', 'flow_A', None, m)
    assert r['status'] == 'HOLD' and r['reason'].endswith('Quality')
    direct = run_one('tan', 'flow_A', 'tan', m)
    assert direct['status'] == 'PASS' and direct['steps'] == 14
    deep = run_one('ta', 'flow_A', 'ta', m, force_deep=True)
    assert deep['status'] == 'PASS' and deep['steps'] == 16
    assert 'Depth' in deep['path'] and 'Straight' in deep['path']
    bad = run_one('', 'flow_A', '', m)
    assert bad['status'] == 'FAIL' and bad['steps'] <= 16
    low = dict(THRESHOLDS)
    low['Coherence'] = 0.8
    held = run_one('new', 'flow_A', 'new', m, thresholds=low)
    assert held['status'] == 'HOLD' and held['path'][-1] == 'Coherence'
    error = run_one('tan', 'flow_A', 'ta', m)
    assert error['status'] == 'HOLD' and not error['chunk']['reusable']
    print('OK: 256 registers, gates, HOLD/FAIL, 3 confirmations, branching, 16-room bound')


def main():
    parser = argparse.ArgumentParser(description='16Rooms symbolic event demonstrator')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--memory', default=None)
    args = parser.parse_args()
    if args.test:
        tests()
    else:
        demo(args.memory)


if __name__ == '__main__':
    main()
