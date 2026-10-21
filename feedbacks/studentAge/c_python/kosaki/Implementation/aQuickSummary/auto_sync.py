#!/usr/bin/env python3
"""Sync playlist metadata, then download previously approved videos."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser(description='Sync YouTube playlists and download approved videos')
p.add_argument('--playlist-name', action='append', default=[], help='Playlist title to include (repeatable); default: all approved playlist videos')
p.add_argument('--include-search', action='store_true', help='Also refresh dance search results')
p.add_argument('--search-limit', type=int, default=100)
p.add_argument('--csv', default='youtube_metadata.csv')
p.add_argument('--directory', default='videos')
a = p.parse_args()
base = Path(__file__).resolve().parent
runner = base / 'run.py'
if not runner.is_file():
    p.error('Put auto_sync.py in the same folder as run.py')
cmd = [sys.executable, str(runner), 'collect', '--mode', 'all' if a.include_search else 'playlist', '--oauth', '--output', a.csv, '--search-limit', str(a.search_limit)]
subprocess.run(cmd, cwd=base, check=True)
source = base / a.csv
with source.open(newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
fields = list(rows[0].keys()) if rows else []
selected = []
for row in rows:
    types = row.get('source_type', '').split('|')
    labels = row.get('source_labels', '').split('|')
    approved = row.get('download_permission', '').strip().lower() in ('yes','true','1')
    if approved and 'my_playlist' in types and (not a.playlist_name or any(x in labels for x in a.playlist_name)):
        selected.append(row)
if not selected:
    print('No approved videos in selected playlists. Review the CSV and mark download_permission=yes only for authorized videos.')
    sys.exit(0)
approved_file = base / 'approved_playlist_downloads.csv'
with approved_file.open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(selected)
print('Downloading', len(selected), 'approved playlist videos; already-downloaded videos will be skipped.', flush=True)
subprocess.run([sys.executable, str(runner), 'download', '--input', str(approved_file), '--directory', a.directory], cwd=base, check=True)
