# -*- coding: utf-8 -*-
"""Webcam/video -> MediaPipe 33 landmarks -> 16Rooms simulator.
No robotics SDK, no motor commands. Requires optional opencv-python and mediapipe.
Use MediaPipe versions with mp.solutions.pose (typically 0.10.x).
"""
import argparse
import csv
import time
from rooms_v11 import pose_features, evaluate, get_json, extract_urdf, read_csv, mapping_config, learning_memory, put_json, FEATURES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',required=True)
    parser.add_argument('--mapping',required=True)
    parser.add_argument('--urdf')
    parser.add_argument('--camera',default='0',help='camera index or video path')
    parser.add_argument('--chunk',default='sixstep')
    parser.add_argument('--eight-ms',type=float,default=4000)
    parser.add_argument('--entry-ms',type=float,default=0)
    parser.add_argument('--memory',default='output/live_backrooms.json')
    parser.add_argument('--out',default='output/live_observations.csv')
    parser.add_argument('--every-n',type=int,default=2)
    args=parser.parse_args()
    try:
        import cv2
        import mediapipe as mp
    except ImportError as e:
        raise SystemExit('Install the optional dependencies first: pip install opencv-python mediapipe ('+str(e)+')')
    if not hasattr(mp,'solutions'):
        raise SystemExit('This MediaPipe installation lacks mp.solutions.pose; use compatible mediapipe 0.10.x or update adapter to Tasks.')
    import os
    os.makedirs(os.path.dirname(os.path.abspath(args.out)),exist_ok=True)
    cap=cv2.VideoCapture(int(args.camera) if args.camera.isdigit() else args.camera)
    if not cap.isOpened():
        raise SystemExit('Cannot open video source')
    lib=read_csv(args.reference); mapping=mapping_config(args.mapping)
    model=extract_urdf(args.urdf) if args.urdf else None
    memory=learning_memory(args.memory)
    fields=['event_id','chunk_id','timestamp_ms','entry_time_ms','phase']+FEATURES+['status','decision_ms','target_count']
    t0=time.monotonic(); frames=0
    with open(args.out,'w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        with mp.solutions.pose.Pose(static_image_mode=False,model_complexity=1) as pose:
            while cap.isOpened():
                ok,frame=cap.read()
                if not ok:
                    break
                frames+=1
                if frames%max(1,args.every_n)!=0:
                    continue
                rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                result=pose.process(rgb)
                points=[]
                if result.pose_landmarks:
                    points=[(l.x,l.y,l.visibility) for l in result.pose_landmarks.landmark]
                features=pose_features(points)
                now=(time.monotonic()-t0)*1000
                phase=((now-args.entry_ms)%args.eight_ms)/args.eight_ms
                item={'event_id':'frame_%06d'%frames,'chunk_id':args.chunk,
                      'timestamp_ms':round(now,2),'entry_time_ms':args.entry_ms,'phase':phase}
                item.update(features)
                decision,_,targets=evaluate(item,lib,mapping,memory,urdf=model)
                item.update({'status':decision['status'],'decision_ms':decision['decision_ms'],'target_count':len(targets)})
                writer.writerow(item);f.flush()
                # Display-only. Never send to a robot. The 8-count clock is a placeholder.
                cv2.putText(frame,'%s  phase %.2f  features %d'%(decision['status'],phase,len(features)),
                            (15,35),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)
                cv2.imshow('16Rooms LIVE - NO MOTOR COMMANDS - press q',frame)
                if (cv2.waitKey(1)&0xFF)==ord('q'):
                    break
    cap.release();cv2.destroyAllWindows();put_json(args.memory,memory)
    print('Observations saved:',args.out)

if __name__=='__main__':
    main()
