# -*- coding: utf-8 -*-
"""16Rooms v1.1: offline, standard-library decision + feedback learning.
This software NEVER sends actuator commands. Commands are proposed for inspection.
Python 3.8+; optional live MediaPipe/OpenCV adapter in live_camera.py.
"""
import argparse
import csv
import json
import math
import os
import time
import xml.etree.ElementTree as ET

ROOMS = ['Input','Buffer','Pool','Queue','Motion','Stack','Coherence','Capacity',
         'Jab','Quality','Twist','Stillness','Depth','Straight','Output','Genesis']
PATH_NEW = [15] + list(range(12)) + [12,13,14]
PATH_REUSE = [15] + list(range(12)) + [14]
FEATURES = ['hip_left_deg','hip_right_deg','knee_left_deg','knee_right_deg',
            'elbow_left_deg','elbow_right_deg','shoulder_left_deg','shoulder_right_deg']


def finite(x):
    try:
        a = float(x)
        return a if math.isfinite(a) else None
    except (ValueError, TypeError):
        return None


def clamp(x, low, high):
    return min(max(x, low), high)


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def csv_write(path, rows, fields):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def get_json(path, default):
    if not path or not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def put_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)


def pack8(candidate, output, room, inp):
    assert 0 <= candidate < 4 and output in (0,1) and 0 <= room < 16 and inp in (0,1)
    return (candidate << 6) | (output << 5) | (room << 1) | inp


def angle(a, b, c):
    v = (a[0]-b[0], a[1]-b[1]); w = (c[0]-b[0], c[1]-b[1])
    nv = math.hypot(*v); nw = math.hypot(*w)
    if nv < 1e-8 or nw < 1e-8:
        return None
    return math.degrees(math.acos(clamp((v[0]*w[0]+v[1]*w[1])/(nv*nw), -1, 1)))


def pose_features(landmarks, visibility_min=0.35):
    """Input sequence [x,y,visibility] for 33 MediaPipe landmarks.
    2D projected angles, NOT physical robot joint angles or ground truth 3D.
    """
    if len(landmarks) < 33:
        return {}
    idx = {'hip_left_deg':(11,23,25), 'hip_right_deg':(12,24,26),
           'knee_left_deg':(23,25,27), 'knee_right_deg':(24,26,28),
           'elbow_left_deg':(11,13,15), 'elbow_right_deg':(12,14,16),
           'shoulder_left_deg':(13,11,23), 'shoulder_right_deg':(14,12,24)}
    features = {}
    for key, triple in idx.items():
        pts = [landmarks[i] for i in triple]
        if any(len(p) < 3 or finite(p[2]) is None or float(p[2]) < visibility_min for p in pts):
            continue
        coords = [(finite(p[0]), finite(p[1])) for p in pts]
        if any(x is None or y is None for x,y in coords):
            continue
        v = angle(*coords)
        if v is not None:
            features[key] = v
    return features


def extract_urdf(path):
    root = ET.parse(path).getroot()
    info = {}
    for j in root.findall('joint'):
        name = j.get('name'); parent = j.find('parent'); child = j.find('child')
        if not name or parent is None or child is None:
            continue
        origin=j.find('origin'); axis=j.find('axis'); limit=j.find('limit')
        xyz = [0.0,0.0,0.0] if origin is None else [float(a) for a in origin.get('xyz','0 0 0').split()]
        info[name]={'name':name,'type':j.get('type'), 'parent':parent.get('link'),
                    'child':child.get('link'),'origin_xyz':xyz,
                    'axis_xyz':[float(a) for a in axis.get('xyz','1 0 0').split()] if axis is not None else None,
                    'lower':finite(limit.get('lower')) if limit is not None else None,
                    'upper':finite(limit.get('upper')) if limit is not None else None}
    return info


def nearest_reference(library, entry, phase):
    matching = [r for r in library if r.get('chunk_id') == entry]
    if not matching:
        return None
    return min(matching, key=lambda x: abs((finite(x.get('phase')) or 0)-phase))


def mapping_config(path):
    data=get_json(path, {})
    # Mapping is an operator-defined APPROXIMATION, never direct-copy human joint values.
    return data.get('joints', [])


def learning_memory(path):
    return get_json(path, {'chunks':{},'residuals':{}})


def evaluate(row, references, config, memory, feedback=None, urdf=None):
    """One decision. No hand-written Coherence/Quality score thresholds.
    Hard constraints are schema, finite values, joint limits and optional trusted operator flags.
    Empirical adaptation updates only after measured feedback; no unsafe automation.
    """
    start=time.perf_counter()
    eid=str(row.get('event_id') or 'event')
    chunk=str(row.get('chunk_id') or '')
    phase=finite(row.get('phase'))
    observed={k:finite(row.get(k)) for k in FEATURES}
    observed={k:v for k,v in observed.items() if v is not None}
    ref=nearest_reference(references,chunk,phase or 0)
    history=memory['chunks'].setdefault(chunk, {'experiences':0,'uses':0,'errors':[]}) if chunk else None
    reasons=[]; status='PROPOSED'
    if not chunk or phase is None or not (0 <= phase <= 1):
        status='HOLD'; reasons.append('invalid_chunk_or_phase')
    if not observed:
        status='HOLD'; reasons.append('no_visible_pose_features')
    if ref is None:
        status='HOLD'; reasons.append('reference_chunk_absent')
    # Timing is descriptive, not a fixed PASS score.
    expected_entry=finite(row.get('entry_time_ms'))
    now=finite(row.get('timestamp_ms'))
    onset_error=None if now is None or expected_entry is None else now-expected_entry
    reused=bool(history and history['experiences'] >= 3)
    # Simple conservative upper-limb retargeting only when mapping explicitly configured.
    # For legs the prototype records an intent but does not propose executable targets.
    targets=[]
    if status=='PROPOSED':
        for item in config:
            joint=item['joint']; source=item['feature']
            if source not in observed or source not in ref:
                continue
            base=finite(item.get('neutral_rad'))
            scale=finite(item.get('scale_rad_per_deg'))
            ref_val=finite(ref.get(source))
            if None in (base,scale,ref_val):
                continue
            # Reference is the teacher: aim for reference relative to operator-calibrated neutral.
            proposed=base+scale*(ref_val-90.0)
            learned=memory['residuals'].get(joint, {'bias':0.0,'samples':0})
            proposed += learned['bias']
            model=(urdf or {}).get(joint)
            if model is None and urdf is not None:
                status='HOLD'; reasons.append('unrecognized_urdf_joint:'+joint); break
            if model is not None and model['type'] not in ('revolute','continuous','prismatic'):
                status='HOLD'; reasons.append('non_actuated_joint:'+joint); break
            # Do not silently clip: report discrepancy; controller must enforce real limits.
            lo=model['lower'] if model is not None else finite(item.get('min_rad'))
            hi=model['upper'] if model is not None else finite(item.get('max_rad'))
            if lo is None or hi is None:
                status='HOLD'; reasons.append('missing_joint_limits:'+joint); break
            if not (lo <= proposed <= hi):
                status='HOLD'; reasons.append('joint_limit_violation:'+joint); break
            targets.append({'event_id':eid,'joint':joint,'target_rad':round(proposed,6),
                            'mode':'UPPER_BODY_SIMULATION_ONLY'})
    # Passive feedback measurement; NEVER execute targets.
    feedback_error=[]
    if feedback:
        for r in feedback:
            if r.get('event_id')!=eid:
                continue
            a=finite(r.get('target_rad')); b=finite(r.get('actual_rad'))
            if a is None or b is None:
                continue
            feedback_error.append(abs(b-a))
            # Tiny online residual learner, trained on independently measured target-vs-actual.
            # This is a proof of update flow, not learned dynamics or safe RL.
            if status=='PROPOSED' and str(r.get('verified','')).lower() in ('yes','true','1'):
                joint=r.get('joint')
                if any(t['joint']==joint for t in targets):
                    curr=memory['residuals'].setdefault(joint, {'bias':0.0,'samples':0})
                    curr['bias']=clamp(curr['bias'] + 0.1*(a-b), -0.15, 0.15)
                    curr['samples']+=1
        if feedback_error and status=='PROPOSED' and history is not None:
            history['errors'].append(sum(feedback_error)/len(feedback_error))
            history['errors']=history['errors'][-100:]
            # Reuse after three externally verified feedback observations, not only success claims.
            if any(r.get('event_id')==eid and str(r.get('verified','')).lower() in ('yes','true','1') for r in feedback):
                history['experiences']+=1
    if reused and status=='PROPOSED' and history:
        history['uses']+=1
    # Mark proposal NOT a robot execution, and NOT a final physical safety decision.
    path=PATH_REUSE if reused else PATH_NEW
    if status=='HOLD':
        path=[15,0,1]   # input issue, no candidate evaluation
        targets=[]
    logs=[]
    for room in path:
        name=ROOMS[room]
        event={'event_id':eid,'chunk_id':chunk,'room_id':format(room,'X'), 'room':name,
               'register_hex':format(pack8(1 if reused else 0,1 if room==14 and status=='PROPOSED' else 0,room,1),'02X'),
               'stage':'HOLD' if status=='HOLD' else 'VISITED','reason':'|'.join(reasons)}
        logs.append(event)
    ref_errors=[abs(observed[k]-finite(ref[k])) for k in observed if ref and k in ref and finite(ref[k]) is not None]
    result={'event_id':eid,'chunk_id':chunk,'status':status,'reason':'|'.join(reasons) or 'candidate_for_simulation',
            'phase':phase, 'entry_offset_ms':onset_error,'angles_compared':len(ref_errors),
            'mean_pose_error_deg':round(sum(ref_errors)/len(ref_errors),4) if ref_errors else '',
            'mean_feedback_error_rad':round(sum(feedback_error)/len(feedback_error),6) if feedback_error else '',
            'experiences':history['experiences'] if history else 0,'reuse_before':int(reused),
            'rooms_visited':len(logs),'decision_ms':round((time.perf_counter()-start)*1000,5),
            'target_count':len(targets)}
    return result,logs,targets


def process(args):
    obs=read_csv(args.input); ref=read_csv(args.reference)
    feedback=read_csv(args.feedback) if args.feedback else []
    model=extract_urdf(args.urdf) if args.urdf else None
    config=mapping_config(args.mapping)
    memory=learning_memory(args.memory)
    decisions=[]; traces=[]; proposals=[]
    for row in obs:
        d,t,p=evaluate(row,ref,config,memory,feedback,model)
        decisions.append(d); traces+=t; proposals+=p
    os.makedirs(args.out,exist_ok=True)
    csv_write(os.path.join(args.out,'decisions.csv'),decisions,
              ['event_id','chunk_id','status','reason','phase','entry_offset_ms','angles_compared',
               'mean_pose_error_deg','mean_feedback_error_rad','experiences','reuse_before','rooms_visited','decision_ms','target_count'])
    csv_write(os.path.join(args.out,'room_history.csv'),traces,
              ['event_id','chunk_id','room_id','room','register_hex','stage','reason'])
    csv_write(os.path.join(args.out,'PROPOSED_TARGETS_NOT_FOR_HARDWARE.csv'),proposals,
              ['event_id','joint','target_rad','mode'])
    put_json(args.memory,memory)
    for d in decisions:
        print('%s %s %s rooms=%d experience=%d targets=%d' %
              (d['event_id'],d['chunk_id'],d['status'],d['rooms_visited'],d['experiences'],d['target_count']))
    print('Saved: '+os.path.abspath(args.out))


def urdf_export(args):
    models=extract_urdf(args.urdf); out=[]
    for name,j in sorted(models.items()):
        x,y,z=j['origin_xyz']
        out.append({'joint':name,'type':j['type'],'parent':j['parent'],'child':j['child'],
                    'local_x':x,'local_y':y,'local_z':z,'complex_xy':str(complex(x,y)),
                    'abs_xy':math.hypot(x,y),'lower_rad':j['lower'],'upper_rad':j['upper']})
    csv_write(args.out,out,['joint','type','parent','child','local_x','local_y','local_z','complex_xy','abs_xy','lower_rad','upper_rad'])
    print('Exported %d local joint reference transforms to %s' % (len(out),args.out))


def main():
    parser=argparse.ArgumentParser(description='16Rooms v1.1 simulator (NO ACTUATOR OUTPUT)')
    sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('run'); p.add_argument('--input',required=True);p.add_argument('--reference',required=True)
    p.add_argument('--mapping',required=True);p.add_argument('--urdf');p.add_argument('--feedback')
    p.add_argument('--memory',default='output/backrooms.json');p.add_argument('--out',default='output')
    p2=sub.add_parser('urdf');p2.add_argument('--urdf',required=True);p2.add_argument('--out',required=True)
    args=parser.parse_args()
    if args.cmd=='run':process(args)
    else:urdf_export(args)

if __name__=='__main__':
    main()
