# -*- coding: utf-8 -*-
"""Parse WhatsApp export -> msgs.pkl  [(datetime, name, text)], + system events."""
import re, json, sys, pickle, os
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
CHAT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "raw", "chat.txt")
NAME = json.load(open(os.path.join(HERE, '..', 'names.json'), encoding='utf-8'))
line_re = re.compile(r'^(\d{1,2})\.(\d{1,2})\.(\d{4}), (\d{1,2}):(\d{2}) - (.*)$')
MK = '\u200e\u200f\u202a\u202b\u202c\u2066\u2067\u2068\u2069'
def clean(s): return s.translate({ord(c): None for c in MK}).strip()

msgs, sysev, unknown = [], [], {}
with open(CHAT, encoding='utf-8', errors='replace') as f:
    for raw in f:
        raw = raw.rstrip('\n')
        m = line_re.match(raw)
        if not m:
            if msgs and raw.strip(): msgs[-1][2] += '\n' + clean(raw)
            continue
        d, mo, y, h, mi, rest = m.groups()
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi))
        rest = clean(rest)
        if ': ' in rest:
            who, txt = rest.split(': ', 1)
            if len(who) < 40:
                nm = NAME.get(who, who)
                if nm == who and who.startswith('+'): unknown[who] = unknown.get(who, 0) + 1
                if nm != '__DEL__': msgs.append([dt, nm, txt])  # __DEL__ = left the group, drop entirely
                continue
        sysev.append((dt, rest))
pickle.dump({'msgs': msgs, 'sys': sysev}, open(os.path.join(HERE, 'msgs.pkl'), 'wb'))
print(len(msgs), 'msgs', len(sysev), 'sys', msgs[0][0], '->', msgs[-1][0])
for k, v in sorted(unknown.items(), key=lambda x: -x[1])[:15]: print(' unmapped', k, v)
