import unittest
from minimal_core import MinimalCore, experiment

class TestMinimalCore(unittest.TestCase):
    def test_hold_then_commit(self):
        s=MinimalCore(frozenset({'A','B','C'}))
        self.assertEqual(s.observe({'A','B'})['event'],'HOLD')
        self.assertEqual(s.observe({'B','C'})['event'],'COMMIT')
        self.assertEqual(s.committed,'B')
    def test_conflict_keeps_state(self):
        s=MinimalCore(frozenset({'A','B'}))
        s.observe({'A'})
        self.assertEqual(s.observe({'B'})['event'],'CONFLICT')
        self.assertEqual(s.committed,'A')
    def test_empty_conflict(self):
        s=MinimalCore(frozenset({'A','B'}))
        self.assertEqual(s.observe(set())['event'],'CONFLICT')
        self.assertEqual(len(s.candidates),2)
    def test_unknown_rejected(self):
        s=MinimalCore(frozenset({'A','B'}))
        with self.assertRaises(ValueError): s.observe({'X'})
    def test_full_observation_holds(self):
        s=MinimalCore(frozenset({'A','B'}))
        self.assertEqual(s.observe({'A','B'})['event'],'HOLD')
    def test_binary_depth(self):
        self.assertEqual([r['binary_observations_to_commit'] for r in experiment()],list(range(1,9)))

if __name__=='__main__': unittest.main()
