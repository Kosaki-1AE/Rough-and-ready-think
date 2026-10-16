import os
import tempfile
import unittest
from pipeline_v13 import (align_events,chunk_catalog,merge_requests,adaptive_stats,pipeline,save_results)
from rooms_v11 import read_csv,mapping_config,extract_urdf
from audio_clock import eight_duration_ms,wav_energy_onsets
import wave
import struct

HERE=os.path.dirname(os.path.abspath(__file__))
S=os.path.join(HERE,'sample')

class IntegratedTests(unittest.TestCase):
    def setup_data(self):
        return (read_csv(os.path.join(S,'observations.csv')),
                read_csv(os.path.join(S,'reference.csv')),
                mapping_config(os.path.join(S,'mapping.json')),
                extract_urdf(os.path.join(S,'mini_robot.urdf')),
                read_csv(os.path.join(S,'feedback.csv')))
    def test_phase_alignment(self):
        x=align_events([{'timestamp_ms':'5000','chunk_id':'sixstep'}],1000,4000)
        self.assertEqual(x[0]['phase'],0)
        self.assertEqual(x[0]['eight_duration_ms'],4000)
    def test_invalid_sync(self):
        with self.assertRaises(ValueError):align_events([],0,0)
    def test_chunk_catalog(self):
        _,r,_,_,_=self.setup_data()
        self.assertTrue(any(x['chunk_id']=='sixstep' for x in chunk_catalog(r)))
    def test_pipeline_integrates_and_keeps_predictions_separate(self):
        o,r,m,u,f=self.setup_data()
        x=pipeline(o,r,m,u,feedback=f)
        self.assertEqual(len(x['decisions']),len(o))
        self.assertTrue(x['refrain'])
        self.assertTrue(x['imagined'])
        self.assertTrue(x['requests'])
        self.assertEqual(x['memory']['chunks']['sixstep']['experiences'],4)
        self.assertEqual(sum(s['verified_samples'] for s in x['stats']),4)
        self.assertTrue(all('NOT_PHYSICS' in q['model'] for q in x['imagined']))
        with tempfile.TemporaryDirectory() as tmp:
            save_results(x,tmp,os.path.join(tmp,'backrooms.json'))
            self.assertTrue(os.path.isfile(os.path.join(tmp,'summary.json')))
    def test_no_feedback_no_experience(self):
        o,r,m,u,_=self.setup_data()
        x=pipeline(o,r,m,u)
        self.assertEqual(x['memory']['chunks']['sixstep']['experiences'],0)
    def test_reobservation_requires_measured_matching_event(self):
        q=[{'event_id':'abc','chunk_id':'sixstep','phase':0.2,'request':'REOBSERVE_BODY','reason':'missing:hip_left_deg'}]
        fresh=[{'event_id':'new','original_event_id':'abc','chunk_id':'sixstep','phase':'0.2',
                'hip_left_deg':'110','measured':'yes'}]
        self.assertEqual(merge_requests(q,fresh)[0]['state'],'FRESH_EVIDENCE_RECEIVED')
        self.assertEqual(merge_requests(q,[dict(fresh[0],measured='no')])[0]['state'],'OPEN')
    def test_verified_only(self):
        x=adaptive_stats([{'verified':'no','chunk_id':'sixstep','target_rad':'1','actual_rad':'0'},
                          {'verified':'yes','chunk_id':'sixstep','target_rad':'1','actual_rad':'0.8'}])
        self.assertEqual(x[0]['verified_samples'],1)
    def test_wav_onset(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=os.path.join(tmp,'a.wav')
            samples=[0]*4000+[30000]*4000+[0]*4000
            with wave.open(p,'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
                w.writeframes(struct.pack('<%dh'%len(samples),*samples))
            events=wav_energy_onsets(p)
            self.assertTrue(events)
            self.assertAlmostEqual(eight_duration_ms(120),4000)

if __name__=='__main__':unittest.main()
