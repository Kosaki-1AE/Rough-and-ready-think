import os
import tempfile
import unittest
from rooms_v11 import pose_features, evaluate, learning_memory, read_csv, mapping_config, extract_urdf, pack8

BASE=os.path.join(os.path.dirname(__file__),'sample')

class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.ref=read_csv(os.path.join(BASE,'reference.csv'))
        self.obs=read_csv(os.path.join(BASE,'observations.csv'))
        self.config=mapping_config(os.path.join(BASE,'mapping.json'))
        self.model=extract_urdf(os.path.join(BASE,'mini_robot.urdf'))
        self.feedback=read_csv(os.path.join(BASE,'feedback.csv'))
        self.mem={'chunks':{},'residuals':{}}
    def test_register(self):
        self.assertEqual(pack8(3,1,15,1),255)
    def test_known_unknown(self):
        d,t,p=evaluate(self.obs[0],self.ref,self.config,self.mem,urdf=self.model)
        self.assertEqual(d['status'],'PROPOSED')
        self.assertEqual(len(t),16)
        self.assertEqual(len(p),1)
        d,_,p=evaluate(self.obs[-1],self.ref,self.config,self.mem,urdf=self.model)
        self.assertEqual(d['status'],'HOLD');self.assertEqual(p,[])
    def test_feedback_updates_and_reuse(self):
        r=[]
        for row in self.obs[:4]:
            d,_,_=evaluate(row,self.ref,self.config,self.mem,self.feedback,self.model)
            r.append(d)
        self.assertEqual(r[3]['rooms_visited'],14)
        self.assertEqual(self.mem['chunks']['sixstep']['experiences'],4)
        self.assertGreater(self.mem['residuals']['left_shoulder_joint']['bias'],0)
    def test_hard_limits(self):
        cfg=[dict(self.config[0],neutral_rad=9)]
        d,_,p=evaluate(self.obs[0],self.ref,cfg,self.mem,urdf=self.model)
        self.assertEqual(d['status'],'HOLD');self.assertEqual(p,[])
    def test_missing_landmarks(self):
        self.assertEqual(pose_features([]),{})
    def test_no_actuator_import(self):
        import rooms_v11
        self.assertFalse(hasattr(rooms_v11,'send_motor_command'))

if __name__=='__main__':unittest.main()
