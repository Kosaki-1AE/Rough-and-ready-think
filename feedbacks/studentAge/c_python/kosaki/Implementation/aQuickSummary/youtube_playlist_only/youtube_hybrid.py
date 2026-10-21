#!/usr/bin/env python3
"""YouTube research candidate catalog: personal playlists + public dance search.
Requires yt-dlp. Downloads only explicitly approved videos.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

FIELDS = ['video_id','title','url','channel','duration_seconds','upload_date','source_type','source_labels','download_permission','review_status']

def run_ytdlp(args):
    command = [sys.executable, '-m', 'yt_dlp', '--ignore-errors', '--skip-download', '--dump-single-json', '--flat-playlist'] + args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode and not result.stdout.strip():
        raise RuntimeError(result.stderr.strip()[-1500:])
    return json.loads(result.stdout)

def read_lines(path):
    if not path.exists():
        return []
    return [s.strip() for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip() and not s.lstrip().startswith('#')]

def video_id(entry):
    val = str(entry.get('id') or '').strip()
    if len(val) == 11:
        return val
    url = str(entry.get('url') or '')
    if 'watch?v=' in url:
        return url.split('watch?v=',1)[1][:11]
    return None

def add(rows, entry, source, label):
    vid = video_id(entry)
    if not vid:
        return
    row = rows.get(vid)
    if row is None:
        row = {'video_id':vid, 'title':entry.get('title') or '', 'url':'https://www.youtube.com/watch?v='+vid,
               'channel':entry.get('channel') or entry.get('uploader') or '',
               'duration_seconds':entry.get('duration') or '', 'upload_date':entry.get('upload_date') or '',
               'source_type':source,'source_labels':label,'download_permission':'','review_status':'unreviewed'}
        rows[vid] = row
    else:
        types = set(row['source_type'].split('|'))
        labels = set(row['source_labels'].split('|'))
        types.add(source); labels.add(label)
        row['source_type'] = '|'.join(sorted(types))
        row['source_labels'] = '|'.join(sorted(labels))
        for key, value in [('title',entry.get('title')),('channel',entry.get('channel') or entry.get('uploader')),('duration_seconds',entry.get('duration')),('upload_date',entry.get('upload_date'))]:
            if not row[key] and value:
                row[key] = value

def load_csv(path):
    if not path.exists(): return {}
    with path.open(newline='', encoding='utf-8-sig') as f:
        return {r['video_id']:r for r in csv.DictReader(f) if r.get('video_id')}

def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        for row in sorted(rows.values(), key=lambda r:r['video_id']): writer.writerow(row)

def collect(args):
    output = Path(args.output)
    rows = load_csv(output)
    # Keep manual approvals and reviews across refreshes.
    playlists = read_lines(Path(args.playlists)) if args.mode in ('all','playlist') else []
    queries = read_lines(Path(args.queries)) if args.mode in ('all','search') else []
    for url in playlists:
        try:
            data = run_ytdlp(['--playlist-end',str(args.playlist_limit),url] if args.playlist_limit else [url])
            label = data.get('title') or url
            for entry in data.get('entries') or []:
                if isinstance(entry,dict): add(rows,entry,'my_playlist',label)
            print('Playlist:',label)
        except Exception as exc: print('Playlist failed:',url,exc,file=sys.stderr)
    for query in queries:
        try:
            data = run_ytdlp(['ytsearch%d:%s' % (args.search_limit,query)])
            for entry in data.get('entries') or []:
                if isinstance(entry,dict): add(rows,entry,'odottemita_search',query)
            print('Search:',query)
        except Exception as exc: print('Search failed:',query,exc,file=sys.stderr)
    save_csv(output,rows)
    print('Saved',len(rows),'unique candidate videos to',output)

def download(args):
    rows = load_csv(Path(args.input))
    approved = [r for r in rows.values() if r.get('download_permission','').strip().lower() in ('yes','true','1')]
    if not approved:
        print('No approved videos. Set download_permission=yes only after verifying rights/permission.')
        return
    out = Path(args.directory)
    out.mkdir(parents=True, exist_ok=True)
    urls = out/'approved_urls.txt'
    urls.write_text('\n'.join(r['url'] for r in approved)+'\n',encoding='utf-8')
    cmd = [sys.executable,'-m','yt_dlp','--ignore-errors','--no-overwrites',
           '--download-archive',str(out/'archive.txt'),'-f','bv*[height<=480]+ba/b[height<=480]/b',
           '-o',str(out/'%(id)s.%(ext)s'),'-a',str(urls)]
    print('Downloading',len(approved),'approved entries; ensure usage complies with platform terms.')
    subprocess.run(cmd,check=True)

def main():
    p=argparse.ArgumentParser(description='Research video catalog: own playlists + public dance searches')
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('collect')
    c.add_argument('--mode',choices=['all','playlist','search'],default='all')
    c.add_argument('--playlists',default='playlists.txt')
    c.add_argument('--queries',default='queries.txt')
    c.add_argument('--search-limit',type=int,default=100,help='Max search results per query (not guaranteed)')
    c.add_argument('--playlist-limit',type=int,default=0,help='0 means all available')
    c.add_argument('--output',default='youtube_metadata.csv')
    d=sub.add_parser('download')
    d.add_argument('--input',default='youtube_metadata.csv')
    d.add_argument('--directory',default='videos')
    args=p.parse_args()
    try:
        if args.command=='collect': collect(args)
        else: download(args)
    except FileNotFoundError:
        p.error('Missing file or yt-dlp; install with python -m pip install -U yt-dlp')
if __name__=='__main__': main()
