#!/usr/bin/env python3
"""Build config/cream_benchmark.json: each line item's all-time best day of cream share.

Usage:
  python3 scripts/benchmark.py --leads <best-month lead dump .xlsx/.xlsb> --mapping config/mapping.xlsx

A day counts only if it has enough leads to read: at least 50, and at least 30% of the
line item's median daily leads that month. Of those days, a share above Q3 + 1.5 x IQR is
treated as an anomaly and left out. The best remaining day is the benchmark.
The raw dump is not stored; only the benchmarks are.
"""
import argparse, json
from pathlib import Path

import pandas as pd

import process as P

MIN_LEADS, MIN_SHARE_OF_MEDIAN = 50, 0.3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leads', required=True)
    ap.add_argument('--mapping', required=True)
    ap.add_argument('--sheet', default=None, help='sheet name; default: first sheet')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent.parent / 'config' / 'cream_benchmark.json'))
    a = ap.parse_args()

    engine = 'pyxlsb' if a.leads.lower().endswith('.xlsb') else None
    A = pd.read_excel(a.leads, sheet_name=a.sheet or 0, engine=engine)
    raw = A['CRM Lead Creation date']
    d = pd.to_datetime(raw, unit='D', origin='1899-12-30') if pd.api.types.is_numeric_dtype(raw) else pd.to_datetime(raw, errors='coerce')
    A['d'] = d.dt.normalize()
    lead_map, _, _, drr2short = P.load_mapping(a.mapping)
    A['li'] = P.tag(A, 'Source Code (VSM)', lead_map, drr2short, P.load_overrides())
    A['cream'] = A['Income Range'].isin(P.HI_INCOME) & A['Occupation'].eq('Salaried') & A['Education'].eq('Graduate & above')

    out = []
    for it in P.ITEMS + ['All channels']:
        s = A if it == 'All channels' else A[A.li == it]
        g = s.groupby('d').agg(leads=('cream', 'size'), cream=('cream', 'sum'))
        row = dict(line_item=it, month=A.d.min().strftime('%Y-%m'), month_leads=int(len(s)),
                   month_share=round(float(s.cream.mean()), 4) if len(s) else None, best_share=None, best_date=None,
                   best_day_leads=None, days_left_out=None)
        if len(g):
            g['share'] = g.cream / g.leads
            ok = g[g.leads >= max(MIN_LEADS, MIN_SHARE_OF_MEDIAN * g.leads.median())]
            if len(ok):
                q1, q3 = ok.share.quantile([0.25, 0.75])
                ok = ok[ok.share <= q3 + 1.5 * (q3 - q1)]
            if len(ok):
                b = ok.share.idxmax()
                row.update(best_share=round(float(ok.share.max()), 4), best_date=b.strftime('%Y-%m-%d'),
                           best_day_leads=int(ok.loc[b, 'leads']), days_left_out=int(len(g) - len(ok)))
        out.append(row)
    Path(a.out).write_text(json.dumps(out, indent=1))
    for r in out:
        print(r)


if __name__ == '__main__':
    main()
