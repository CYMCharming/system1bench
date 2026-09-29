"""Fresh policy-composition controls with executable labels and matched interventions.

No labels come from a language model. Generator seed is a data seed, not a model seed.
"""
from copy import deepcopy
import itertools
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from system1bench.common import digest, request, sha, write  # noqa: E402

RULES = {
'refund': {
'en': 'Apply in order: suspected fraud -> hold; otherwise, elapsed_days <= return_window and damaged -> replace; otherwise, elapsed_days <= return_window -> refund; otherwise -> deny. Escalate if suspected fraud or amount >= review_threshold. Severity is 2 when both urgent and damaged, 1 when exactly one is true, and 0 otherwise. The reference_notes field is irrelevant.',
'zh': '按顺序执行：疑似欺诈则 hold；否则，elapsed_days <= return_window 且物品损坏则 replace；否则，elapsed_days <= return_window 则 refund；否则 deny。疑似欺诈或 amount >= review_threshold 时升级审核。urgent 和 damaged 都为真时严重程度为2；恰有一个为真时为1；均为假时为0。reference_notes 字段与决策无关。'},
'access': {
'en': 'Apply in order: disabled or expired -> deny; otherwise, mfa_required and not mfa_verified -> challenge; otherwise, role in permitted_roles -> allow; otherwise -> deny. Escalate if anomalous and attempts >= review_threshold. Severity is 2 if attempts >= high_threshold, 1 if attempts >= low_threshold but below high_threshold, otherwise 0. The reference_notes field is irrelevant.',
'zh': '按顺序执行：disabled 或 expired 为真则 deny；否则，要求多因素认证且尚未通过，即 mfa_required 为真且 mfa_verified 为假，则 challenge；否则，role 属于 permitted_roles 则 allow；否则 deny。anomalous 为真且 attempts >= review_threshold 时升级审核。attempts >= high_threshold 时严重程度为2；否则 attempts >= low_threshold 时为1；否则为0。reference_notes 字段与决策无关。'},
'routing': {
'en': 'Apply in order: outage and paying -> urgent_support; otherwise category=billing -> billing; otherwise category=technical -> technical; otherwise -> general. Escalate if outage or (vip and age_hours >= review_threshold). Severity is 2 if age_hours >= high_threshold, 1 if age_hours >= low_threshold but below high_threshold, otherwise 0. The reference_notes field is irrelevant.',
'zh': '按顺序执行：outage 和 paying 都为真则 urgent_support；否则 category=billing 则 billing；否则 category=technical 则 technical；否则 general。outage 为真，或 vip 为真且 age_hours >= review_threshold 时升级审核。age_hours >= high_threshold 时严重程度为2；否则 age_hours >= low_threshold 时为1；否则为0。reference_notes 字段与决策无关。'}
}
OPTIONS = {'refund': {'hold':'Hold for fraud investigation','replace':'Send a replacement','refund':'Return the payment','deny':'Deny the request'},
'access': {'deny':'Deny access','challenge':'Require multi-factor verification','allow':'Allow access'},
'routing': {'urgent_support':'Urgent support team','billing':'Billing team','technical':'Technical team','general':'General assistance'}}
ZH_OPTIONS = {'refund':['暂缓并调查欺诈','发送替换品','退还付款','拒绝请求'], 'access':['拒绝访问','要求多因素验证','允许访问'], 'routing':['紧急支持团队','账单团队','技术团队','一般帮助']}
VARIANTS = ['original','repeat','reversed','chinese','distractor','paraphrase','choice_encoded','counterfactual']


def oracle(family, f, p):
    if family=='refund':
        action='hold' if f['suspected_fraud'] else 'replace' if f['elapsed_days']<=p['return_window'] and f['damaged'] else 'refund' if f['elapsed_days']<=p['return_window'] else 'deny'
        review=f['suspected_fraud'] or f['amount']>=p['review_threshold']
        severity=int(f['urgent'])+int(f['damaged'])
    elif family=='access':
        action='deny' if f['disabled'] or f['expired'] else 'challenge' if f['mfa_required'] and not f['mfa_verified'] else 'allow' if f['role'] in p['permitted_roles'] else 'deny'
        review=f['anomalous'] and f['attempts']>=p['review_threshold']
        severity=2 if f['attempts']>=p['high_threshold'] else 1 if f['attempts']>=p['low_threshold'] else 0
    else:
        action='urgent_support' if f['outage'] and f['paying'] else 'billing' if f['category']=='billing' else 'technical' if f['category']=='technical' else 'general'
        review=f['outage'] or (f['vip'] and f['age_hours']>=p['review_threshold'])
        severity=2 if f['age_hours']>=p['high_threshold'] else 1 if f['age_hours']>=p['low_threshold'] else 0
    return {'action':action,'review':str(bool(review)).lower(),'severity':str(severity)}


def independent_oracle(family, f, p):
    """Separate declarative truth-table implementation used to verify every label."""
    if family=='refund':
        conditions=[(f['suspected_fraud'],'hold'), (f['elapsed_days']<=p['return_window'] and f['damaged'],'replace'), (f['elapsed_days']<=p['return_window'],'refund'), (True,'deny')]
        review=any([f['suspected_fraud'],f['amount']>=p['review_threshold']]); score=sum([f['urgent'],f['damaged']])
    elif family=='access':
        conditions=[(any([f['disabled'],f['expired']]),'deny'),(f['mfa_required'] and f['mfa_verified']==False,'challenge'),(f['role'] in set(p['permitted_roles']),'allow'),(True,'deny')]
        review=all([f['anomalous'],f['attempts']>=p['review_threshold']]); score=sum(f['attempts']>=t for t in [p['low_threshold'],p['high_threshold']])
    else:
        conditions=[(all([f['outage'],f['paying']]),'urgent_support'),(f['category']=='billing','billing'),(f['category']=='technical','technical'),(True,'general')]
        review=any([f['outage'],all([f['vip'],f['age_hours']>=p['review_threshold']])]);score=sum(f['age_hours']>=t for t in [p['low_threshold'],p['high_threshold']])
    return {'action':next(v for yes,v in conditions if yes),'review':str(bool(review)).lower(),'severity':str(int(score))}


def draw(family,rng):
    b=lambda: bool(rng.getrandbits(1))
    if family=='refund':
        p={'return_window':rng.choice([7,14,21,30]),'review_threshold':rng.choice([100,250,500])}
        f={'suspected_fraud':b(),'elapsed_days':p['return_window']+rng.choice([-1,0,1]),'damaged':b(),'amount':p['review_threshold']+rng.choice([-1,0,1]),'urgent':b()}
    else:
        low=rng.choice([2,4,6]);high=low+rng.choice([3,5,7]);p={'review_threshold':rng.choice([3,5,9]),'low_threshold':low,'high_threshold':high}
        v=rng.choice([low-1,low,low+1,high-1,high,high+1])
        if family=='access':
            p['permitted_roles']=rng.sample(['staff','admin','auditor'],rng.choice([1,2]));f={'disabled':b(),'expired':b(),'mfa_required':b(),'mfa_verified':b(),'role':rng.choice(['staff','admin','auditor','guest']),'anomalous':b(),'attempts':v}
        else:
            f={'outage':b(),'paying':b(),'category':rng.choice(['billing','technical','other']),'vip':b(),'age_hours':v}
    return f,p


def changed_fact(family,f,p):
    base=oracle(family,f,p)['action']
    for key,value in f.items():
        candidates=[not value] if isinstance(value,bool) else (['billing','technical','other'] if key=='category' else ['staff','admin','auditor','guest'] if key=='role' else [0,100])
        for v in candidates:
            z=deepcopy(f);z[key]=v
            if oracle(family,z,p)['action'] != base:return z,key
    return None,None


def questions(family, zh=False):
    criteria=deepcopy(OPTIONS[family])
    if zh:criteria=dict(zip(criteria,ZH_OPTIONS[family]))
    return {'action':{'type':'choice','instructions':'根据 state.policy、state.parameters 和 state.facts，应该采取哪个行动？' if zh else 'Using state.policy, state.parameters and state.facts, which action is required?','criteria':criteria},
            'review':{'type':'noul','instructions':'按照 state.policy 的升级规则，是否需要升级审核？' if zh else 'Is escalation required by the escalation rule in state.policy?'},
            'severity':{'type':'score','instructions':'按照 state.policy 的严重程度规则，给出严重程度等级。' if zh else 'Apply the severity rule in state.policy to select the severity level.','criteria':['等级0','等级1','等级2'] if zh else ['Level 0','Level 1','Level 2']}}


def build():
    suites=[]
    for family in RULES:
        cases=[]
        seen=set()
        for seed in [101,202,303]:
            rng=random.Random(seed+sum(map(ord,family)))
            for i in range(32):
                for _ in range(1000):
                    facts,params=draw(family,rng); cf,changed=changed_fact(family,facts,params)
                    fingerprint=digest({'facts':facts,'parameters':params})
                    target=list(OPTIONS[family])[i % len(OPTIONS[family])]
                    if cf is not None and fingerprint not in seen and oracle(family,facts,params)['action']==target:
                        seen.add(fingerprint)
                        break
                else:raise ValueError('No decisive single-field intervention')
                group=f'{family}:{seed}:{i:03d}'
                for variant in VARIANTS:
                    f=deepcopy(cf if variant=='counterfactual' else facts)
                    q=questions(family,variant=='chinese')
                    state={'policy':RULES[family]['zh' if variant=='chinese' else 'en'],'parameters':deepcopy(params),'facts':f}
                    if variant=='reversed':q['action']['criteria']=dict(reversed(list(q['action']['criteria'].items())))
                    if variant=='distractor':state['reference_notes']=[{'archived_record':j,'comment':'This old record is not the current request.','amount':9999,'urgent':True,'disabled':True} for j in range(12)]
                    if variant=='paraphrase':
                        q['action']['instructions']='Determine the action for the current facts by following the supplied policy in its stated priority order.'
                        q['review']['instructions']='Do the current facts meet the supplied rule for escalation?'
                        q['severity']['instructions']='Which severity level follows from the supplied rule and current facts?'
                    if variant=='choice_encoded':
                        q['review']={'type':'choice','instructions':q['review']['instructions'],'criteria':{'false':'No, escalation is not required','true':'Yes, escalation is required'}}
                        q['severity']={'type':'choice','instructions':q['severity']['instructions'],'criteria':{'0':'Level 0','1':'Level 1','2':'Level 2'}}
                    truth=oracle(family,f,params);assert truth==independent_oracle(family,f,params)
                    c={'id':group+':'+variant,'state':state,'questions':q,'gold':{k:{'label':v} for k,v in truth.items()},'group':group,'family':family,'language':'zh' if variant=='chinese' else 'en','condition':variant,'generator_seed':seed,'changed_field':changed if variant=='counterfactual' else None}
                    c['request_sha256']=digest(request(c));cases.append(c)
        suites.append({'name':'policy_'+family,'track':'programmatic_policy_confirmation','reference':'programmatic','source':'system1bench_policy_v1','cases':cases})
    return {'protocol':'system1bench-policy-v1','budget':{'max_len':8192,'head_max_len':4096},'generator_seeds':[101,202,303],'variants':VARIANTS,'suites':suites}


def self_check(frozen):
    for s in frozen['suites']:
        groups={}
        for c in s['cases']:groups.setdefault(c['group'],{})[c['condition']]=c
        for variants in groups.values():
            base=variants['original']
            assert base['request_sha256']==variants['repeat']['request_sha256']
            for name,c in variants.items():
                if name!='counterfactual':assert c['gold']==base['gold']
            cf=variants['counterfactual'];assert cf['gold']['action']!=base['gold']['action']
            assert sum(cf['state']['facts'][k]!=v for k,v in base['state']['facts'].items())==1
    # Exhaustive priority interactions for representative threshold parameters.
    p={'return_window':14,'review_threshold':100}
    for a,b,c,d,e in itertools.product([False,True],[13,14,15],[False,True],[99,100,101],[False,True]):
        f=dict(suspected_fraud=a,elapsed_days=b,damaged=c,amount=d,urgent=e);assert oracle('refund',f,p)==independent_oracle('refund',f,p)


if __name__=='__main__':
    out=ROOT/'research/confirmation_v1';out.mkdir(parents=True,exist_ok=True)
    f=build();self_check(f)
    if (out/'frozen.json').exists():
        import json
        if json.loads((out/'frozen.json').read_text())!=f:raise ValueError('Refusing to replace different frozen cases')
    write(out/'frozen.json',f)
    write(out/'manifest.json',{'protocol':f['protocol'],'generator_sha256':sha(__file__),'frozen_sha256':sha(out/'frozen.json'),'requests':sum(len(s['cases']) for s in f['suites']),'decisions':sum(len(c['questions']) for s in f['suites'] for c in s['cases']),'independent_base_states':288,'seeds':[101,202,303],'variants':VARIANTS,'oracle':'executable policy; no model-generated labels','design_scope':'fresh programmatic compositional policy transfer, not real-world business validity'})
    print('Frozen 288 base states x 8 interventions; 2304 requests / 6912 decisions')
