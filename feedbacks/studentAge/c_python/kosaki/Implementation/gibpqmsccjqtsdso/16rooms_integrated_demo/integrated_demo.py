#!/usr/bin/env python3
"""Offline music + pose + 16Rooms integration. No robot hardware commands."""
import argparse, csv, json, math, wave
from pathlib import Path
import numpy as np
from gbmc_music import run as run_music
from rooms_v11 import FEATURES, extract_urdf
from pipeline_v13 import pipeline, save_results

def write_csv(path, rows):
    if not rows: return
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def synthetic_data(out, seconds=4.0, sr=11025):
    t=np.arange(int(sr*seconds))/sr
    sound=0.16*np.sin(2*np.pi*220*t)
    for sec in np.arange(0.25,seconds,0.5):
        ix=int(sec*sr)
        sound[ix:ix+100]+=0.65*np.hanning(100)
    sound=np.clip(sound,-1,1)
    wav=out/'demo_synthetic.wav'
    with wave.open(str(wav),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes((sound*32767).astype('<i2').tobytes())
    rows=[]
    for i in range(int(seconds*30)):
        ms=i*1000/30
        phase=(ms%2000)/2000
        r={'event_id':f'pose_{i:04d}','chunk_id':'synthetic_8count','timestamp_ms':round(ms,3),'phase':phase}
        for j,k in enumerate(FEATURES):
            r[k]=round(90+25*math.sin(2*math.pi*phase+j*0.45),3)
        rows.append(r)
    return wav,rows,rows[::5]

def angle(a,b,c):
    if any(x is None for x in (a,b,c)): return None
    u=np.array(a)-np.array(b);v=np.array(c)-np.array(b)
    n=np.linalg.norm(u)*np.linalg.norm(v)
    if n<1e-9:return None
    return round(float(np.degrees(np.arccos(np.clip(np.dot(u,v)/n,-1,1)))),4)

def convert_pose_csv(path):
    """MediaPipe 33 landmark CSV -> eight angle features, missing values stay missing."""
    out=[]
    with open(path,newline='',encoding='utf-8-sig') as f:
        for i,r in enumerate(csv.DictReader(f)):
            def pt(name):
                try:
                    if float(r.get(name+'_visibility',1))<.35:return None
                    return [float(r[name+'_x']),float(r[name+'_y']),float(r[name+'_z'])]
                except (ValueError,KeyError,TypeError):return None
            def a(x,y,z):return angle(pt(x),pt(y),pt(z))
            d={'event_id':f'pose_{i:06d}','chunk_id':'dance_chunk',
               'timestamp_ms':r.get('timestamp_ms','')}
            names={
              'knee_left_deg':('left_hip','left_knee','left_ankle'),
              'knee_right_deg':('right_hip','right_knee','right_ankle'),
              'elbow_left_deg':('left_shoulder','left_elbow','left_wrist'),
              'elbow_right_deg':('right_shoulder','right_elbow','right_wrist'),
              'hip_left_deg':('left_shoulder','left_hip','left_knee'),
              'hip_right_deg':('right_shoulder','right_hip','right_knee'),
              'shoulder_left_deg':('left_elbow','left_shoulder','left_hip'),
              'shoulder_right_deg':('right_elbow','right_shoulder','right_hip')}
            for k,v in names.items():
                val=a(*v)
                d[k]='' if val is None else val
            out.append(d)
    if not out:raise ValueError('Pose CSV has no rows')
    return out

def nearest(rows,t,key='time_s'):
    if not rows:return {}
    return min(rows,key=lambda r:abs(float(r[key])-t))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--wav',type=Path,help='PCM WAV, otherwise generated synthetic audio')
    ap.add_argument('--pose-csv',type=Path,help='extract_pose.py output, otherwise synthetic poses')
    ap.add_argument('--reference-csv',type=Path,help='Optional reference CSV with chunk_id/phase/angle columns')
    ap.add_argument('--out',type=Path,default=Path('output_integrated'))
    ap.add_argument('--bpm',type=float,default=120)
    ap.add_argument('--start-ms',type=float,default=0)
    ap.add_argument('--no-layers',action='store_true')
    a=ap.parse_args()
    if a.bpm<=0:ap.error('--bpm must be positive')
    a.out.mkdir(parents=True,exist_ok=True)
    if a.wav is None or a.pose_csv is None:
        swav,sposes,srefs=synthetic_data(a.out)
    wav=a.wav if a.wav else swav
    poses=convert_pose_csv(a.pose_csv) if a.pose_csv else sposes
    if a.reference_csv:
        with a.reference_csv.open(newline='',encoding='utf-8-sig') as f:
            refs=list(csv.DictReader(f))
    elif a.pose_csv:
        refs=[] # real input must not be silently used as its own teacher
    else:
        refs=srefs
    music_dir=a.out/'music'
    music_summary=run_music(wav,music_dir,analyze_layers=not a.no_layers)
    def load(name):
        p=music_dir/name
        if not p.exists():return []
        with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
    music_events=load('events.csv')
    layer_rows=load('layer_rooms_timeline.csv')
    eight_ms=8*60000/a.bpm
    model=extract_urdf(Path(__file__).parent/'g1_29dof_mode_13.urdf')
    result=pipeline(poses,refs,[],model,start_ms=a.start_ms,eight_ms=eight_ms)
    save_results(result,a.out/'robot',a.out/'robot'/'memory.json')
    combined=[]
    for pose,decision,mental in zip(result['aligned'],result['decisions'],result['mental']):
        t=float(pose['timestamp_ms'])/1000
        m=nearest(music_events,t)
        l=nearest(layer_rows,t)
        combined.append({
          'time_s':round(t,4),'event_id':pose['event_id'],
          'pose_source':'mediapipe_csv' if a.pose_csv else 'SYNTHETIC',
          'music_source':'user_wav' if a.wav else 'SYNTHETIC',
          'chunk_id':pose['chunk_id'],'phase':pose.get('phase',''),
          'music_room':m.get('room_after',''),'music_event':m.get('event',''),
          'drum_room':l.get('drum_room',''),'melody_room':l.get('melody_room',''),
          'robot_decision':decision['status'],'robot_rooms_visited':decision['rooms_visited'],
          'pose_error_deg':decision['mean_pose_error_deg'],
          'next_action':mental['next_action'],'robot_hardware_commands':0})
    write_csv(a.out/'integrated_timeline.csv',combined)
    summary={'audio':music_summary,'pose_rows':len(poses),'integrated_rows':len(combined),
       'reference_rows':len(refs),'robot_proposed':sum(x['status']=='PROPOSED' for x in result['decisions']),
       'robot_hold':sum(x['status']=='HOLD' for x in result['decisions']),
       'hardware_commands':0,'eight_duration_ms':eight_ms,
       'notes':['Offline alignment by nearest timestamp','Music layer analysis uses full-song noncausal HPSS',
       'No automatic calibration of MediaPipe human angles to G1 joints',
       'No robot motor control; predictions are not measured outcomes']}
    (a.out/'integrated_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        def hexint(x):return int(x,16) if x else float('nan')
        ts=[r['time_s'] for r in combined]
        fig,ax=plt.subplots(figsize=(12,4))
        ax.step(ts,[hexint(r['music_room']) for r in combined],where='post',label='music')
        if layer_rows:
            ax.step(ts,[hexint(r['drum_room']) for r in combined],where='post',label='drum',alpha=.75)
            ax.step(ts,[hexint(r['melody_room']) for r in combined],where='post',label='melody',alpha=.75)
        ax.set(xlabel='Time (s)',ylabel='Room (0-F)',title='16Rooms music timelines')
        ax.set_yticks(range(16),[f'{i:X}' for i in range(16)])
        ax.legend();fig.tight_layout();fig.savefig(a.out/'timeline.png',dpi=140);plt.close(fig)
    except ImportError:pass
    print('SUCCESS:',a.out.resolve())
    print('rows:',len(combined),'proposed:',summary['robot_proposed'],'hold:',summary['robot_hold'])
    print('NO ROBOT HARDWARE COMMANDS')
if __name__=='__main__':main()
