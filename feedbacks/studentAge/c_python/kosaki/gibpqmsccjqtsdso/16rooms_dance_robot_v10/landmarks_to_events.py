# -*- coding: utf-8 -*-
"""Convert MediaPipe long-form landmark CSV + manually annotated 8-count segments
into 16Rooms event CSV. Reference and observed videos must use same angle method.
"""
from __future__ import print_function
import argparse
import csv
import math
from rooms_dance import read_csv,write_csv,number

def angle(a,b,c):
    ux,uy=a[0]-b[0],a[1]-b[1]
    vx,vy=c[0]-b[0],c[1]-b[1]
    den=math.hypot(ux,uy)*math.hypot(vx,vy)
    if den<1e-9:return None
    return math.degrees(math.acos(max(-1.0,min(1.0,(ux*vx+uy*vy)/den))))

def load_frames(path):
    groups={}
    for row in read_csv(path):
        t=number(row.get('time_ms'))
        i=number(row.get('landmark_id'))
        x,y,v=number(row.get('x')),number(row.get('y')),number(row.get('visibility'))
        if None in (t,i,x,y,v):continue
        groups.setdefault(t,{})[int(i)]=(x,y,v)
    return groups

def extract_near(groups,time_ms):
    if not groups:return None
    k=min(groups,key=lambda t:abs(t-time_ms))
    lm=groups[k]
    # Left side: shoulder 11, elbow 13, hip 23, knee 25, ankle 27, foot 31.
    triples={'hip_angle':(11,23,25),'knee_angle':(23,25,27),
             'ankle_angle':(25,27,31),'shoulder_angle':(13,11,23)}
    result={}
    vis=[]
    for name,ids in triples.items():
        if all(i in lm for i in ids):
            result[name]=angle(lm[ids[0]],lm[ids[1]],lm[ids[2]])
            vis.extend(lm[i][2] for i in ids)
    result['visibility']=min(vis) if vis else None
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--reference',required=True,help='teacher landmarks.csv')
    p.add_argument('--observed',required=True,help='learner landmarks.csv')
    p.add_argument('--segments',required=True,help='manually annotated chunk timings CSV')
    p.add_argument('--out',default='dance_events.csv')
    a=p.parse_args()
    ref,obs=load_frames(a.reference),load_frames(a.observed)
    result=[]
    for seg in read_csv(a.segments):
        reftime=number(seg.get('reference_sample_ms'))
        obstime=number(seg.get('observed_sample_ms'))
        rf=extract_near(ref,reftime) if reftime is not None else None
        ob=extract_near(obs,obstime) if obstime is not None else None
        row=dict(seg)
        row['visibility']='' if not ob or ob['visibility'] is None else ob['visibility']
        for name in ['hip_angle','knee_angle','ankle_angle','shoulder_angle']:
            row['ref_'+name]= '' if not rf or rf.get(name) is None else round(rf[name],3)
            row['obs_'+name]= '' if not ob or ob.get(name) is None else round(ob[name],3)
        row['ref_motion_phase']=seg.get('beat_phase','')
        row['obs_motion_phase']=seg.get('observed_beat_phase',seg.get('beat_phase',''))
        result.append(row)
    fields=['event_id','chunk_id','entry_time_ms','observed_time_ms','eight_duration_ms',
            'beat_phase','visibility','ref_hip_angle','obs_hip_angle','ref_knee_angle',
            'obs_knee_angle','ref_ankle_angle','obs_ankle_angle','ref_shoulder_angle',
            'obs_shoulder_angle','ref_motion_phase','obs_motion_phase','teacher_verified']
    write_csv(a.out,result,fields)
    print('Created %d dance event records -> %s' % (len(result),a.out))

if __name__=='__main__': main()
