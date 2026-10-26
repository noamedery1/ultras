# -*- coding: utf-8 -*-
"""data_auto.json + curated/*.json + template.html -> ../index.html"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
def load(name, default):
    p = os.path.join(HERE, 'curated', name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default
D = json.load(open(os.path.join(HERE, 'data_auto.json'), encoding='utf-8'))
D.pop('threats', None); D.pop('couples', None)  # only curated threats are published
D['cur'] = dict(proph=load('proph.json', []), flips=load('flips.json', []), threats=load('threats.json', []),
                psych={**load('psych_a.json', {}), **load('psych_b.json', {})},
                roast=load('roast.json', {}), persona=load('persona.json', {}))
js = json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', r'<\/')
# never publish phone numbers: @mentions -> member name, unknown -> מישהו
import re
NAMES = json.load(open(os.path.join(HERE, '..', 'names.json'), encoding='utf-8'))
PH = re.compile(r'\+\d{1,3}[\d\- ()]{8,15}\d')
js = PH.sub(lambda m: NAMES.get(m.group(0), 'מישהו').replace('__DEL__', 'מישהו'), js)
assert not re.search(r'\d{2,3}-\d{3}-\d{4}', js), 'phone number leaked'
html = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read().replace('/*DATA*/null', js)
open(os.path.join(HERE, '..', 'index.html'), 'w', encoding='utf-8').write(html)
print('index.html', round(len(html.encode()) / 1e6, 2), 'MB', {k: len(v) for k, v in D['cur'].items()})
