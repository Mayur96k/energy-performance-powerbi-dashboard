# Build the report in Power BI Desktop

Following these steps takes about 45–60 minutes and rebuilds the four pages shown in `docs/screenshots/`. You need Power BI Desktop (free, Windows).

## 1. Get the data
1. Clone the repo, or download it as a ZIP and extract it.
2. Optional: regenerate the data with `python src/generate_data.py`. The CSVs are already in `data/`.

## 2. Load the queries
1. Open Power BI Desktop and go to **Transform data**.
2. Create the **`DataFolder`** parameter (**Manage Parameters → New**, type *Text*) and set it to your local `data\` folder, including the trailing `\`.
3. For each block in [`power-query/queries.pq`](power-query/queries.pq), go to **New Source → Blank Query → Advanced Editor**, paste the block, and give the query the name in its header. Create `fnLoadCsv` first.
4. Right-click `fnLoadCsv` and untick **Enable load**.
5. Click **Close & Apply**.

## 3. Model
1. Create the relationships listed in [`docs/data-model.md`](../docs/data-model.md). They're all many-to-one with single filter direction.
2. Select the **Date** table, then **Table tools → Mark as date table** using `date`.
3. Sort `Date[month_name]` by `month_num`.
4. Hide all `*_key` and `*_id` columns and the foreign keys in the fact tables.
5. Set formats:
   - `energy_kwh`: thousands separator, 0 decimals
   - `grid_price_eur_per_kwh`: currency, 4 decimals

## 4. Measures
1. **Home → Enter data** creates an empty table; name it **`_Measures`**.
2. Add every measure from [`dax/measures.dax`](dax/measures.dax). Put them in the display folders shown as `[1 Energy]`, `[2 Operations]` and so on.
3. Set formats:
   - percentages as `0.0 %`
   - `kWh/m3` as `0.000`
   - EUR as currency
4. Delete the placeholder column from `_Measures` so it shows as a measure table.

## 5. Theme
Go to **View → Themes → Browse for themes** and pick [`theme/wwtp-energy-theme.json`](theme/wwtp-energy-theme.json). The theme applies colour-blind-safe series colours, status colours and card styling.

## 6. Pages
Set the canvas to 16:9 (1280 × 720). On each page, add a header text box and the **slicers**: Date (between), Plant, Region and Process group. Sync the slicers across all pages (**View → Sync slicers**).

| Page | Visuals |
|---|---|
| **1. Executive Overview** | 6 cards: Total Energy (MWh), Specific Energy (kWh/m3), Energy Self-Sufficiency %, Grid Energy Cost (EUR), CO2 Emissions (tCO2e), Normalised Energy Savings vs PY. Line chart: Specific Energy by `month_name`, legend `year`, constant line = Target. Table: Plant × Specific Energy, Target, Variance vs Target %, Target Status (font colour = *Target Status Colour*). Bar: Process Share % by `process_group` |
| **2. Process Energy** | Stacked column: Total Energy (MWh) by `year_month`, legend `process_group`. Bar: Total Energy by `process_area`. Line: Aeration Energy ÷ COD Removed by `year_month`, legend `plant_name`. Cards: Aeration Share %, Energy per kg COD Removed |
| **3. Plant Benchmarking** | Bar: Specific Energy by `plant_name`, with *Target Specific Energy* as the reference value. Matrix: Plant × kWh/m³, kWh/kg COD, kWh/PE/yr, Self-Sufficiency %. Small multiples line chart: Specific Energy by `year_month`, small multiples = `plant_name` |
| **4. Supply, Cost & Carbon** | Cards: Self-Generated Energy, Self-Sufficiency %, Energy Cost per m3, Avoided Cost from Self-Generation. Stacked column: Energy Supplied by `year_month`, legend `energy_source`. Bar: Self-Sufficiency % by plant (target as reference). Line: CO2 Emissions by `year_month` |

Tips:
- Add **tooltips** showing Specific Energy, Treated Volume and Avg Daily Flow.
- Use **drill-through** from any plant to a plant detail page (optional fifth page).
- Turn on **Edit interactions** so clicking a plant filters every visual on the page.

## 7. Check against Python
Run `python src/kpis.py`. With the full period selected, the cards should match its output, for example 2025 portfolio specific energy **0.401 kWh/m³** and self-sufficiency **38.9 %**.

## 8. Save to the repo
Save as **`powerbi/WWTP-Energy-Performance.pbix`**. Then take screenshots of each page, replace the previews in `docs/screenshots/`, and commit both.

> Tip: **File → Save as → Power BI project (.pbip)** saves the model and report as text files. Those are much easier to review in Git than a binary `.pbix`.
