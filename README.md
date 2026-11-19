# AMLI Term – daily performance dashboard

A static site with six tabs (Overview, Day on day, Cream audience, Prospecting, Call centre, Payments). Vercel serves `public/`. The first three tabs read `public/data.json`, which `scripts/process.py` rebuilds each day. The Prospecting tab reads `public/prospecting.json`, which `scripts/prospecting.py` builds from the GA4 consolidated report.

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

## Call centre tab update

Export the "Call Centre report" Google Sheet as `.xlsx` (File → Download → Microsoft Excel), then run:

```
python3 scripts/callcentre.py --report <Call Centre report .xlsx> --out public/callcentre.json
```

Then commit and push. The tab compares each day with the median of the 7 days before it, for each segment (Overall, Top Funnel, SEM Core, Vernac, Bottom Funnel, Affiliate). Ready time = login − not-ready; true utilisation = (talk + dial) ÷ ready time; idle rate = idle ÷ ready time; connects per agent = calls per agent × Connect%. Undialled = leads still open with no dial; closed, no dial = leads closed with no dial. Flags fire on: calls per agent under 70% of usual with normal logins and idle up 8+ pts (system issue), agents down 15%+, undialled 5%+, closed with no dial 15%+, idle 25%+, Connect% down 1.5+ pts, wrap per connected call up 30%+. The findings cards are text written on 13 Nov from the 14 Oct – 12 Nov report and don't update.

## Payments tab update

Export the "Payment Report" Google Sheet as `.xlsx`, then run:

```
python3 scripts/payments.py --report <Payment Report .xlsx> --out public/payments.json
```

Then commit and push. Successful payments = transactions × success %, and the same for each method. "Other" = Overall minus Core, PR and SEO. A segment's day is marked incomplete when its transactions are under 30% of its 7-day median. The Yesterday section also reads the call-centre data, so refresh `callcentre.json` on the same day to explain volume drops.

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

## Creatives received page (`/creatives`)

A separate client-facing page, `public/creatives/index.html`, counting creatives received each month from the "Term - HM (Int)" tab of the "Creative Repository Dashboard - AMLI x HM" sheet: Static (Branded / Non-Branded HM AI) and Video (Annual Deal Influencers / Non-Annual Deal Influencers / Nano / Branded). Months follow the sheet's Month column.

- **Sync:** `apps-script/creatives/Code.gs` runs as a Google Apps Script under a HiveMinds login (public web apps are blocked on the Workspace). `syncToGitHub` reads the sheet and commits counts only (no ad names or links) to `public/creatives.json` when they change and at least once a day; `setupSchedule` runs it daily around 6 am and 6 pm IST. It needs a GitHub fine-grained token (this repo, Contents: read and write) saved as the `GITHUB_TOKEN` script property. Each commit redeploys Vercel.
- The page reads `public/creatives.json`; Refresh reloads it. `API_URL` in the page stays empty unless the script is ever published as a public web app.
- Classification rules (annual-deal list, Nano face types, HM AI tag) sit at the top of `Code.gs`.
