"""Builds public/prospecting.json for the Prospecting tab.

Input: the AMLI GA4 Term Consolidated Report (.xlsb), sheet "OTP GA4 Report".
Scope: Channel in (Meta, Google) and Theme1 == "Prospecting".
Metrics kept: Cost (spend), Leads, QL, QQ-G. CPL, QL% and CPQQG are worked out on the page.

    python3 scripts/prospecting.py --report <GA4 consolidated .xlsb> --out public/prospecting.json
"""
import argparse, json, re
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--report', required=True)
ap.add_argument('--out', default='public/prospecting.json')
a = ap.parse_args()

df = pd.read_excel(a.report, sheet_name='OTP GA4 Report', engine='pyxlsb')
p = df[df.Channel.isin(['Meta', 'Google']) & (df.Theme1 == 'Prospecting')].copy()
p['dt'] = pd.to_datetime(pd.to_numeric(p.Date, errors='coerce'), unit='D', origin='1899-12-30')
p = p[p.dt.notna()]
COLS = {'Cost': 'spend', 'Leads': 'leads', 'QL': 'ql', 'QQ-G': 'qqg'}
for c in COLS:
    p[c] = pd.to_numeric(p[c], errors='coerce').fillna(0)
p = p.rename(columns=COLS)
M = list(COLS.values())

last = p.dt.max()
start = (last.replace(day=1) - pd.DateOffset(months=1)).normalize()   # first day of last month
p = p[p.dt >= start]
p['date'] = p.dt.dt.strftime('%Y-%m-%d')

# 1. Line item (campaign) x day
c = p.groupby(['date', 'Channel', 'Campaign'])[M].sum().reset_index()
c = c.rename(columns={'Channel': 'channel', 'Campaign': 'campaign'})
c = c[c.spend > 0]

# Meta ad-name attributes
LANGS = {'English', 'Hindi', 'Hinglish', 'Kannada', 'Telugu', 'Tamil', 'Malayalam', 'Marathi', 'Bengali', 'Gujarati', 'Odia', 'Punjabi'}
CREATOR = {'InfluencerAffiliate': 'Influencer', 'InfluencerUGC': 'Influencer', 'HMInfluencerUGC': 'Influencer', 'UGCModel': 'Influencer',
           'Nano': 'Nano creator', 'Celeb': 'Celeb', 'AICeleb': 'Celeb', 'CelebAIOthers': 'Celeb',
           'AIOthers': 'AI generated', 'HmAI': 'AI generated', 'HmAIBrand': 'AI generated', 'GeoAds': 'GeoAds', 'Inhouse': 'Inhouse'}
SKIP = {'AI', 'NonAI', 'NewCPR', 'NoCPR', 'NonBranded', 'Branded', 'SD', 'Revamp', 'Term', 'Static', 'Video', 'Gif'} | LANGS
STOP = set(CREATOR) | {'P2C', 'Human', 'Vector', 'Dialogue', 'Men', 'Women', 'WomenMen', 'TermInsurance'}

def parse(name):
    t = str(name).split('_'); low = [x.lower() for x in t]
    r = {'partner': t[0] if len(t) > 2 else 'Other',
         'format': 'Video' if 'video' in low else ('Static' if ('static' in low or 'gif' in low) else 'Other'),
         'language': 'Unknown', 'creator': 'Other', 'launch': None}
    for x in t:
        if x in LANGS: r['language'] = x
        if x in CREATOR: r['creator'] = CREATOR[x]
    hook = []
    for x in t[1:]:
        if x in STOP or re.fullmatch(r'\d+Cr\d*|\d{8}', x): break
        if x in SKIP or x == t[0]: continue
        hook.append(x)
    r['hook'] = ' '.join(hook[:4]) or ' '.join(t[:3])
    if re.fullmatch(r'\d{8}', t[-1]):
        d = pd.to_datetime(t[-1], format='%d%m%Y', errors='coerce')
        r['launch'] = None if pd.isna(d) else d.strftime('%Y-%m-%d')
    return r

m = p[p.Channel == 'Meta'].copy()
attrs = pd.DataFrame([dict(ad=n, **parse(n)) for n in m['Ad Name'].dropna().unique()])
m = m.merge(attrs, left_on='Ad Name', right_on='ad')

# 2. Meta video vs static x day
f = m[m.format != 'Other'].groupby(['date', 'format'])[M].sum().reset_index()

# 3. Meta ads: last 14 days and the 14 before
l14 = last - pd.Timedelta(days=13); p14 = l14 - pd.Timedelta(days=14)
m['w'] = None
m.loc[m.dt >= l14, 'w'] = 'l14'
m.loc[(m.dt >= p14) & (m.dt < l14), 'w'] = 'p14'
g = m[m.w.notna()].pivot_table(index='ad', columns='w', values=M, aggfunc='sum', fill_value=0)
g.columns = [f'{x}_{y}' for x, y in g.columns]
g = attrs.merge(g.reset_index(), on='ad')
for col in [f'{x}_{y}' for x in M for y in ('l14', 'p14')]:
    if col not in g: g[col] = 0
g = g[(g.spend_l14 > 0) | (g.spend_p14 > 0)]

def rows(d):
    d = d.copy()
    for k in d.columns:
        if d[k].dtype.kind == 'f': d[k] = d[k].round(0).astype(int)
    return json.loads(d.to_json(orient='records'))

out = {
    'pr_meta': {'as_of': last.strftime('%Y-%m-%d'), 'l14_start': l14.strftime('%Y-%m-%d'), 'p14_start': p14.strftime('%Y-%m-%d'),
                'source': a.report.split('/')[-1]},
    'pr_campaign_daily': rows(c),
    'pr_meta_format_daily': rows(f),
    'pr_meta_ads': rows(g),
}
json.dump(out, open(a.out, 'w'), ensure_ascii=False, separators=(',', ':'))
print('as of', out['pr_meta']['as_of'], '| line-item days', len(c), '| ads', len(g))
