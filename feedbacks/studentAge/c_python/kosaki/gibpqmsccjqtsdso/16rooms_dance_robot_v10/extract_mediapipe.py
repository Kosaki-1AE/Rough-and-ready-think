# -*- coding: utf-8 -*-
"""Optional video -> 33 landmarks CSV. Requires cv2 + mediapipe (not core deps).
Version-specific legacy mediapipe.solutions.pose API; if unavailable, use MediaPipe Tasks adapter.
"""
from __future__ import print_function
import argparse
import csv
import sys

def main():
    p=argparse.ArgumentParser(description='Extract time-stamped landmarks from permitted dance video')
    p.add_argument('--video',required=True)
    p.add_argument('--out',default='landmarks.csv')
    p.add_argument('--stride',type=int,default=1)
    a=p.parse_args()
    if a.stride < 1:
        p.error('--stride must be >= 1')
    try:
        import cv2
        import mediapipe as mp
    except ImportError:
        sys.exit('This OPTIONAL video extractor needs opencv-python and mediapipe; the core does not.')
    if not hasattr(mp, 'solutions'):
        sys.exit('MediaPipe legacy solutions API unavailable in this installation. Use a Tasks Pose Landmarker adapter.')
    cap=cv2.VideoCapture(a.video)
    if not cap.isOpened():
        sys.exit('Cannot open video: '+a.video)
    fps=cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        sys.exit('FPS unavailable; timestamp calibration required')
    fields=['frame','time_ms','landmark_id','x','y','z','visibility']
    try:
        with open(a.out,'w') as f:
            writer=csv.DictWriter(f,fieldnames=fields)
            writer.writeheader()
            frame=0
            with mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1) as pose:
                while True:
                    ok,img=cap.read()
                    if not ok:
                        break
                    if frame % a.stride == 0:
                        rgb=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
                        result=pose.process(rgb)
                        if result.pose_landmarks:
                            for i,lm in enumerate(result.pose_landmarks.landmark):
                                writer.writerow({'frame':frame,'time_ms':round(frame*1000.0/fps,3),
                                                 'landmark_id':i,'x':lm.x,'y':lm.y,'z':lm.z,
                                                 'visibility':lm.visibility})
                    frame+=1
    finally:
        cap.release()
    print('Extracted %d input frames -> %s' % (frame,a.out))

if __name__=='__main__':
    main()
