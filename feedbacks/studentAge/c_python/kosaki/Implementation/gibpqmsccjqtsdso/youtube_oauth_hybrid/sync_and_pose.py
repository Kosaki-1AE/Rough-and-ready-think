#!/usr/bin/env python3
"""Run existing approved-video auto_sync.py, then extract pose from local videos."""
import argparse
import subprocess
import sys
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--playlist-name', action='append', default=[])
p.add_argument('--include-search', action='store_true')
p.add_argument('--search-limit', type=int, default=100)
p.add_argument('--directory', default='videos')
p.add_argument('--output', default='pose_csv')
p.add_argument('--sample-fps', type=float, default=0)
p.add_argument('--skip-sync', action='store_true', help='Process already downloaded local videos only')
a = p.parse_args()
base = Path(__file__).resolve().parent
if not a.skip_sync:
    cmd = [sys.executable, str(base/'auto_sync.py'), '--directory', a.directory, '--search-limit', str(a.search_limit)]
    for name in a.playlist_name:
        cmd += ['--playlist-name', name]
    if a.include_search:
        cmd.append('--include-search')
    subprocess.run(cmd, cwd=base, check=True)
subprocess.run([sys.executable, str(base/'extract_pose.py'), '--input', a.directory, '--output', a.output, '--sample-fps', str(a.sample_fps)], cwd=base, check=True)
