import unittest
from research.analyze import paired,risk_curve,cluster_estimate
from research.analyze_confirmation import simultaneous


class ResearchAnalysisTests(unittest.TestCase):
    def row(self,i,p,g,prob=None):
        return dict(id=str(i),qid='q',group=str(i),prediction=p,gold=g,error=None,probabilities=prob or [.3,.7])

    def test_zero_accuracy_change_can_hide_all_flips(self):
        a=[self.row(1,'a','a'),self.row(2,'b','a')];b=[self.row(1,'b','a'),self.row(2,'a','a')]
        r=paired(a,b);self.assertEqual(r['estimate'],0);self.assertEqual(r['disagreement']['estimate'],1)
        self.assertEqual((r['a_only_correct'],r['b_only_correct']),(1,1))

    def test_semantic_label_mapping_and_alignment(self):
        a=[self.row(1,'true','true')];b=[self.row(1,'B','B')]
        with self.assertRaises(ValueError):paired(a,b)
        r=paired(a,b,mapping={'true':'B'});self.assertEqual(r['disagreement']['estimate'],0)

    def test_risk_does_not_break_probability_ties(self):
        rows=[self.row(1,'a','a',[.8,.2]),self.row(2,'b','a',[.8,.2])]
        curve=risk_curve(rows)['curve'];self.assertEqual(len(curve),1);self.assertEqual(curve[0]['coverage'],1)
        self.assertEqual(curve[0]['risk'],.5)

    def test_cluster_not_variant_count(self):
        r=cluster_estimate([0,1,0,1],['a','a','b','b'],draws=100)
        self.assertEqual(r['clusters'],2);self.assertEqual(r['ci95'],[.5,.5])

    def test_simultaneous_degenerate_flag(self):
        r=simultaneous([[0]*6]*6,[101,101,202,202,303,303])
        self.assertTrue(all(x['zero_empirical_variance'] for x in r));self.assertTrue(all(x['simultaneous_ci95']==[0,0] for x in r))


if __name__=='__main__':unittest.main()
