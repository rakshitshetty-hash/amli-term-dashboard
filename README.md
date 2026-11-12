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

Replace `config/plan.xlsx` with the new month's media plan. It must keep the "FInal" sheet with a `Mon'YY Plan` block, plus the "DOD" and "QL DOD" sheets.

## Rules the numbers follow

- Leads are dated by CRM lead creation date. Sales and APE are dated by payment date.
- Source codes map to line items through `config/mapping.xlsx`. `config/overrides.json` moves NewBlank7 into Brand.
- Daily and month-to-date targets follow the plan's daily curves: QL for leads, NOP for sales, APE for APE.
- Cream = income 10L+, salaried and graduate & above.

## Vercel settings

Framework preset: Other. Build command: none. Output directory: `public` (set in `vercel.json`).
