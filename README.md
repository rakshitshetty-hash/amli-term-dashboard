# AMLI Term – daily performance dashboard

A static site with four tabs (Overview, Day on day, Cream audience, Prospecting). Vercel serves `public/`. The first three tabs read `public/data.json`, which `scripts/process.py` rebuilds each day. The Prospecting tab reads `public/prospecting.json`, which `scripts/prospecting.py` builds from the GA4 consolidated report.

## Daily update

1. Drop the day's files in the Drive folder: the unique lead dump (`.xlsb`) and the Direct & D2C sales dump (`.xlsx`).
2. The update pulls the "Term All Channels" tab of the Daily Spends Tracker into `data/spends.csv`, runs:

   ```
   pip install -r requirements.txt
   python3 scripts/process.py \
     --leads <lead dump> --sales <sales dump> \
     --spends data/spends.csv \
     --mapping config/mapping.xlsx --plan config/plan.xlsx \
     --out public/data.json
   ```

3. Commit and push. Vercel redeploys on every push to `main`.

`process.py` prints the as-of date, totals, and any source codes the mapping doesn't cover. Add those to `config/mapping.xlsx` (the Master Tracker mapping) and run it again.

## Prospecting tab update

When a new AMLI GA4 Term Consolidated Report (`.xlsb`) lands, run:

```
python3 scripts/prospecting.py --report <GA4 consolidated .xlsb> --out public/prospecting.json
```

Then commit and push. The tab covers Meta and Google rows with Theme1 = Prospecting and shows CPL (Spend ÷ Leads), QL% (QL ÷ Leads) and CPQQG (Spend ÷ QQ-G), MTD against the same days last month. Creative attributes (format, partner, language, creator type, launch date) are read from the Meta ad naming convention. The "What to do" list is worked out on the page: line items against their channel's CPQQG (Efficient ≤ 0.9×, Expensive ≥ 1.2×), Meta ads with ₹1L+ spend in the last 14 days against the Meta CPQQG (Scale ≤ 0.8×, Pause ≥ 1.5× or no QQ-G).

## Monthly update

Replace `config/plan.xlsx` with the new month's media plan. It must keep the "FInal" sheet with a `Mon'YY Plan` block whose header row names the Cost, CPL, Leads, NOP and AFYP columns, plus the "DOD" and "QL DOD" sheets.

## Rules the numbers follow

- Leads are dated by CRM lead creation date. Sales and APE are dated by payment date.
- Source codes map to line items through `config/mapping.xlsx`. `config/overrides.json` moves NewBlank7 into Brand.
- Daily and month-to-date targets follow the plan's daily curves: QL for leads, NOP for sales, APE for APE.
- Spend targets come from the plan's Cost column, spread over days on the QL curve, so a day's target spend = its target leads × the plan CPL. Cost pacing = spend ÷ target spend.
- Cream = income 10L+, salaried and graduate & above. The Cream tab compares each line item with its all-time best day, stored in `config/cream_benchmark.json`. Rebuild it from a new best month with `python3 scripts/benchmark.py --leads <dump> --mapping config/mapping.xlsx`; the raw dump is not kept in the repo.

## Vercel settings

Framework preset: Other. Build command: none. Output directory: `public` (set in `vercel.json`).
