# -*- coding: utf-8 -*-
"""16Rooms dance/robot prototype. Python 2.7+ / Python 3.x; standard library only.
READ-ONLY decision engine. Never sends motor commands.
"""
from __future__ import print_function
import argparse
import csv
import json
import math
import os
import sys
import time
import xml.etree.ElementTree as ET

ROOMS = ['Input', 'Buffer', 'Pool', 'Queue', 'Motion', 'Stack', 'Coherence',
         'Capacity', 'Jab', 'Quality', 'Twist', 'Stillness', 'Depth',
         'Straight', 'Output', 'Genesis']
PATH_BASE = [15] + list(range(0, 12))  # Genesis then Input ... Stillness (13)


def read_csv(path):
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def number(value, default=None):
    try:
        n = float(value)
        if not math.isfinite(n) if hasattr(math, 'isfinite') else (math.isnan(n) or math.isinf(n)):
            return default
        return n
    except (TypeError, ValueError):
        return default


def clamp(x):
    return max(0.0, min(1.0, x))


def pack8(candidate, output, room, inp):
    if not (0 <= candidate <= 3 and output in (0, 1) and 0 <= room <= 15 and inp in (0, 1)):
        raise ValueError('invalid 8-bit register fields')
    return (candidate << 6) | (output << 5) | (room << 1) | inp


def unpack8(value):
    return ((value >> 6) & 3, (value >> 5) & 1, (value >> 1) & 15, value & 1)


def load_memory(path):
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_memory(path, obj):
    if not path:
        return
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def relative_angles(rows):
    """Use observed/teacher numeric feature columns, normalized by tolerances.
    No hidden assumption that video observation equals force/contact sensation.
    """
    errors = []
    weights = []
    for row in rows:
        for name, tol in [('hip_angle', 35.0), ('knee_angle', 35.0),
                          ('ankle_angle', 35.0), ('shoulder_angle', 35.0),
                          ('motion_phase', 0.25)]:
            a = number(row.get('obs_' + name))
            b = number(row.get('ref_' + name))
            if a is not None and b is not None:
                errors.append(min(1.0, abs(a-b)/tol))
                weights.append(1.0)
    if not errors:
        return None
    return clamp(1.0 - sum(errors) / len(errors))


def process_sample(sample, memory, robot_rows=None):
    """One decision per chunk/event. Quantities derived from input rows; thresholds are hypotheses."""
    tick = time.perf_counter if hasattr(time, 'perf_counter') else time.time
    start = tick()
    cid = sample.get('chunk_id', '').strip()
    label = sample.get('event_id', '').strip()
    phase = number(sample.get('beat_phase'))
    cue = number(sample.get('entry_time_ms'))
    now = number(sample.get('observed_time_ms'))
    duration = number(sample.get('eight_duration_ms'))
    visibility = number(sample.get('visibility'))
    valid = bool(cid and label and duration is not None and duration > 0 and
                 phase is not None and 0 <= phase < 1.000001)
    entry_error = None if cue is None or now is None or duration is None or duration <= 0 else abs(now-cue) / duration
    timing_score = None if entry_error is None else clamp(1.0-entry_error*8.0)
    pose_score = relative_angles([sample])
    # Perception quality is not correctness; measured separately from imitation error.
    sensor_score = visibility if visibility is not None and 0 <= visibility <= 1 else None
    # Optional robot feedback is descriptive only, not safe to drive on its own.
    robot_error = None
    if robot_rows:
        matches = [r for r in robot_rows if r.get('event_id') == label]
        errs = []
        for r in matches:
            target, actual = number(r.get('target_rad')), number(r.get('actual_rad'))
            if target is not None and actual is not None:
                errs.append(abs(actual-target))
        if errs:
            robot_error = sum(errs)/len(errs)
    hist = memory.get(cid, {'verified_experiences': 0, 'uses': 0, 'last_status': ''})
    reusable = hist.get('verified_experiences', 0) >= 3
    # Human-supplied quality label is external verification, never a discovered truth.
    teacher = sample.get('teacher_verified', '').strip().lower()
    verified = teacher in ('yes', '1', 'true')
    scores = {
        'Input': (1.0 if valid else 0.0, 1.0, 'valid_schema'),
        'Buffer': (sensor_score, 0.60, 'visibility_proxy'),
        'Pool': (1.0, 0.50, 'candidate_available'),
        'Queue': (timing_score, 0.60, 'entry_alignment'),
        'Motion': (pose_score, 0.55, 'pose_similarity'),
        'Stack': (pose_score, 0.55, 'reference_comparison'),
        'Coherence': (pose_score, 0.60, 'observed_joint_consistency_proxy'),
        'Capacity': (1.0, 0.50, 'candidate_exists'),
        'Jab': (pose_score, 0.50, 'fallback_candidate_proxy'),
        'Quality': (min(x for x in [sensor_score, pose_score, timing_score] if x is not None)
                    if all(x is not None for x in (sensor_score, pose_score, timing_score)) else None,
                    0.60, 'minimum_required_score'),
        'Twist': (pose_score, 0.50, 'alternative_candidate_proxy'),
        'Stillness': (1.0, 0.50, 'global_review'),
        'Depth': (pose_score, 0.55, 'fallback_review'),
        'Straight': (pose_score, 0.55, 'conservative_reference'),
        'Output': (1.0, 1.0, 'decision_output'),
        'Genesis': (1.0, 1.0, 'last_input_observation'),
    }
    # Gate: absolute (hard) constraints cannot be relaxed by confidence.
    if not valid:
        scores['Input'] = (0.0, 1.0, 'invalid_input')
    path = PATH_BASE + ([14] if reusable else [12,13,14])
    logs = []
    status, reason = 'PASS', 'all_gates_passed'
    for room in path:
        name = ROOMS[room]
        score, threshold, rule = scores[name]
        if score is None:
            result = 'HOLD'
            why = 'missing_measurement:' + rule
        elif score < threshold:
            result = 'FAIL' if name == 'Input' else 'HOLD'
            why = 'below_gate:' + rule
        else:
            result, why = 'PASS', rule
        outbit = 1 if name == 'Output' and result == 'PASS' else 0
        byte = pack8(1 if reusable else 0, outbit, room, 1 if valid else 0)
        logs.append({'event_id': label, 'chunk_id': cid, 'room_id': '%X' % room,
                     'room': name, 'score': '' if score is None else round(score, 5),
                     'threshold': threshold, 'gate': result, 'reason': why,
                     'register_hex': '%02X' % byte})
        if result != 'PASS':
            status, reason = result, why
            break
    # Only explicitly teacher-verified successful decisions count as verified experiences.
    if status == 'PASS' and verified:
        hist['verified_experiences'] = hist.get('verified_experiences', 0) + 1
    if status == 'PASS' and reusable:
        hist['uses'] = hist.get('uses', 0) + 1
    hist['last_status'] = status
    memory[cid] = hist
    elapsed = (tick()-start)*1000.0
    summary = {'event_id': label, 'chunk_id': cid, 'status': status, 'reason': reason,
               'rooms_visited': len(logs), 'decision_ms': round(elapsed, 4),
               'reuse_enabled_before': int(reusable), 'verified_by_teacher': int(verified),
               'verified_experiences_after': hist.get('verified_experiences', 0),
               'pose_similarity': '' if pose_score is None else round(pose_score, 5),
               'timing_score': '' if timing_score is None else round(timing_score, 5),
               'robot_mean_joint_error_rad': '' if robot_error is None else round(robot_error, 5)}
    return summary, logs


def run(args):
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    memory = load_memory(args.memory)
    obs = read_csv(args.input)
    robots = read_csv(args.robot_feedback) if args.robot_feedback else []
    summaries, history = [], []
    for row in obs:
        summary, trace = process_sample(row, memory, robots)
        summaries.append(summary)
        history.extend(trace)
    write_csv(os.path.join(args.out, 'decisions.csv'), summaries,
              ['event_id','chunk_id','status','reason','rooms_visited','decision_ms',
               'reuse_enabled_before','verified_by_teacher','verified_experiences_after',
               'pose_similarity','timing_score','robot_mean_joint_error_rad'])
    write_csv(os.path.join(args.out, 'room_history.csv'), history,
              ['event_id','chunk_id','room_id','room','score','threshold','gate','reason','register_hex'])
    write_csv(os.path.join(args.out, 'chunks.csv'),
              [dict(chunk_id=k, **v) for k,v in sorted(memory.items())],
              ['chunk_id','verified_experiences','uses','last_status'])
    save_memory(args.memory, memory)
    for s in summaries:
        print('%s %-12s %-4s rooms=%d time=%.3fms reuse=%d' %
              (s['event_id'], s['chunk_id'], s['status'], s['rooms_visited'],
               s['decision_ms'], s['reuse_enabled_before']))
    print('CSV output: ' + os.path.abspath(args.out))


def urdf(args):
    """Transform joint origins through parent link frames at q=0; only fixed origins and RPY.
    The result is the URDF zero-configuration reference, not actual pose or collision bounds.
    """
    root = ET.parse(args.urdf).getroot()
    joints = []
    for j in root.findall('joint'):
        parent, child, origin = j.find('parent'), j.find('child'), j.find('origin')
        if parent is None or child is None:
            continue
        def triple(s, default):
            items = (s or default).split()
            return tuple(float(x) for x in items)
        xyz = triple(origin.get('xyz') if origin is not None else None, '0 0 0')
        rpy = triple(origin.get('rpy') if origin is not None else None, '0 0 0')
        axis_el, limit = j.find('axis'), j.find('limit')
        axis = triple(axis_el.get('xyz') if axis_el is not None else None, '1 0 0')
        joints.append((j.get('name'),j.get('type'),parent.get('link'),child.get('link'),xyz,rpy,axis,limit))
    # standard R=Rz(yaw)Ry(pitch)Rx(roll)
    def rotate(v,rpy):
        r,p,y = rpy
        cr,sr,cp,sp,cy,sy = math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
        x0, y0, z0 = v
        x1,y1,z1 = x0,cr*y0-sr*z0,sr*y0+cr*z0
        x2,y2,z2 = cp*x1+sp*z1,y1,-sp*x1+cp*z1
        return (cy*x2-sy*y2,sy*x2+cy*y2,z2)
    def mat_mul(a,b):
        return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    def matrix(rpy):
        basis = [rotate((1,0,0),rpy),rotate((0,1,0),rpy),rotate((0,0,1),rpy)]
        return [[basis[j][i] for j in range(3)] for i in range(3)]
    ident = [[1,0,0],[0,1,0],[0,0,1]]
    child_links = set(j[3] for j in joints)
    roots = set(j[2] for j in joints) - child_links
    states = dict((r,((0.0,0.0,0.0),ident)) for r in roots)
    remaining = list(joints)
    values = []
    while remaining:
        progress = False
        for j in remaining[:]:
            name,typ,parent,child,xyz,rpy,axis,limit=j
            if parent not in states:
                continue
            origin,Rp=states[parent]
            xyz_global=tuple(origin[i]+sum(Rp[i][k]*xyz[k] for k in range(3)) for i in range(3))
            Rj=mat_mul(Rp,matrix(rpy))
            states[child]=(xyz_global,Rj)
            x,y,z=xyz_global
            values.append({'joint':name,'type':typ,'parent':parent,'child':child,
                           'local_x':xyz[0],'local_y':xyz[1],'local_z':xyz[2],
                           'root_x':x,'root_y':y,'root_z':z,
                           'w_xy':str(round(x,6))+'+'+str(round(y,6))+'i',
                           'abs_xy':math.hypot(x,y),
                           'w_xz':str(round(x,6))+'+'+str(round(z,6))+'i',
                           'abs_xz':math.hypot(x,z),
                           'w_yz':str(round(y,6))+'+'+str(round(z,6))+'i',
                           'abs_yz':math.hypot(y,z),
                           'axis_x':axis[0],'axis_y':axis[1],'axis_z':axis[2],
                           'lower':limit.get('lower','') if limit is not None else '',
                           'upper':limit.get('upper','') if limit is not None else ''})
            remaining.remove(j)
            progress=True
        if not progress:
            raise ValueError('URDF linkage unresolved (cycle/missing parent): '+str([j[0] for j in remaining]))
    fields=['joint','type','parent','child','local_x','local_y','local_z',
            'root_x','root_y','root_z','w_xy','abs_xy','w_xz','abs_xz','w_yz','abs_yz',
            'axis_x','axis_y','axis_z','lower','upper']
    write_csv(args.out, values,fields)
    print('Extracted %d joints to %s (zero configuration; relative to URDF root)' % (len(values),args.out))


def main():
    parser=argparse.ArgumentParser(description='16Rooms Dance + Robot offline, read-only prototype')
    sub=parser.add_subparsers(dest='command')
    p=sub.add_parser('run')
    p.add_argument('--input', required=True,help='CSV: one decision/event per row')
    p.add_argument('--memory', default='backrooms.json')
    p.add_argument('--robot-feedback', default=None)
    p.add_argument('--out', default='output')
    u=sub.add_parser('urdf')
    u.add_argument('--urdf',required=True)
    u.add_argument('--out',default='joints_complex.csv')
    args=parser.parse_args()
    if args.command=='run':
        run(args)
    elif args.command=='urdf':
        urdf(args)
    else:
        parser.print_help()

if __name__=='__main__':
    main()
