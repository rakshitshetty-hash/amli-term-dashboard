"""Builds public/callcentre.json for the Call centre tab.

Input: the "Call Centre report" Google Sheet, exported as .xlsx. It has six daily agent-productivity
tabs (Overall, Top Funnel, SEM Core, Vernac, Bottom Funnel, Affiliate) and six hourly lead-dialling
tabs with the same segments.

    python3 scripts/callcentre.py --report <Call Centre report .xlsx> --out public/callcentre.json
"""
import argparse, json
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--report', required=True)
ap.add_argument('--out', default='public/callcentre.json')
a = ap.parse_args()

x = {k.strip(): v for k, v in pd.read_excel(a.report, sheet_name=None).items()}
DAILY = {'Overall': 'Overall', 'Top Funnel': 'Top Funnel', 'SEM Core': 'SEM Core', 'Vernac': 'Vernac', 'Bottom Funnel': 'Bottom Funnel', 'Affiliate': 'Affiliate'}
HOURLY = {'Hourly - Overall': 'Overall', 'Hourly Top Funnel': 'Top Funnel', 'Hourly SEM Core': 'SEM Core', 'Hourly Vernac': 'Vernac', 'Hourly Bottom': 'Bottom Funnel', 'Hourly Affiliate': 'Affiliate'}
COLS = ['date', 'login', 'notready', 'tos', 'idle', 'idle_rate', 'talk', 'dial', 'util', 'wrap_conn_s', 'wrap_nc_s', 'wrap', 'att_min', 'agents', 'calls_pa', 'connect']

d = []
for tab, seg in DAILY.items():
    t = x[tab].iloc[:, :16].copy(); t.columns = COLS; t['seg'] = seg; d.append(t)
d = pd.concat(d)
d['date'] = pd.to_datetime(d.date, errors='coerce'); d = d[d.date.notna()]
for c in COLS[1:]: d[c] = pd.to_numeric(d[c], errors='coerce')
d['conn_pa'] = d.calls_pa * d.connect
d['date'] = d.date.dt.strftime('%Y-%m-%d')
keep = ['seg', 'date', 'agents', 'login', 'notready', 'tos', 'idle_rate', 'util', 'calls_pa', 'connect', 'conn_pa', 'att_min', 'wrap_conn_s', 'wrap', 'talk', 'dial', 'idle']

h = []
for tab, seg in HOURLY.items():
    t = x[tab].iloc[:, :6].copy(); t.columns = ['cdate', 'bdate', 'hour', 'status', 'dial', 'leads']; t['seg'] = seg; h.append(t)
h = pd.concat(h)
h['bdate'] = pd.to_datetime(h.bdate, errors='coerce'); h = h[h.bdate.notna()]
h['leads'] = pd.to_numeric(h.leads, errors='coerce').fillna(0); h['hour'] = pd.to_numeric(h.hour, errors='coerce').astype(int)
nd = h.dial.astype(str).str.strip().eq('Not_Dialled'); st = h.status.astype(str).str.strip()
h['ond'] = np.where(nd & st.eq('Open'), h.leads, 0); h['cnd'] = np.where(nd & st.eq('Close'), h.leads, 0)
H = h.groupby(['seg', 'bdate', 'hour'])[['leads', 'ond', 'cnd']].sum().reset_index()
H['bdate'] = H.bdate.dt.strftime('%Y-%m-%d')

out = {'cc_daily': json.loads(d[keep].round(4).to_json(orient='records')),
       'cc_hourly': json.loads(H.astype({'leads': int, 'ond': int, 'cnd': int}).to_json(orient='records')),
       'cc_meta': {'daily_from': d.date.min(), 'daily_to': d.date.max(), 'hourly_from': H.bdate.min(), 'hourly_to': H.bdate.max()}}
json.dump(out, open(a.out, 'w'), separators=(',', ':'))
print('daily', out['cc_meta']['daily_from'], '→', out['cc_meta']['daily_to'], '| hourly', out['cc_meta']['hourly_from'], '→', out['cc_meta']['hourly_to'])
