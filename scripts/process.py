#!/usr/bin/env python3
"""Build public/data.json for the AMLI Term dashboard.

Inputs (all paths are arguments):
  --leads    Unique lead dump (.xlsb or .xlsx), sheet "Direct Term"
  --sales    Direct & D2C sales dump (.xlsx), sheet "Term"
  --spends   CSV of the "Term All Channels" tab: header row, then one row per day
  --mapping  Master Tracker mapping workbook (sheets "Mapping", "Spends Tracker")
  --plan     Month media plan workbook (sheets "FInal", "DOD", "QL DOD")
  --out      Output JSON path (default public/data.json)

Rules:
  Leads are dated by CRM lead creation date. Sales and APE by payment date.
  Source codes map to DRR line items via the Mapping sheet; config/overrides.json can
  move a source code to another short line item (NewBlank7 -> Brand).
  Cream = income 10L+ AND Salaried AND Graduate & above.
  Spend targets: the plan's Cost column, spread across days on the QL curve (the same
  curve as leads), so a day's target spend = its target leads x the line item's plan CPL.
"""
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import column_index_from_string

ITEMS = ['SEO', 'Brand', 'Core', 'Others', 'PR', 'RM', 'New Affiliate', 'Amazon', 'Netcore']
HI_INCOME = {'10-20 lakhs', '> 20 lakhs', '20-35 lakhs', '> 50 lakhs', '35-50 lakhs', '> 15 lakh'}
# Plan rows behind each line item (daily targets) and each summary group.
ITEM_PLAN = {
    'SEO': ['SEO'], 'Brand': ['SEM Brand + Bing'], 'Core': ['Keyword category 2 & 5 (Core + RLSA)'],
    'Others': ['Keyword category 3'], 'PR': ['FB WC + Vserve PR (FB Prospecting)'], 'RM': ['GDN RM'],
    'New Affiliate': ['New Affiliate', 'DRIM'], 'Amazon': ['Amazon'],
    'Netcore': ['Netcore DropLead', 'Netcore Chase+Birthday', 'Netcore Chase'],
}
GROUPS = [  # (name, plan rows, actual short line items)
    ('Bottom Funnel', ['SEM Brand + Bing', 'Keyword category 2 & 5 (Core + RLSA)', 'Keyword category 3'], ['Brand', 'Core', 'Others']),
    ('Display', ['FB WC + Vserve PR (FB Prospecting)', 'GDN RM'], ['PR', 'RM']),
    ('New Affiliate', ['New Affiliate', 'DRIM'], ['New Affiliate', 'DRIM']),
    ('NRI Search', ['NRI_SWP'], ['NRI Search']),
    ('NRI PR', ['NRI Prospecting'], ['NRI PR']),
    ('Netcore', ['Netcore DropLead', 'Netcore_Cross-sell + Upsell', 'Netcore Chase+Birthday', 'Netcore Chase'],
     ['Netcore', 'App customers_buy_online', 'App Cross Sell', 'Upsell Journey']),
    ('Amazon', ['Amazon'], ['Amazon']),
    ('SEO', ['SEO'], ['SEO']),
]


def s(v):
    return '' if v is None else str(v).strip()


def num(v):
    v = s(v).replace(',', '')
    try:
        return float(v) if v else 0.0
    except ValueError:
        return 0.0


def load_mapping(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    m = wb['Mapping']
    lead_map = {s(r[1]): s(r[2]) for r in m.iter_rows(min_row=2, values_only=True) if s(r[1])}
    sale_map = {s(r[5]): s(r[6]) for r in m.iter_rows(min_row=2, values_only=True) if len(r) > 6 and s(r[5])}
    st = [(s(r[1]), s(r[2]), s(r[3])) for r in wb['Spends Tracker'].iter_rows(min_row=2, values_only=True) if s(r[1])]
    drr2short = {drr: short for _, drr, short in st}
    drr2short.update({'SEO': 'SEO', 'Netcore': 'Netcore', 'New Affiliate': 'New Affiliate', 'Amazon': 'Amazon'})
    return lead_map, sale_map, st, drr2short


def load_overrides():
    p = Path(__file__).resolve().parent.parent / 'config' / 'overrides.json'
    return json.loads(p.read_text()) if p.exists() else {}


def tag(df, src_col, cmap, drr2short, overrides):
    src = df[src_col].astype(str).str.strip()
    li = src.map(cmap).map(lambda x: drr2short.get(x, x) if isinstance(x, str) else 'Unmapped')
    for code, short in overrides.get('source_to_line_item', {}).items():
        li[src == code] = short
    return li


def load_leads(path):
    engine = 'pyxlsb' if str(path).lower().endswith('.xlsb') else None
    df = pd.read_excel(path, sheet_name='Direct Term', engine=engine)
    raw = df['CRM Lead Creation date']
    if pd.api.types.is_numeric_dtype(raw):
        d = pd.to_datetime(raw, unit='D', origin='1899-12-30')
    else:
        d = pd.to_datetime(raw, errors='coerce')
    df['d'] = d.dt.normalize()
    return df


def load_sales(path):
    df = pd.read_excel(path, sheet_name='Term')
    d = pd.to_datetime(df.get('Payement Date'), errors='coerce')
    d = d.fillna(pd.to_datetime(df['Payment date & Time'], errors='coerce'))
    df['d'] = d.dt.normalize()
    return df


def load_spends(path, st):
    rows = list(__import__('csv').reader(open(path, newline='', encoding='utf-8')))
    head, body = rows[0], rows[1:]
    names = [n.replace('  ', ' ') for n, _, _ in st]
    shorts = [x for _, _, x in st]
    used = [False] * len(st)
    col_short = {}
    for i, h in enumerate(head[1:], start=1):
        k = s(h).replace('  ', ' ')
        if k.lower() == 'total':
            continue
        for j, n in enumerate(names):
            if not used[j] and n == k:
                used[j] = True
                col_short[i] = shorts[j]
                break
        else:
            col_short[i] = 'Unmapped spend: ' + k
    out = []
    for r in body:
        m = re.match(r'(\d{2})/(\d{2})/(\d{4})', s(r[0]) if r else '')
        if not m:
            continue
        day = pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if not any(num(r[i]) for i in col_short if i < len(r)):
            continue  # an empty future day
        for i, short in col_short.items():
            if i < len(r):
                out.append((day, short, num(r[i])))
    return pd.DataFrame(out, columns=['d', 'li', 'spend'])


def load_plan(path, month_start):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['FInal']
    label = month_start.strftime("%b'%y") + ' Plan'
    start = None
    for row in ws.iter_rows(min_row=1, max_row=3):
        for c in row:
            if s(c.value) == label:
                start = c
                break
        if start:
            break
    if not start:
        sys.exit(f'Plan block "{label}" not found in sheet FInal')
    col, hdr_row = start.column, start.row + 1
    heads = {}
    for c in range(col, col + 20):
        h = s(ws.cell(hdr_row, c).value).lower()
        if h and h not in heads:
            heads[h] = c
    need = {'leads': 'leads', 'nop': 'nop', 'afyp': 'afyp'}
    for k in need:
        if k not in heads:
            sys.exit(f'Column "{k}" not found in the {label} header row')
    c_cost, c_cpl = heads.get('cost'), heads.get('cpl')
    plan = {}
    for r in range(hdr_row + 1, hdr_row + 41):
        k = s(ws.cell(r, col).value)
        if not k:
            continue
        plan[k] = dict(L=num(ws.cell(r, heads['leads']).value), N=num(ws.cell(r, heads['nop']).value),
                       A=num(ws.cell(r, heads['afyp']).value) * 1e7,
                       C=num(ws.cell(r, c_cost).value) if c_cost else 0.0)
    dod = wb['DOD']
    nop = [num(dod.cell(r, 3).value) for r in range(2, 2 + month_start.days_in_month)]
    ape = [num(dod.cell(r, 4).value) for r in range(2, 2 + month_start.days_in_month)]
    ql = [num(wb['QL DOD'].cell(r, 3).value) for r in range(2, 2 + month_start.days_in_month)]
    return plan, ql, nop, ape


def main():
    ap = argparse.ArgumentParser()
    for a in ['leads', 'sales', 'spends', 'mapping', 'plan']:
        ap.add_argument('--' + a, required=True)
    ap.add_argument('--out', default='public/data.json')
    a = ap.parse_args()

    lead_map, sale_map, st, drr2short = load_mapping(a.mapping)
    ov = load_overrides()
    L = load_leads(a.leads)
    S = load_sales(a.sales)
    SP = load_spends(a.spends, st)

    last = min(L['d'].max(), S['d'].max(), SP['d'].max())
    month_start = last.replace(day=1)
    L = L[(L.d >= month_start) & (L.d <= last)].copy()
    S = S[(S.d >= month_start) & (S.d <= last)].copy()
    SP = SP[(SP.d >= month_start) & (SP.d <= last)]
    L['li'] = tag(L, 'Source Code (VSM)', lead_map, drr2short, ov)
    S['li'] = tag(S, 'Source Code (VSM)', sale_map, drr2short, ov)
    L['cream'] = L['Income Range'].isin(HI_INCOME) & L['Occupation'].eq('Salaried') & L['Education'].eq('Graduate & above')

    sp = SP.groupby(['d', 'li']).spend.sum()
    ld = L.groupby(['d', 'li']).size().rename('leads')
    sl = S.groupby(['d', 'li']).agg(sales=('APE', 'size'), ape=('APE', 'sum'))
    D = pd.concat([sp, ld, sl], axis=1).fillna(0).reset_index()
    days = pd.date_range(month_start, last)

    daily, cream = [], []
    for x in days:
        dd = D[D.d == x]
        ll = L[L.d == x]
        for it in ITEMS + ['All channels']:
            part = dd if it == 'All channels' else dd[dd.li == it]
            lpart = ll if it == 'All channels' else ll[ll.li == it]
            daily.append(dict(date=x.strftime('%Y-%m-%d'), line_item=it, spend=round(part.spend.sum()), leads=int(part.leads.sum()),
                              sales=int(part.sales.sum()), ape=round(part.ape.sum())))
            cream.append(dict(date=x.strftime('%Y-%m-%d'), line_item=it, leads=len(lpart), cream_leads=int(lpart.cream.sum())))

    plan, ql, nop, apec = load_plan(a.plan, month_start)
    paid_rows = [k for k in plan if not k.lower().startswith(('total', 'unique'))]
    unique_total = dict(L=plan.get('Total Unique Leads excluding HSA ULIP', {}).get('L', 0),
                        N=plan.get('Unique Sale excluding HSA ULIP', {}).get('N', 0),
                        A=plan.get('Unique Sale excluding HSA ULIP', {}).get('A', 0),
                        C=sum(plan[k].get('C', 0) for k in paid_rows))
    tot = lambda keys, m: sum(plan.get(k, {}).get(m, 0) for k in keys)
    item_t = {it: {m: tot(keys, m) for m in 'LNAC'} for it, keys in ITEM_PLAN.items()}
    item_t['All channels'] = unique_total
    targets = []
    for i, x in enumerate(pd.date_range(month_start, month_start + pd.offsets.MonthEnd(0))):
        for it, t in item_t.items():
            targets.append(dict(date=x.strftime('%Y-%m-%d'), line_item=it,
                                target_leads=round(t['L'] * ql[i] / sum(ql), 1),
                                target_sales=round(t['N'] * nop[i] / sum(nop), 2),
                                target_ape=round(t['A'] * apec[i] / sum(apec)),
                                target_spend=round(t['C'] * ql[i] / sum(ql))))

    n = last.day
    shL, shN, shA = sum(ql[:n]) / sum(ql), sum(nop[:n]) / sum(nop), sum(apec[:n]) / sum(apec)
    summary = []
    def add(order, name, t, acts):
        summary.append(dict(order=order, group=name,
                            leads_target_month=round(t['L']), leads_target_mtd=round(t['L'] * shL), leads_mtd=int(acts.leads.sum()),
                            sales_target_month=round(t['N']), sales_target_mtd=round(t['N'] * shN), sales_mtd=int(acts.sales.sum()),
                            ape_l_target_month=round(t['A'] / 1e5, 1), ape_l_target_mtd=round(t['A'] * shA / 1e5, 1),
                            ape_l_mtd=round(acts.ape.sum() / 1e5, 1)))
    add(1, 'Total', unique_total, D)
    for i, (name, keys, acts) in enumerate(GROUPS, start=2):
        add(i, name, {m: tot(keys, m) for m in 'LNA'}, D[D.li.isin(acts)])

    unmapped = sorted(set(L.loc[L.li == 'Unmapped', 'Source Code (VSM)'].astype(str)) | set(S.loc[S.li == 'Unmapped', 'Source Code (VSM)'].astype(str)))
    out = dict(meta=dict(as_of=last.strftime('%Y-%m-%d'), generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                         unmapped_source_codes=unmapped),
               targets_vs_actuals=summary, daily_performance=daily, daily_targets=targets, cream_leads=cream)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, separators=(',', ':')))
    print(f'as_of {last.date()} · leads {len(L)} · sales {len(S)} · spend {SP.spend.sum():,.0f} · unmapped {unmapped}')


if __name__ == '__main__':
    main()
