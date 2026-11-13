# AMLI Term – daily performance dashboard

A static site with three tabs (Overview, Day on day, Cream audience). Vercel serves `public/`. The page reads `public/data.json`, which `scripts/process.py` rebuilds each day.

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
