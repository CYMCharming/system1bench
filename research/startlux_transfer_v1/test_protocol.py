"""Small semantic checks, including scalar native Boolean and exact probability loss."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from research.startlux_transfer_v1.adapter import NativeAdapter
from research.startlux_transfer_v1.analyze import pilot_values
from research.startlux_transfer_v1.freeze import make
from system1bench.common import request
from system1bench.decision_models import validate_distribution

def test_native_scalar_boolean():
    class Model:
        def decide(self,state,questions):
            return {'review':{'type':'noul','noul':.75}},{}
    adapter=NativeAdapter.__new__(NativeAdapter);adapter.name='startlux_4b';adapter.model=Model()
    questions={'review':{'type':'noul','instructions':'Review?','criteria':{'true':'Yes','false':'No'}}}
    result=adapter.predict({},questions)
    assert result=={'review':{'true':.75,'false':.25}}
    assert validate_distribution(questions['review'],result['review'])[0]=='true'

def test_intern_boolean_semantics():
    class Model:
        def predict(self,row): return {'answers':{'review':{'probabilities':{'no':.75,'yes':.25}}}}
    adapter=NativeAdapter.__new__(NativeAdapter);adapter.name='intern_4b';adapter.model=Model()
    assert adapter.predict({}, {'review':{'type':'noul'}})=={'review':{'false':.75,'true':.25}}

def test_proper_probability_loss():
    row={'probabilities':{'a':.5,'b':.5,'c':0},'gold_distribution':{'a':.5,'b':.5,'c':0}}
    values=pilot_values(row)
    assert values=={'excess_brier':0,'expected_brier':.5,'total_variation':0,'impossible_mass':0}
    row['probabilities']={'a':0,'b':0,'c':1}
    assert pilot_values(row)=={'excess_brier':1.5,'expected_brier':2,'total_variation':1,'impossible_mass':1}

def test_payload_whitelist_and_option_reversal():
    case={'state':'visible','questions':{'q':{'type':'choice','criteria':{'x':'X','y':'Y'}}},
          'gold':{'q':{'label':'x'}},'reasoning':'hidden','metadata':{'target_tool':'hidden'}}
    assert set(request(case))=={'state','questions'}
    changed=copy.deepcopy(case)
    changed['questions']['q']['criteria']=dict(reversed(list(case['questions']['q']['criteria'].items())))
    assert case['gold']==changed['gold'] and case['state']==changed['state']
    assert list(changed['questions']['q']['criteria'])==['y','x']

def test_opaque_identity_is_not_reference_identity():
    cases=[make('unit',str(i),str(i),'s','q',{'option_0':'Correct','option_1':'Wrong1','option_2':'Wrong2'},'option_0','all') for i in range(30)]
    assert {c['gold']['decision']['label'] for c in cases}=={'option_0','option_1','option_2'}
    for c in cases:
        assert c['questions']['decision']['criteria'][c['gold']['decision']['label']]=='Correct'

def test_hosted_append_and_rounding_end_to_end():
    from benchmarks import jev_api
    from research.startlux_transfer_v1 import run
    from system1bench.common import digest,sha
    class FakeClient:
        def __init__(self,*args,**kwargs): self.stop=SimpleNamespace(is_set=lambda:False)
        def predict(self,item):
            suite,case=item
            return dict(model='jev-1.13.0',error=None,response={'answers':{'decision':{
                'type':'choice','choice':'option_0','probabilities':{'option_0':.60,'option_1':.39}}}},
                payload_sha256=digest(dict(model='jev-1.13.0',**request(case))),attempts=[],
                payload_complete=True,server_tokenization_verified=False)
    original=run.ROOT
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);here=root/'research/startlux_transfer_v1';here.mkdir(parents=True)
        for rel in ('research/startlux_transfer_v1/run.py','research/startlux_transfer_v1/adapter.py',
                    'system1bench/decision_models.py','research/model_expansion_v2/adapter.py'):
            path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/rel,path)
        (here/'PROTOCOL.md').write_text('test only')
        case=dict(id='test/original',state='visible',questions={'decision':dict(type='choice',instructions='q',
            criteria={'option_0':'A','option_1':'B'})},gold={'decision':{'label':'option_0'}},
            expansion_condition='original',group='test',family='test')
        case['request_sha256']=digest(request(case))
        frozen=root/'data/startlux_transfer_v1/frozen.json';frozen.parent.mkdir(parents=True)
        frozen.write_text(json.dumps({'suites':[{'name':'test','source':'unit','cases':[case]}]}))
        manifest=dict(cohort=['jev'],expected_decisions=1,frozen_sha256=sha(frozen),
            protocol_sha256=sha(here/'PROTOCOL.md'),code_sha256={name:sha(here/name) for name in ('run.py','adapter.py')})
        (here/'manifest.json').write_text(json.dumps(manifest))
        with patch.object(run,'ROOT',root),patch.object(run,'HERE',here),patch.object(jev_api,'Client',FakeClient),\
             patch('sys.argv',['run.py','--model','jev','--credential','unused']):
            run.main()
        meta=json.loads((here/'results/transfer/jev/metadata.json').read_text())
        row=json.loads((here/'results/transfer/jev/raw.jsonl').read_text())
        assert meta['status']=='DONE' and meta['count']==1 and meta['errors']==0
        assert abs(sum(row['probabilities'].values())-1)<1e-12 and row['prediction']=='option_0'
        assert row['hosted_evidence']['reported_probabilities']=={'option_0':.60,'option_1':.39}
        class TiedClient(FakeClient):
            def predict(self,item):
                output=super().predict(item)
                output['response']['answers']['decision'].update(choice='option_1',probabilities={'option_0':.5,'option_1':.5})
                return output
        tie=here/'tie';tie.mkdir()
        for name in ('PROTOCOL.md','run.py','adapter.py','manifest.json'):shutil.copyfile(here/name,tie/name)
        with patch.object(run,'ROOT',root),patch.object(run,'HERE',tie),patch.object(jev_api,'Client',TiedClient),\
             patch('sys.argv',['run.py','--model','jev','--credential','unused']):
            run.main()
        tied=json.loads((tie/'results/transfer/jev/raw.jsonl').read_text())
        assert tied['prediction']=='option_1' and tied['distribution_argmax_prediction']=='option_0' and tied['error'] is None

if __name__=='__main__':
    test_native_scalar_boolean()
    test_intern_boolean_semantics()
    test_proper_probability_loss()
    test_payload_whitelist_and_option_reversal()
    test_opaque_identity_is_not_reference_identity()
    test_hosted_append_and_rounding_end_to_end()
    print('PASS: 6 semantic/integration checks')
