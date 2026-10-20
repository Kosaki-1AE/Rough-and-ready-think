# -*- coding: utf-8 -*-
"""Capture actual camera/video poses to CSV, then run full v1.3 pipeline.
No camera/MediaPipe requirement for offline tests; optional at runtime.
No robot SDK / actuator path. Video uses video media timestamps where possible.
"""
import argparse
import csv
import os
import time
from rooms_v11 import pose_features, FEATURES, read_csv, mapping_config, extract_urdf, learning_memory
from pipeline_v13 import pipeline, save_results


def capture(source, output, chunk, entry_ms, eight_ms, every_n=2, max_frames=0, preview=False):
    try:
        import cv2
        import mediapipe as mp
    except ImportError as e:
        raise RuntimeError('Requires compatible OpenCV and MediaPipe: '+str(e))
    if not hasattr(mp,'solutions') or not hasattr(mp.solutions,'pose'):
        raise RuntimeError('MediaPipe solutions.pose unavailable; use compatible older build or adapt Tasks API')
    if eight_ms<=0:raise ValueError('eight_ms must be positive')
    camera = str(source).isdigit()
    cap=cv2.VideoCapture(int(source) if camera else source)
    if not cap.isOpened():raise RuntimeError('Cannot open source: '+str(source))
    os.makedirs(os.path.dirname(os.path.abspath(output)),exist_ok=True)
    cols=['event_id','chunk_id','timestamp_ms','entry_time_ms','phase','measured','source']+FEATURES
    t0=time.monotonic(); n=0; accepted=0
    try:
        with open(output,'w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
            with mp.solutions.pose.Pose(static_image_mode=False,model_complexity=1) as pose:
                while cap.isOpened():
                    ok,frame=cap.read()
                    if not ok:break
                    n+=1
                    if max_frames and n>max_frames:break
                    if n%max(1,every_n):continue
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    prediction=pose.process(rgb)
                    landmarks=[(v.x,v.y,v.visibility) for v in prediction.pose_landmarks.landmark] if prediction.pose_landmarks else []
                    features=pose_features(landmarks)
                    media_ts=cap.get(cv2.CAP_PROP_POS_MSEC) if not camera else 0.0
                    timestamp=(time.monotonic()-t0)*1000.0 if camera else media_ts
                    row={'event_id':'frame_%06d'%n,'chunk_id':chunk,'timestamp_ms':round(timestamp,3),
                         'entry_time_ms':entry_ms,'phase':((timestamp-entry_ms)%eight_ms)/eight_ms,
                         'measured':'yes' if features else 'no', 'source':'camera' if camera else 'video'}
                    row.update(features);writer.writerow(row);accepted+=1
                    if preview:
                        cv2.putText(frame,'16Rooms - observational ONLY',(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.65,(255,255,255),2)
                        cv2.imshow('16Rooms no motor commands',frame)
                        if cv2.waitKey(1)&0xFF==ord('q'):break
    finally:
        cap.release()
        if preview:cv2.destroyAllWindows()
    return accepted


def main():
    p=argparse.ArgumentParser(description='MediaPipe video/camera -> full offline mental loop; never moves robots')
    p.add_argument('--source',default='0');p.add_argument('--chunk',required=True)
    p.add_argument('--reference',required=True);p.add_argument('--mapping',required=True)
    p.add_argument('--urdf',required=True)
    p.add_argument('--entry-ms',type=float,default=0);p.add_argument('--eight-ms',type=float,default=4000)
    p.add_argument('--every-n',type=int,default=2);p.add_argument('--max-frames',type=int,default=0)
    p.add_argument('--preview',action='store_true')
    p.add_argument('--out',default='output/live_v13');p.add_argument('--memory',default='output/live_v13_backrooms.json')
    a=p.parse_args();os.makedirs(a.out,exist_ok=True)
    observations=os.path.join(a.out,'camera_observations.csv')
    count=capture(a.source,observations,a.chunk,a.entry_ms,a.eight_ms,a.every_n,a.max_frames,a.preview)
    data=pipeline(read_csv(observations),read_csv(a.reference),mapping_config(a.mapping),
                  extract_urdf(a.urdf),memory=learning_memory(a.memory),start_ms=a.entry_ms,eight_ms=a.eight_ms)
    save_results(data,a.out,a.memory)
    print('Captured observations:',count,'processed events:',len(data['decisions']))
    print('NO ROBOT COMMANDS; no actual physical simulation')

if __name__=='__main__':main()
