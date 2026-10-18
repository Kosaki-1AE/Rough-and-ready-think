#!/usr/bin/env python3
"""Extract MediaPipe Pose 33 landmarks from local videos into per-video CSV files."""
import argparse
import csv
import json
import sys
from pathlib import Path

EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v'}

def extract(video, output_dir, sample_fps, overwrite, model_complexity):
    import cv2
    import mediapipe as mp
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / (video.stem + '_pose.csv')
    if target.exists() and not overwrite:
        print('SKIP:', video.name)
        return 'skipped'
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError('Cannot open video: ' + str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise RuntimeError('Unknown FPS: ' + str(video))
    names = [name.lower() for name in mp.solutions.pose.PoseLandmark.__members__.keys()]
    fields = ['video_id', 'video_file', 'frame_index', 'timestamp_ms', 'detected']
    for name in names:
        fields.extend([name + '_' + k for k in ('x', 'y', 'z', 'visibility')])
    tmp = target.with_suffix('.csv.part')
    processed = 0
    detected = 0
    try:
        with mp.solutions.pose.Pose(static_image_mode=False, model_complexity=model_complexity, enable_segmentation=False, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose, tmp.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            index = 0
            next_sample = 0.0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                timestamp = index / fps
                index += 1
                if sample_fps > 0:
                    if timestamp + 1e-8 < next_sample:
                        continue
                    next_sample += 1.0 / sample_fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                row = {'video_id': video.stem, 'video_file': video.name, 'frame_index': index-1, 'timestamp_ms': round(timestamp*1000, 3), 'detected': int(result.pose_landmarks is not None)}
                if result.pose_landmarks:
                    detected += 1
                    for name, point in zip(names, result.pose_landmarks.landmark):
                        for key in ('x','y','z','visibility'):
                            row[name+'_'+key] = getattr(point, key)
                writer.writerow(row)
                processed += 1
        tmp.replace(target)
    finally:
        cap.release()
    print('OK:', video.name, 'frames:', processed, 'detected:', detected)
    return 'ok'

def main():
    p = argparse.ArgumentParser(description='MediaPipe Pose 33-point CSV extractor (local videos)')
    p.add_argument('--input', default='videos', help='Video directory or one video file')
    p.add_argument('--output', default='pose_csv', help='Output directory')
    p.add_argument('--sample-fps', type=float, default=0, help='0 = every source frame; otherwise approximate samples/second')
    p.add_argument('--model-complexity', type=int, choices=[0,1,2], default=1)
    p.add_argument('--overwrite', action='store_true')
    args = p.parse_args()
    root = Path(args.input)
    if not root.exists():
        p.error('Input not found: ' + str(root))
    videos = [root] if root.is_file() else sorted(x for x in root.rglob('*') if x.is_file() and x.suffix.lower() in EXTENSIONS)
    if not videos:
        p.error('No video files found in ' + str(root))
    try:
        import cv2
        import mediapipe as mp
        if not hasattr(mp, 'solutions'):
            p.error('This script needs MediaPipe Solutions Pose; install mediapipe==0.10.21 in a compatible Python environment (for example Python 3.11).')
    except ImportError as e:
        p.error('Missing dependency: '+str(e)+'; install requirements.txt in Python 3.11')
    errors = 0
    for video in videos:
        try:
            extract(video, Path(args.output), args.sample_fps, args.overwrite, args.model_complexity)
        except Exception as exc:
            errors += 1
            print('ERROR:', video, exc, file=sys.stderr)
    print('Finished:', len(videos), 'videos,', errors, 'errors')
    if errors:
        sys.exit(1)

if __name__ == '__main__':
    main()
