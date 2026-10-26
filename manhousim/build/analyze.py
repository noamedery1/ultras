# -*- coding: utf-8 -*-
"""msgs.pkl -> data_auto.json (search index, funny pool, FIFA, matches, leaves)
              + *_cands.txt dumps for hand curation (prophecies, chameleon, psych)."""
import re, json, os, pickle, math, statistics
from collections import Counter, defaultdict
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
D = pickle.load(open(os.path.join(HERE, 'msgs.pkl'), 'rb'))
MS, SYS = D['msgs'], D['sys']
NAMES = json.load(open(os.path.join(HERE, '..', 'names.json'), encoding='utf-8'))
END = MS[-1][0]
YEAR0 = END - timedelta(days=365)

# ---------- text helpers ----------
MED = ('<המדיה', 'הושמט', 'נמחקה', '<ההודעה', 'ההודעה נמחקה', 'null', '<נערכה')
def is_media(t): return any(m in t for m in MED[:3]) or t.startswith('‏<')
LAUGH = re.compile(r'(חח+|הה+ה|כככ+|😂|🤣|😭|😆|💀|😅)')
def is_laugh(t):
    t = t.strip()
    if len(t) <= 16 and LAUGH.search(t): return True
    l = re.sub(r'[^\wא-ת]', '', t)
    return bool(re.fullmatch(r'[חהכ]+', l)) and len(l) >= 3
CURSE = re.compile(r'(שרמוט|זונה|מניאק|מפגר|כוסאמ|כוס אמ|מטומטם|תזדיין|מזיין|יזיין|חרא|זבל|טמבל|דביל|בהמה|מעפן|סתום|אידיוט|אהבל|קוקסינל)')
# content rule: no politics, no racism (search vocab + any displayed text)
BLOCK = re.compile(r'(ביבי|נתניהו|בחירות|חמאס|חטופ|ממשל|ליכוד|גביר|סמוטריץ|לפיד|גנץ|בנט|שמאלנ|ערבי|ערבים|ערביה|כושי|כושים|מחבל|טרור|עזה|חיזבאללה|מלחמה|נאצ|היטלר|מוות ל|קואליצ|כנסת|הפגנ|דרוז|אחמד|טיבי|מוסלמ|יהודים|עבודה ערבית)')
def blocked(t): return bool(BLOCK.search(t))
def readable(t):
    if not t or is_media(t) or 'http' in t or is_laugh(t): return False
    return len(re.findall(r'[א-ת]', t)) >= 8 and len(t) <= 260
TOK = re.compile(r'[א-ת]{2,}|[a-zA-Z]{3,}')
STOP = set("של את זה לא אני אתה הוא היא אנחנו הם על עם גם כי אם מה מי יש אין כל רק אבל או כמו יותר פחות הכי כבר עוד זאת הזה שזה שלא שיש טוב ממש שם פה לו לי לך להם אותו אותה וגם אז ולא הכל בכל כן לפני אחרי בין עד מאוד נראה צריך אומר יהיה היה הייתי אפשר בגלל כאילו איזה איך למה כאן שלנו שלו שלהם עכשיו קצת הרבה משהו מישהו כאלה ככה שהוא שהיא שאני באמת וזה תמיד אולי שלך אתם הזאת הזו אצל בו זו יא רוצה עושה יכול זה".split())

pidx = {}
PEOPLE = []
for m in MS:
    if m[1].startswith('+'): continue
    if m[1] not in pidx: pidx[m[1]] = len(PEOPLE); PEOPLE.append(m[1])
def pid(n): return pidx.get(n, -1)

# ---------- funny score (laughs from others right after) ----------
N = len(MS)
score = [0] * N
for i in range(N):
    dt, who, t = MS[i]
    if not readable(t): continue
    laughers = set()
    for j in range(i + 1, min(i + 7, N)):
        if (MS[j][0] - dt).seconds > 300 and MS[j][0] - dt > timedelta(0): break
        if MS[j][1] != who and is_laugh(MS[j][2]): laughers.add(MS[j][1])
    score[i] = len(laughers)

def bin_of(dt): return (dt.year - 2021) * 2 + (0 if dt.month <= 6 else 1)
NB = bin_of(END) + 1
BIN_LABELS = [f"{'א' if b % 2 == 0 else 'ב'}׳ {2021 + b // 2}" for b in range(NB)]

# ---------- funny pool ----------
pool_ids = [i for i in range(N) if score[i] >= 1 and not MS[i][1].startswith('+') and not blocked(MS[i][2])]
pool_ids.sort(key=lambda i: -score[i])
pool_ids = sorted(pool_ids[:9000])
pool = [[MS[i][0].strftime('%d.%m.%y'), pid(MS[i][1]), MS[i][2][:220], score[i]] for i in pool_ids]

# ---------- search index ----------
tot = Counter(); per = defaultdict(Counter); bins = defaultdict(Counter); first = {}
for i, (dt, who, t) in enumerate(MS):
    if is_media(t) or 'http' in t: continue
    p = pid(who)
    for w in set(x.lower() for x in TOK.findall(t)):
        if w in STOP: continue
        tot[w] += 1
        if p >= 0: per[w][p] += 1
        bins[w][bin_of(dt)] += 1
        if w not in first and p >= 0: first[w] = i
vocab = [w for w, c in tot.items() if c >= 30 and not BLOCK.search(w)]
index = {}
for w in vocab:
    f = first.get(w)
    ft = None
    if f is not None:
        txt = MS[f][2]
        ft = [MS[f][0].strftime('%d.%m.%y'), pid(MS[f][1]), '' if tot[w] < 80 or blocked(txt) or not readable(txt) else txt[:100]]
    bl = [bins[w].get(b, 0) for b in range(NB)]
    index[w] = [tot[w], [x for p, c in per[w].most_common(6) for x in (p, c)], bl, ft]

# ---------- year window stats (FIFA / psych / matches) ----------
Y = [(i, m) for i, m in enumerate(MS) if m[0] >= YEAR0 and not m[1].startswith('+')]
cnt = Counter(m[1] for _, m in Y)
ACTIVE = [n for n, c in cnt.most_common() if c >= 250]
st = {n: dict(msgs=cnt[n], night=0, curse=0, laugh_made=0, media=0, chars=0, txt=0, q=0, laugh_give=0,
              hours=Counter(), lat=[]) for n in ACTIVE}
for i, (dt, who, t) in Y:
    if who not in st: continue
    s = st[who]
    if dt.hour < 6: s['night'] += 1
    s['hours'][dt.hour] += 1
    if is_media(t) or 'http' in t: s['media'] += 1
    elif is_laugh(t): s['laugh_give'] += 1
    else:
        s['txt'] += 1; s['chars'] += len(t)
        if CURSE.search(t): s['curse'] += 1
        if '?' in t: s['q'] += 1
    s['laugh_made'] += score[i]
    if i and MS[i - 1][1] != who:
        gap = (dt - MS[i - 1][0]).total_seconds()
        if 0 <= gap <= 1800: s['lat'].append(gap)

def pct_rank(vals):
    order = sorted(vals.items(), key=lambda x: x[1]); n = len(order)
    return {k: i / max(1, n - 1) for i, (k, _) in enumerate(order)}
raw = {
    'pac': {n: -statistics.mean(s['lat']) if s['lat'] else -999 for n, s in st.items()},
    'sho': {n: s['laugh_made'] / s['msgs'] for n, s in st.items()},
    'pas': {n: s['media'] / s['msgs'] for n, s in st.items()},
    'sta': {n: s['night'] / s['msgs'] for n, s in st.items()},
    'phy': {n: s['curse'] / max(1, s['txt']) for n, s in st.items()},
    'vis': {n: s['chars'] / max(1, s['txt']) for n, s in st.items()},
}
vol = pct_rank({n: s['msgs'] for n, s in st.items()})
P = {k: pct_rank(v) for k, v in raw.items()}
POS = {'pac': 'כנף מהיר', 'sho': 'חלוץ מטרה', 'pas': 'קשר פורוורדים', 'sta': 'שוער לילה', 'phy': 'בלם קצב', 'vis': 'פליימייקר חופר'}
fifa = []
for n in ACTIVE:
    s = st[n]
    stats = {k: round(45 + 54 * P[k][n]) for k in raw}
    ovr = round(48 + 20 * vol[n] + 0.5 * (sum(sorted(stats.values())[-3:]) / 3 - 45))
    top = max(stats, key=stats.get)
    fifa.append(dict(name=n, ovr=ovr, pos=POS[top], stats=stats, msgs=s['msgs'],
                     real=dict(lat=round(statistics.mean(s['lat'])) if s['lat'] else None,
                               laugh=round(100 * raw['sho'][n], 1), media=round(100 * raw['pas'][n]),
                               night=round(100 * raw['sta'][n]), curse=round(100 * raw['phy'][n], 1),
                               chars=round(raw['vis'][n]), peak=s['hours'].most_common(1)[0][0])))
fifa.sort(key=lambda x: -x['ovr'])

# ---------- matches (reply graph) ----------
ARGUE = re.compile(r'(לא נכון|שטויות|מה אתה מדבר|תשתוק|אתה לא מבין|בולשיט|די כבר|קשקוש|חרטא|מפגר|דביל|סתום|אידיוט|מה אתה רוצה|תפסיק|על מה אתה|אתה הזוי|הזוי|אין לך מושג|לא מבין כלום)')
def reply_pairs(lo, hi):
    rep = Counter(); arg = Counter(); laughs = Counter()
    for i in range(1, N):
        dt, who, t = MS[i]
        if dt < lo or dt >= hi: continue
        a, b = MS[i - 1][1], who
        if a == b or a.startswith('+') or b.startswith('+'): continue
        if (dt - MS[i - 1][0]).total_seconds() > 180: continue
        rep[(b, a)] += 1                      # b replied to a
        if ARGUE.search(t): arg[(b, a)] += 1
        if is_laugh(t): laughs[(b, a)] += 1  # b laughed at a
    return rep, arg, laughs
rep, arg, lau = reply_pairs(YEAR0, END + timedelta(1))
old_rep, _, _ = reply_pairs(END - timedelta(days=365 * 3), YEAR0)
old_cnt = Counter(m[1] for m in MS if END - timedelta(days=365 * 3) <= m[0] < YEAR0)
def norm(r, c, a, b): return (r[(a, b)] + r[(b, a)]) / math.sqrt(max(1, c[a]) * max(1, c[b]))
matches = {}
for a in ACTIVE:
    others = [b for b in ACTIVE if b != a]
    partners = sorted(others, key=lambda b: -norm(rep, cnt, a, b))
    p = partners[0]
    exs = [(norm(old_rep, old_cnt, a, b) - norm(rep, cnt, a, b), b) for b in others if old_cnt[b] > 300 and old_cnt[a] > 300]
    ex = max(exs) if exs else None
    nem = max((b for b in others if b != p), key=lambda b: arg[(a, b)] + arg[(b, a)])  # partner excluded: chattiest pair always argues most
    # unrequited: a replies to b far more than b to a
    unreq = max(others, key=lambda b: rep[(a, b)] / max(1, rep[(b, a)]) if rep[(a, b)] >= 30 else -1)
    fan = max((b for b in others if b != p), key=lambda b: lau[(b, a)])   # who laughs at a's msgs most (not the partner)
    matches[a] = dict(
        partner=[p, rep[(a, p)], rep[(p, a)]],
        top5=[[b, rep[(a, b)] + rep[(b, a)]] for b in partners[:5]],
        ex=[ex[1], round(norm(old_rep, old_cnt, a, ex[1]) * 1000), round(norm(rep, cnt, a, ex[1]) * 1000)] if ex and ex[0] > 0.004 else None,
        nemesis=[nem, arg[(a, nem)], arg[(nem, a)]],
        unreq=[unreq, rep[(a, unreq)], rep[(unreq, a)]] if rep[(a, unreq)] >= 30 and rep[(a, unreq)] > 1.3 * max(1, rep[(unreq, a)]) else None,
        fan=[fan, lau[(fan, a)]],
    )
couples = sorted({tuple(sorted((a, b))) for a in ACTIVE for b in ACTIVE if a < b},
                 key=lambda ab: -norm(rep, cnt, *ab))[:12]
couples = [[a, b, rep[(a, b)] + rep[(b, a)]] for a, b in couples]

# ---------- leaves ----------
SYSN = {'Niv': 'ניב שחר', 'Yoni Saadon': 'יוני סעדון', 'Yosef-pal19 מתנות בעיצוב אישי': 'יוסף', 'בוקובזה': 'בוקבוזה'}
kicks = []
for dt, t in SYS:
    m = re.match(r'^[~  ]*(.+?) הסיר/ה את (.+)$', t)
    if m:
        by, whom = m.groups()
        by = SYSN.get(by.strip(), NAMES.get(by.strip(), by.strip()))
        whom = NAMES.get(whom.strip(), 'לא מזוהה ' + whom.strip()[-4:])
        if whom != '__DEL__': kicks.append([dt.strftime('%d.%m.%y'), by, whom])
THREAT = re.compile(r'(יוצא מהקבוצה|יוצא מהקבוצה הזאת|עוזב את הקבוצה|אני עוזב|יוצא מפה|תוציאו אותי|עזבתי את הקבוצה|תעיפו אותי|תוציא אותי|משתיק את הקבוצה|השתקתי את הקבוצה|גמרתי עם ביתר|נשבע לא הולך|לא הולך יותר למשחק|מוכר את המנוי|לא מחדש מנוי|לא מחדש את המנוי|אני פורש|פורש מביתר|פורש מהקבוצה|אני לא אוהד|לא אוהד יותר|מבטל את המנוי|אחרון שאני הולך|פעם אחרונה שאני|נמאס לי מהקבוצה|נמאס לי מביתר)')
threats = []
for i, (dt, who, t) in enumerate(MS):
    if who.startswith('+') or not THREAT.search(t) or blocked(t) or len(t) > 220: continue
    back = None
    for j in range(i + 1, min(i + 4000, N)):
        if MS[j][1] == who and not is_media(MS[j][2]):
            back = (MS[j][0] - dt).total_seconds() / 60; nxt = MS[j][2][:100]; break
    threats.append([dt.strftime('%d.%m.%y %H:%M'), who, t[:200], round(back) if back is not None else None,
                    nxt if back is not None and not blocked(nxt) else ''])

# ---------- dumps for curation ----------
def ctx(i, before=2, after=6):
    out = []
    for j in range(max(0, i - before), min(N, i + after + 1)):
        out.append(('>> ' if j == i else '   ') + f"{MS[j][0]:%d.%m.%y %H:%M} {MS[j][1]}: {MS[j][2][:160]}")
    return '\n'.join(out)
PROPH = re.compile(r'(אני אומר לכם|אני אומר לך|תזכרו את|תזכרו מה|תשמרו את ההודעה|שמרו את ההודעה|תצלמו|צילום מסך|מבטיח לכם|אני מבטיח|תרשמו|רשמו לכם|אני מנבא|נבואה|הימור שלי|ניחוש שלי|אין סיכוי ש|מתערב|בוא נתערב|על כל הכסף|נעלה ליגה|ניקח אליפות|ניקח גביע|נרד ליגה|יורדים ליגה|לא יחזיק|יפוטר עד|תוך חודש|עד סוף העונה)')
with open(os.path.join(HERE, 'proph_cands.txt'), 'w', encoding='utf-8') as f:
    c = [i for i, m in enumerate(MS) if not m[1].startswith('+') and PROPH.search(m[2]) and readable(m[2]) and not blocked(m[2])]
    c.sort(key=lambda i: -(score[i] * 2 + len(MS[i][2]) / 80))
    for i in c[:400]: f.write(f"#{i} s={score[i]}\n{ctx(i, 1, 5)}\n\n")
told = Counter(m[1] for m in MS if not m[1].startswith('+') and re.search(r'(אמרתי לכם|אמרתי לך|אמרתי לכן|צדקתי|מי אמר לכם)', m[2]))

POSW = re.compile(r'(גאון|מלך|אגדה|תותח|מטורף|ענק|אלוף|הכי טוב|כוכב|פצצה|יהלום|קוסם|מדהים|גדול|אוהב אותו|מושלם|חיה|בהמה של שחקן|מפלצת)')
NEGW = re.compile(r'(פלופ|אפס|זבל|גרוע|שיעוף|לפטר|תפטרו|יפוטר|חרא|מביך|בושה|אסון|פח |לא שווה|תתבייש|שיילך|שילך|חלש|מעפן|גועל|נכה|עלוב|קטסטרופה|שיעופו|תעיפו|לא יודע לשחק|לא כדורגלן)')
FIG = ['אלמוג', 'קאלו', 'סילבה', 'שועה', 'אנסה', 'אברמוב', 'יצחקי', 'טוריאל', 'זהבי', 'מוצה', 'מוצ׳ה', 'יוספי', 'ורקו', 'וורקו',
       'אצילי', 'נחמיאס', 'גורפינקל', 'פוטקין', 'רפאלוב', 'זבש', 'לוקה', 'גרינפלד', 'טבארש', 'עזו', 'ירדן', 'שאדו', 'מנדי', 'מורוזוב', 'חגי', 'בוזגלו', 'טל בן חיים', 'כהן']
flips = []
by = defaultdict(list)
for i, (dt, who, t) in enumerate(MS):
    if who.startswith('+') or not readable(t) or blocked(t): continue
    pz, ng = bool(POSW.search(t)), bool(NEGW.search(t))
    if pz == ng: continue
    for fg in FIG:
        if fg in t: by[(who, fg)].append((i, 1 if pz else -1))
for (who, fg), L in by.items():
    for k in range(1, len(L)):
        (i0, s0), (i1, s1) = L[k - 1], L[k]
        if s0 != s1:
            days = (MS[i1][0] - MS[i0][0]).total_seconds() / 86400
            if days <= 45: flips.append((days, who, fg, i0, i1))
flips.sort()
with open(os.path.join(HERE, 'flip_cands.txt'), 'w', encoding='utf-8') as f:
    for days, who, fg, i0, i1 in flips[:500]:
        f.write(f"## {who} / {fg} / {days:.1f}d  #{i0}->#{i1}\n  A {MS[i0][0]:%d.%m.%y %H:%M}: {MS[i0][2][:200]}\n  B {MS[i1][0]:%d.%m.%y %H:%M}: {MS[i1][2][:200]}\n")

# psych features for hand-written diagnoses
group_w = Counter(); pw = defaultdict(Counter); pfig = defaultdict(Counter); pemo = defaultdict(Counter)
EMO = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
for i, (dt, who, t) in Y:
    if who not in st or is_media(t) or 'http' in t: continue
    for w in set(TOK.findall(t)):
        if w in STOP or len(w) < 3: continue
        group_w[w] += 1; pw[who][w] += 1
    for fg in FIG:
        if fg in t: pfig[who][fg] += 1
    for e in EMO.findall(t): pemo[who][e] += 1
with open(os.path.join(HERE, 'psych_cands.txt'), 'w', encoding='utf-8') as f:
    for n in ACTIVE:
        s = st[n]; G = sum(group_w.values()); W = sum(pw[n].values())
        sig = sorted(((c / W) / ((group_w[w] + 5) / G), w) for w, c in pw[n].items() if c >= 6)[-14:][::-1]
        top_i = sorted([i for i, m in Y if m[1] == n and readable(m[2]) and not blocked(m[2])], key=lambda i: -score[i])[:8]
        f.write(f"=== {n} msgs={s['msgs']} rank={ACTIVE.index(n) + 1} night={100 * s['night'] // s['msgs']}% peak={s['hours'].most_common(3)} "
                f"curse={100 * s['curse'] / max(1, s['txt']):.1f}% q={100 * s['q'] / max(1, s['txt']):.0f}% laughgive={100 * s['laugh_give'] // s['msgs']}% "
                f"media={100 * s['media'] // s['msgs']}% len={s['chars'] / max(1, s['txt']):.0f} lat={statistics.median(s['lat']) if s['lat'] else '-'}s funny/100={100 * raw['sho'][n]:.1f}\n")
        f.write(f"  partner={matches[n]['partner'][0]} nemesis={matches[n]['nemesis'][0]} fan={matches[n]['fan'][0]} threats={sum(1 for t in threats if t[1] == n)} told={told[n]}\n")
        f.write(f"  figs={pfig[n].most_common(5)} emo={''.join(e for e, _ in pemo[n].most_common(6))}\n  sig={[w for _, w in sig]}\n")
        for i in top_i: f.write(f"  [{score[i]}] {MS[i][2][:170]}\n")
        f.write('\n')

auto = dict(end=END.strftime('%d.%m.%Y'), year0=YEAR0.strftime('%d.%m.%Y'), people=PEOPLE, bins=BIN_LABELS,
            index=index, pool=pool, fifa=fifa, matches=matches, couples=couples, kicks=kicks, threats=threats,
            told=told.most_common(15), total=N)
json.dump(auto, open(os.path.join(HERE, 'data_auto.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('vocab', len(index), 'pool', len(pool), 'active', len(ACTIVE), 'threats', len(threats), 'kicks', len(kicks), 'flips', len(flips),
      'size MB', round(os.path.getsize(os.path.join(HERE, 'data_auto.json')) / 1e6, 2))
