"""Builds public/payments.json for the Payments tab.

Input: the "Payment Report" Google Sheet exported as .xlsx, with tabs Overall, Core, PR and SEO.
Each row is a day: total transactions (payment attempts), success %, and attempts, share and success % for
UPI, credit card, debit card and net banking. "Other" = Overall minus Core, PR and SEO.

    python3 scripts/payments.py --report <Payment Report .xlsx> --out public/payments.json
"""
import argparse, json
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--report', required=True)
ap.add_argument('--out', default='public/payments.json')
a = ap.parse_args()

COLS = ['date', 'tx', 'succ', 'upi_a', 'upi_sel', 'upi_s', 'cc_a', 'cc_sel', 'cc_s', 'dc_a', 'dc_sel', 'dc_s', 'nb_a', 'nb_sel', 'nb_s']
M = ['upi', 'cc', 'dc', 'nb']
rows = []
for name, t in pd.read_excel(a.report, sheet_name=None).items():
    seg = name.strip()
    if seg not in ('Overall', 'Core', 'PR', 'SEO'):
        continue
    t = t.iloc[:, :15].copy(); t.columns = COLS; t['seg'] = seg
    t['date'] = pd.to_datetime(t.date, errors='coerce'); t = t[t.date.notna()]
    for c in COLS[1:]: t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0)
    t['ok'] = (t.tx * t.succ).round()
    for m in M: t[m + '_ok'] = (t[m + '_a'] * t[m + '_s']).round()
    rows.append(t)
d = pd.concat(rows)
keep = ['tx', 'ok'] + [m + '_a' for m in M] + [m + '_ok' for m in M]
o = d[d.seg == 'Overall'].set_index('date')[keep]
s = d[d.seg.isin(['Core', 'PR', 'SEO'])].groupby('date')[keep].sum().reindex(o.index, fill_value=0)
oth = (o - s).clip(lower=0).reset_index(); oth['seg'] = 'Other'
d = pd.concat([d[['seg', 'date'] + keep], oth[['seg', 'date'] + keep]])
d['date'] = d.date.dt.strftime('%Y-%m-%d')
for c in keep: d[c] = d[c].astype(int)
json.dump({'pay_daily': json.loads(d.to_json(orient='records'))}, open(a.out, 'w'), separators=(',', ':'))
print('payments', d.date.min(), '→', d.date.max(), '|', len(d), 'rows')
