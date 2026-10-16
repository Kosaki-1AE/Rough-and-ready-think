# -*- coding: utf-8 -*-
"""v1.3 integrated OFFLINE pipeline. No actuator communication or physics engine.

Reference/observation timestamps are explicitly aligned; no synthetic outcomes
are presented as experience. Stdlib, Python >=3.8.
"""
import argparse
import csv
import math
import os
import json
import copy
from rooms_v11 import (read_csv, csv_write, finite, get_json, put_json,
                       mapping_config, extract_urdf, learning_memory, evaluate, FEATURES)
from mental_loop import replay, simulate, reobserve_requests


def observed_keyframes(rows, chunk):
    """Return recorded reference phases without filling unknown intervals."""
    out = []
    for row in rows:
        if row.get('chunk_id') != chunk:
            continue
        p = finite(row.get('phase'))
        if p is None or not 0 <= p <= 1:
            continue
        f = {k: finite(row.get(k)) for k in FEATURES}
        if any(v is not None for v in f.values()):
            out.append((p, f))
    return sorted(out, key=lambda x: x[0])


def chunk_catalog(references):
    chunks = sorted({r.get('chunk_id', '') for r in references if r.get('chunk_id')})
    result = []
    for ch in chunks:
        frames = observed_keyframes(references, ch)
        if not frames:
            continue
        result.append({'chunk_id': ch, 'start_phase':frames[0][0],
                       'end_phase':frames[-1][0], 'keyframes':len(frames),
                       'start_pose_json':json.dumps(frames[0][1], sort_keys=True),
                       'end_pose_json':json.dumps(frames[-1][1], sort_keys=True),
                       'reference_source':'MEASURED_OR_USER_PROVIDED_REFERENCE'})
    return result


def align_events(rows, start_ms, eight_ms):
    if eight_ms <= 0 or not math.isfinite(eight_ms):
        raise ValueError('eight_ms must be finite and positive')
    out = []
    for n, row in enumerate(rows):
        x = dict(row)
        t = finite(x.get('timestamp_ms'))
        if t is None:
            # Explicitly allow prealigned phase, but never pretend to derive it from time.
            phase = finite(x.get('phase'))
            if phase is None:
                x['_sync_error'] = 'missing_timestamp_and_phase'
            else:
                x['_sync_error'] = 'phase_supplied_not_audio_derived'
        else:
            phase = ((t-start_ms) % eight_ms) / eight_ms
            x['phase'] = round(phase, 9)
            x['_sync_error'] = ''
        x.setdefault('event_id', 'event_%06d' % (n+1))
        x['entry_time_ms'] = start_ms
        x['eight_duration_ms'] = eight_ms
        out.append(x)
    return out


def merge_requests(requests, fresh):
    """Mark a request resolved ONLY for fresh, valid, matching measured evidence."""
    updated=[]
    for req in requests:
        r=dict(req)
        event=r.get('event_id')
        chunk=r.get('chunk_id')
        phase=finite(r.get('phase'))
        applicable=[]
        for obs in fresh:
            if obs.get('chunk_id') != chunk:
                continue
            if obs.get('original_event_id') != event:
                continue
            p=finite(obs.get('phase'))
            if p is None or phase is None or abs(p-phase)>0.03:
                continue
            if str(obs.get('measured','')).lower() not in ('yes','true','1'):
                continue
            if not any(finite(obs.get(k)) is not None for k in FEATURES):
                continue
            applicable.append(obs)
        r['state']='FRESH_EVIDENCE_RECEIVED' if applicable else 'OPEN'
        r['fresh_event_id']=applicable[-1].get('event_id','') if applicable else ''
        updated.append(r)
    return updated


def adaptive_stats(feedback):
    """Descriptive observed error distribution per chunk, no quality cutoffs."""
    by={}
    for r in feedback:
        if str(r.get('verified','')).lower() not in ('true','yes','1'):
            continue
        a,b=finite(r.get('target_rad')),finite(r.get('actual_rad'))
        if a is None or b is None:
            continue
        chunk=r.get('chunk_id') or 'unspecified'
        by.setdefault(chunk, []).append(abs(a-b))
    summaries=[]
    for chunk, errors in sorted(by.items()):
        errors=sorted(errors); n=len(errors)
        summaries.append({'chunk_id':chunk,'verified_samples':n,
                          'mean_abs_error_rad':round(sum(errors)/n,7),
                          'median_abs_error_rad':round(errors[(n-1)//2] if n%2 else (errors[n//2-1]+errors[n//2])/2,7),
                          'min_abs_error_rad':round(errors[0],7),
                          'max_abs_error_rad':round(errors[-1],7)})
    return summaries


def pipeline(observations, references, mapping, model, feedback=None, memory=None,
             start_ms=0.0, eight_ms=4000.0, replay_points=9, response=0.4,
             fresh=None):
    memory = memory if memory is not None else {'chunks':{}, 'residuals':{}}
    feedback = feedback or []
    fresh = fresh or []
    aligned=align_events(observations,start_ms,eight_ms)
    results={'aligned':aligned, 'catalog':chunk_catalog(references),
             'decisions':[], 'room_history':[], 'proposals':[],
             'refrain':[], 'imagined':[], 'requests':[], 'mental':[],
             'experience':[], 'memory':memory}
    for row in aligned:
        # No fake feedback. The learner sees verified feedback only.
        own_feedback=[f for f in feedback if f.get('event_id')==row.get('event_id')]
        decision, trace, proposals=evaluate(row,references,mapping,memory,own_feedback,model)
        results['decisions'].append(decision)
        results['room_history'].extend(trace)
        results['proposals'].extend(proposals)
        ch=str(row.get('chunk_id') or '')
        phase=finite(row.get('phase'))
        if phase is None:
            phase=0.0
        frames, replay_reason=replay(references,ch,phase,replay_points)
        if decision['status']!='PROPOSED':
            reason=decision['reason']; simulated=[]
        elif replay_reason!='ok':
            reason=replay_reason;simulated=[]
        else:
            simulated,reason=simulate(frames,mapping,model,memory,response=response)
        requests=reobserve_requests(ch,phase,reason,references,frames,row)
        # If the data came from a live source but evidence gaps remain, flag for reobservation.
        if not requests and not any(finite(row.get(k)) is not None for k in FEATURES):
            requests=[{'chunk_id':ch,'phase':phase,'reason':'no_pose','request':'REOBSERVE_BODY'}]
        if replay_reason!='ok' and not any(q['reason']==replay_reason for q in requests):
            requests.append({'chunk_id':ch,'phase':phase,'reason':replay_reason,'request':'REOBSERVE_REFERENCE'})
        results['mental'].append({'event_id':row['event_id'],'chunk_id':ch,'phase':phase,
                                  'decision':decision['status'],
                                  'next_action':'REOBSERVE' if requests else ('SIMULATED_NOT_EXECUTED' if reason=='ok' else 'HOLD'),
                                  'reason':reason,'replay_frames':len(frames),'prediction_rows':len(simulated),
                                  'reobserve_requests':len(requests), 'room_visits':len(trace)})
        for f in frames:
            r={'event_id':row['event_id'],'chunk_id':ch,'phase':f['phase'],
               'interpolated':f['interpolated'],'observed':f['observed']}
            r.update(f['features']);results['refrain'].append(r)
        for p in simulated:
            r={'event_id':row['event_id'],'chunk_id':ch}; r.update(p)
            results['imagined'].append(r)
        for r in requests:
            req=dict(r);req['event_id']=row['event_id'];results['requests'].append(req)
        results['experience'].append({'event_id':row['event_id'],'chunk_id':ch,
                                      'verified_feedback_rows':sum(str(f.get('verified','')).lower() in ('yes','true','1') for f in own_feedback),
                                      'imagined_rows_not_training':len(simulated),
                                      'training_rule':'VERIFIED_MEASUREMENTS_ONLY'})
    results['requests']=merge_requests(results['requests'],fresh)
    results['stats']=adaptive_stats(feedback)
    return results


FIELDS={
 'aligned':['event_id','chunk_id','timestamp_ms','entry_time_ms','eight_duration_ms','phase','_sync_error']+FEATURES,
 'catalog':['chunk_id','start_phase','end_phase','keyframes','start_pose_json','end_pose_json','reference_source'],
 'decisions':['event_id','chunk_id','status','reason','phase','entry_offset_ms','angles_compared','mean_pose_error_deg','mean_feedback_error_rad','experiences','reuse_before','rooms_visited','decision_ms','target_count'],
 'room_history':['event_id','chunk_id','room_id','room','register_hex','stage','reason'],
 'proposals':['event_id','joint','target_rad','mode'],
 'refrain':['event_id','chunk_id','phase','interpolated','observed']+FEATURES,
 'imagined':['event_id','chunk_id','phase','joint','target_rad','predicted_rad','predicted_tracking_error_rad','model'],
 'requests':['event_id','chunk_id','phase','reason','request','state','fresh_event_id'],
 'mental':['event_id','chunk_id','phase','decision','next_action','reason','replay_frames','prediction_rows','reobserve_requests','room_visits'],
 'experience':['event_id','chunk_id','verified_feedback_rows','imagined_rows_not_training','training_rule'],
 'stats':['chunk_id','verified_samples','mean_abs_error_rad','median_abs_error_rad','min_abs_error_rad','max_abs_error_rad']}


def save_results(results,out,memory_path):
    os.makedirs(out,exist_ok=True)
    for key,cols in FIELDS.items():
        suffix='_NOT_FOR_HARDWARE' if key in ('proposals','imagined') else ''
        csv_write(os.path.join(out,key+suffix+'.csv'),results[key],cols)
    put_json(memory_path,results['memory'])
    put_json(os.path.join(out,'summary.json'),{
        'events':len(results['decisions']),
        'proposed':sum(r['status']=='PROPOSED' for r in results['decisions']),
        'hold':sum(r['status']=='HOLD' for r in results['decisions']),
        'reobserve_requests':len(results['requests']),
        'unresolved_requests':sum(q['state']=='OPEN' for q in results['requests']),
        'imagined_predictions_NOT_experience':len(results['imagined']),
        'verified_feedback_samples':sum(s['verified_samples'] for s in results['stats']),
        'hardware_commands':0})


def main():
    p=argparse.ArgumentParser(description='16Rooms integrated offline pipeline - NEVER CONTROLS ROBOTS')
    p.add_argument('--input',required=True)
    p.add_argument('--reference',required=True)
    p.add_argument('--mapping',required=True)
    p.add_argument('--urdf',required=True)
    p.add_argument('--feedback')
    p.add_argument('--fresh',help='Measured re-observation events CSV, with original_event_id, measured=yes')
    p.add_argument('--eight-ms',type=float,default=4000)
    p.add_argument('--entry-ms',type=float,default=0)
    p.add_argument('--memory',default='output/v13_backrooms.json')
    p.add_argument('--out',default='output/v13')
    a=p.parse_args()
    x=pipeline(read_csv(a.input),read_csv(a.reference),mapping_config(a.mapping),
               extract_urdf(a.urdf),read_csv(a.feedback) if a.feedback else [],
               learning_memory(a.memory),a.entry_ms,a.eight_ms,
               fresh=read_csv(a.fresh) if a.fresh else [])
    save_results(x,a.out,a.memory)
    print('events=%d proposals=%d requests=%d verified=%d' %
          (len(x['decisions']),len(x['proposals']),len(x['requests']),sum(s['verified_samples'] for s in x['stats'])))
    print('NO ROBOT COMMANDS. Saved: '+os.path.abspath(a.out))

if __name__=='__main__':
    main()
