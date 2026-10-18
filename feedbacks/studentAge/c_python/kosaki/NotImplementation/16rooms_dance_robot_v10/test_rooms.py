from __future__ import print_function
import csv
import os
import subprocess
import sys
import tempfile
import unittest
import rooms_dance as m

class TestRooms(unittest.TestCase):
    def test_pack(self):
        for n in range(256):
            self.assertEqual(m.pack8(*m.unpack8(n)),n)

    def test_demo(self):
        rows=m.read_csv(os.path.join('sample','dance_events.csv'))
        mem={}
        ans=[m.process_sample(r,mem)[0] for r in rows]
        self.assertEqual([r['status'] for r in ans],['PASS','PASS','PASS','PASS','HOLD','HOLD'])
        self.assertEqual([r['rooms_visited'] for r in ans[:4]],[16,16,16,14])
        self.assertEqual(mem['sixstep_A']['verified_experiences'],4)
        self.assertEqual(mem['sixstep_A']['uses'],1)

    def test_urdf(self):
        class A(object): pass
        a=A(); a.urdf=os.path.join('sample','mini_robot.urdf')
        fd,a.out=tempfile.mkstemp(suffix='.csv');os.close(fd)
        try:
            m.urdf(a)
            rows=m.read_csv(a.out)
            self.assertEqual(len(rows),2)
            self.assertAlmostEqual(float(rows[1]['root_x']),0.1)
            self.assertAlmostEqual(float(rows[1]['root_z']),-0.1)
        finally:
            os.unlink(a.out)

    def test_missing_measurement(self):
        row=dict(m.read_csv(os.path.join('sample','dance_events.csv'))[0])
        row['visibility']=''
        result,_=m.process_sample(row,{})
        self.assertEqual(result['status'],'HOLD')

if __name__=='__main__':
    unittest.main()
