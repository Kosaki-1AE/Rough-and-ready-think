# -*- coding: utf-8 -*-
"""Offline mono/stereo PCM WAV energy-onset detector. NO false promise of beat tracking.
Find transient onset candidates; operator picks an entry and BPM for final 8-count.
Only Python standard library; does not handle MP3/M4A directly.
"""
import argparse
import wave
import struct
import math
from rooms_v11 import csv_write


def wav_energy_onsets(path, hop_ms=20.0, window_ms=40.0, min_gap_ms=120.0):
    with wave.open(path,'rb') as f:
        rate=f.getframerate(); channels=f.getnchannels(); width=f.getsampwidth()
        if width not in (1,2) or channels not in (1,2):
            raise ValueError('Only 8/16-bit PCM mono/stereo WAV supported; convert audio first')
        raw=f.readframes(f.getnframes())
    if width==1:
        signal=[(x-128)/128.0 for x in raw]
    else:
        count=len(raw)//2
        signal=[v/32768.0 for v in struct.unpack('<%dh'%count,raw)]
    if channels==2:
        signal=[(signal[i]+signal[i+1])*0.5 for i in range(0,len(signal)-1,2)]
    window=max(1,int(rate*window_ms/1000.0)); hop=max(1,int(rate*hop_ms/1000.0))
    energy=[]
    for i in range(0,max(0,len(signal)-window+1),hop):
        a=signal[i:i+window]
        rms=math.sqrt(sum(v*v for v in a)/len(a))
        energy.append((1000.0*i/rate,rms))
    if len(energy)<4:
        return []
    changes=[max(0.0,energy[i][1]-energy[i-1][1]) for i in range(1,len(energy))]
    med=sorted(changes)[len(changes)//2]
    absolute_floor=0.005
    threshold=max(absolute_floor,med*3)
    peaks=[];last=-1e12
    for i in range(1,len(changes)-1):
        t=energy[i+1][0];val=changes[i]
        if val>=threshold and val>=changes[i-1] and val>changes[i+1] and t-last>=min_gap_ms:
            peaks.append({'timestamp_ms':round(t,2), 'energy_rise':round(val,7),
                          'method':'ENERGY_TRANSIENT_CANDIDATE_NOT_BEAT'})
            last=t
    return peaks


def eight_duration_ms(bpm):
    if not math.isfinite(bpm) or bpm<=0:
        raise ValueError('BPM must be positive')
    return 8*60000.0/bpm


def main():
    p=argparse.ArgumentParser(description='WAV onset candidates, not automatic beat transcription')
    p.add_argument('--wav',required=True);p.add_argument('--out',default='output/audio_onsets.csv')
    p.add_argument('--bpm',type=float)
    a=p.parse_args()
    peaks=wav_energy_onsets(a.wav)
    csv_write(a.out,peaks,['timestamp_ms','energy_rise','method'])
    print('Candidates:',len(peaks),'saved:',a.out)
    if a.bpm is not None:
        print('eight_ms for user supplied BPM:',round(eight_duration_ms(a.bpm),2))
    print('Choose --entry-ms based on inspection of musical onset; no beat grid inferred.')

if __name__=='__main__':
    main()
