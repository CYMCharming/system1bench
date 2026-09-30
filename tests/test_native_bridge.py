import unittest
from unittest.mock import patch

from system1bench.native_bridge import ExpandedDecisionAdapter

class FakeEngine:
    metadata={'fake':True}
    limit=32768
    def audit(self,state,questions):
        if state=='overlong':
            raise ValueError('ContextOverflow')
        return {qid:dict(complete=True,prompt_tokens=8,token_sha256='a'*64) for qid in questions}
    def predict(self,state,questions):
        return {'a':{'left':.8,'right':.2},'b':{'false':.3,'true':.7},'c':{'0':.25,'1':.75}}

class TestNativeBridge(unittest.TestCase):
    def make(self):
        with patch('system1bench.native_bridge.DecisionAdapter',return_value=FakeEngine()):
            return ExpandedDecisionAdapter('kev_4b','/fake/checkpoint')
    def test_all_primitives_and_budget(self):
        adapter=self.make()
        q={'a':dict(type='choice',criteria={'left':'L','right':'R'}),'b':dict(type='noul'),'c':dict(type='score',criteria=['low','high'])}
        out=adapter.predict(['ok'],q,'en',dict(max_len=8192),1)[0]['answers']
        self.assertEqual(out['a']['choice'],'left')
        self.assertEqual(out['b']['noul'],.7)
        self.assertAlmostEqual(out['c']['score'],.75)
        self.assertEqual(adapter.engine.limit,8192)
    def test_one_overflow_does_not_poison_batch(self):
        adapter=self.make()
        q={'a':dict(type='choice',criteria={'left':'L','right':'R'})}
        out=adapter.predict(['overlong','ok'],q,'en',dict(max_len=16),2)
        self.assertEqual(out[0]['answers'],{})
        self.assertEqual(out[1]['answers']['a']['choice'],'left')
        self.assertFalse(adapter.audit('overlong',q,dict(max_len=16))['a']['complete'])
    def test_budget_change_invalidates_prompt_cache(self):
        adapter=self.make()
        adapter.engine.cache={'old':'prompt'}
        adapter._budget(dict(max_len=16))
        self.assertEqual(adapter.engine.cache,{})
        with self.assertRaises(ValueError):
            adapter._budget(dict(max_len=0))

if __name__=='__main__':
    unittest.main()
