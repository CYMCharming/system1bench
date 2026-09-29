from copy import deepcopy
import unittest
from benchmarks.codebook_control import render
from system1bench.llm_adapter import messages
from research.confirmation import build,self_check,oracle,independent_oracle


class ConfirmationTests(unittest.TestCase):
    def test_generator_and_counterfactuals(self):
        f=build();self_check(f)
        self.assertEqual(sum(len(s['cases']) for s in f['suites']),2304)
        for s in f['suites']:
            base=[c for c in s['cases'] if c['condition']=='original']
            self.assertEqual(len({str(c['state']) for c in base}),96)
            for c in s['cases']:
                self.assertEqual(oracle(c['family'],c['state']['facts'],c['state']['parameters']),independent_oracle(c['family'],c['state']['facts'],c['state']['parameters']))

    def test_codebook_orthogonal_and_baseline_identical(self):
        q={'type':'choice','instructions':'Choose','criteria':{'x':'first','y':'second','z':'third'}};state={'value':1}
        import json
        a,base=render(state,q,'baseline');b,repeat=render(state,q,'repeat')
        self.assertEqual(a,messages(state,q));self.assertEqual(a,b);self.assertEqual(base,repeat)
        p,pc=render(state,q,'position_only');c,cc=render(state,q,'code_only');both,bc=render(state,q,'both')
        get=lambda m:json.loads(m[1]['content'])['candidates']
        self.assertEqual(get(p),get(a)[::-1]);self.assertEqual(pc,base)
        self.assertEqual([x['label'] for x in get(c)],[x['label'] for x in get(a)]);self.assertEqual(cc,base[::-1])
        qr=deepcopy(q);qr['criteria']=dict(reversed(list(qr['criteria'].items())))
        self.assertEqual(both,messages(state,qr));self.assertEqual(bc,base[::-1])


if __name__=='__main__':unittest.main()
