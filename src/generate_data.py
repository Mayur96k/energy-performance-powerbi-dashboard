"""
Generate a synthetic dataset for the Wastewater Treatment Plant (WWTP)
Energy Performance dashboard.

All plants, figures and events are FICTIONAL. The values follow typical
industry ranges for municipal activated-sludge plants, so the
dashboard behaves realistically without using any real operational data.

Output: a star schema of CSV files in ./data
    dim_date.csv, dim_plant.csv, dim_process_area.csv, dim_energy_source.csv
    fact_energy_consumption.csv, fact_energy_supply.csv,
    fact_operations.csv, fact_energy_tariff.csv, fact_targets.csv

Usage:
    python src/generate_data.py                  # default 2024-01-01 .. 2025-12-31
    python src/generate_data.py --seed 7 --start 2023-01-01 --end 2025-12-31
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# --------------------------------------------------------------------------
# Reference data (fictional)
# --------------------------------------------------------------------------
PLANTS = [
    # code, name, region, process, design PE, design flow m3/d, has AD/CHP, PV kWp, efficiency factor
    ("WWTP01", "Riverside WWTP", "North", "Activated sludge + anaerobic digestion", 450_000, 95_000, True, 600, 0.95),
    ("WWTP02", "Lakeview WWTP", "East", "Activated sludge + anaerobic digestion", 280_000, 60_000, True, 350, 1.02),
    ("WWTP03", "Greenfield WWTP", "South", "Membrane bioreactor (MBR)", 120_000, 26_000, False, 250, 1.35),
    ("WWTP04", "Hillcrest WWTP", "West", "Activated sludge (extended aeration)", 75_000, 16_000, False, 0, 1.18),
    ("WWTP05", "Bayside WWTP", "Coastal", "Activated sludge + anaerobic digestion", 190_000, 42_000, True, 400, 1.08),
]

# Share of electricity per process area for a typical activated-sludge plant
PROCESS_AREAS = [
    # id, name, group, base share
    (1, "Inlet Pumping", "Pumping", 0.12),
    (2, "Preliminary Treatment", "Pre-treatment", 0.04),
    (3, "Primary Treatment", "Pre-treatment", 0.03),
    (4, "Biological Treatment (Aeration)", "Biological", 0.55),
    (5, "Secondary Clarification & RAS", "Biological", 0.07),
    (6, "Sludge Treatment & Dewatering", "Sludge", 0.10),
    (7, "Odour Control", "Auxiliary", 0.03),
    (8, "Buildings & Auxiliaries", "Auxiliary", 0.06),
]

ENERGY_SOURCES = [
    # id, name, type, renewable, CO2 factor kgCO2e/kWh (illustrative)
    (1, "Grid Electricity", "Imported", False, 0.052),
    (2, "Biogas CHP", "Self-generated", True, 0.0),
    (3, "Solar PV", "Self-generated", True, 0.0),
]

TARIFF_BASE_EUR_PER_KWH = 0.165  # illustrative average industrial price


def build_dim_date(start: str, end: str) -> pd.DataFrame:
    d = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "date": d.date,
            "date_key": d.strftime("%Y%m%d").astype(int),
            "year": d.year,
            "quarter": "Q" + d.quarter.astype(str),
            "month_num": d.month,
            "month_name": d.strftime("%b"),
            "year_month": d.strftime("%Y-%m"),
            "week_iso": d.isocalendar().week.values.astype(int),
            "day_of_week": d.strftime("%a"),
            "is_weekend": d.dayofweek >= 5,
            "season": np.select(
                [d.month.isin([12, 1, 2]), d.month.isin([3, 4, 5]), d.month.isin([6, 7, 8])],
                ["Winter", "Spring", "Summer"],
                "Autumn",
            ),
        }
    )


def build_dims() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dim_plant = pd.DataFrame(
        PLANTS,
        columns=[
            "plant_code", "plant_name", "region", "treatment_process",
            "design_capacity_pe", "design_flow_m3_per_day", "has_anaerobic_digestion",
            "solar_pv_kwp", "_eff",
        ],
    ).drop(columns="_eff")
    dim_process = pd.DataFrame(
        PROCESS_AREAS, columns=["process_area_id", "process_area", "process_group", "_share"]
    ).drop(columns="_share")
    dim_source = pd.DataFrame(
        ENERGY_SOURCES,
        columns=["energy_source_id", "energy_source", "source_type", "is_renewable", "co2_factor_kg_per_kwh"],
    )
    return dim_plant, dim_process, dim_source


def simulate(dim_date: pd.DataFrame, rng: np.random.Generator):
    dates = pd.to_datetime(dim_date["date"])
    n = len(dates)
    doy = dates.dt.dayofyear.values
    t = np.arange(n)

    # Shared weather signal: wetter winters, occasional storm events
    seasonal_rain = 2.2 + 1.6 * np.cos(2 * np.pi * (doy - 15) / 365)
    temp_c = 12.5 - 8.5 * np.cos(2 * np.pi * (doy - 20) / 365) + rng.normal(0, 1.8, n)

    ops_rows, cons_rows, gen_rows = [], [], []

    for (code, _name, _reg, process, pe, q_design, has_ad, pv_kwp, eff) in PLANTS:
        rain = rng.gamma(0.55, seasonal_rain / 0.55, n)
        storms = rng.random(n) < 0.012
        rain[storms] += rng.uniform(25, 50, storms.sum())

        # Influent flow: dry-weather flow + rainfall-driven infiltration (with 1-day lag)
        dwf = q_design * 0.72 * (1 + 0.03 * (dates.dt.dayofweek < 5).astype(float).values)
        rain_effect = np.convolve(rain, [0.55, 0.30, 0.15], mode="full")[:n]
        flow = dwf * (1 + 0.022 * rain_effect) * rng.normal(1, 0.04, n)
        flow = np.minimum(flow, q_design * 1.9)

        # Pollutant load is fairly stable; dilution during rain
        cod_load_in = pe * 0.12 * rng.normal(1, 0.06, n)  # kg COD/day (≈120 g/PE/day)
        cod_removed = cod_load_in * np.clip(rng.normal(0.93, 0.015, n), 0.85, 0.97)
        effluent_cod = (cod_load_in - cod_removed) / flow * 1000  # mg/L
        nh4_eff = np.clip(rng.gamma(2.0, 0.6, n) + np.where(temp_c < 8, 1.2, 0), 0.1, None)

        # Electricity demand: driven by load (aeration) and flow (pumping)
        base_kwh_per_m3 = 0.38 * eff
        aeration_temp = 1 + 0.010 * (temp_c - 12)  # warmer water → lower O2 solubility → more air
        load_factor = cod_removed / cod_removed.mean()
        flow_factor = flow / flow.mean()

        # Efficiency programme: blower upgrade at Riverside and Bayside from July 2025
        improvement = np.ones(n)
        if code in ("WWTP01", "WWTP05"):
            improvement[dates >= "2025-07-01"] = 0.88
        # Unplanned issue: diffuser fouling at Hillcrest, Feb–Apr 2025
        fouling = np.ones(n)
        if code == "WWTP04":
            m = (dates >= "2025-02-01") & (dates < "2025-05-01")
            fouling[m] = 1.22

        total_ref = flow.mean() * base_kwh_per_m3
        biogas_nm3 = np.zeros(n)
        sludge_tds = cod_removed * 0.00035 * rng.normal(1, 0.05, n)  # tonnes dry solids

        for (pa_id, _pa, _grp, share) in PROCESS_AREAS:
            if pa_id == 4:
                driver = load_factor * aeration_temp * improvement * fouling
            elif pa_id in (1, 5):
                driver = flow_factor
            elif pa_id == 6:
                driver = sludge_tds / sludge_tds.mean()
            else:
                driver = np.ones(n)
            share_adj = share * (1.25 if (process.startswith("Membrane") and pa_id == 4) else 1.0)
            kwh = total_ref * share_adj * driver * rng.normal(1, 0.035, n)
            cons_rows.append(
                pd.DataFrame(
                    {"date_key": dim_date["date_key"], "plant_code": code,
                     "process_area_id": pa_id, "energy_kwh": kwh.round(1)}
                )
            )

        # Generation: biogas CHP (plants with digestion) and solar PV
        if has_ad:
            biogas_nm3 = cod_removed * 0.11 * rng.normal(1, 0.06, n)  # Nm3/day (≈0.11 Nm3 per kg COD removed)
            chp_avail = np.where(rng.random(n) < 0.03, rng.uniform(0, 0.4, n), 1.0)  # outages
            if code == "WWTP02":  # planned CHP overhaul, Oct 2024
                chp_avail[(dates >= "2024-10-07") & (dates < "2024-10-28")] = 0.0
            chp_kwh = biogas_nm3 * 6.0 * 0.38 * chp_avail  # 6 kWh/Nm3 × 38 % electrical efficiency
            gen_rows.append(pd.DataFrame({"date_key": dim_date["date_key"], "plant_code": code,
                                          "energy_source_id": 2, "energy_kwh": chp_kwh.round(1)}))
        if pv_kwp:
            sun = np.clip(2.6 + 2.1 * np.cos(2 * np.pi * (doy - 172) / 365) - 0.08 * rain, 0.2, None)
            pv_kwh = pv_kwp * sun * rng.normal(1, 0.12, n)
            gen_rows.append(pd.DataFrame({"date_key": dim_date["date_key"], "plant_code": code,
                                          "energy_source_id": 3, "energy_kwh": np.clip(pv_kwh, 0, None).round(1)}))

        ops_rows.append(
            pd.DataFrame(
                {
                    "date_key": dim_date["date_key"],
                    "plant_code": code,
                    "influent_flow_m3": flow.round(0),
                    "rainfall_mm": rain.round(1),
                    "avg_temperature_c": temp_c.round(1),
                    "cod_load_in_kg": cod_load_in.round(0),
                    "cod_removed_kg": cod_removed.round(0),
                    "effluent_cod_mg_l": effluent_cod.round(1),
                    "effluent_nh4_mg_l": nh4_eff.round(2),
                    "biogas_produced_nm3": biogas_nm3.round(0),
                    "sludge_produced_t_ds": sludge_tds.round(2),
                }
            )
        )

    fact_cons = pd.concat(cons_rows, ignore_index=True)
    fact_gen = pd.concat(gen_rows, ignore_index=True)
    fact_ops = pd.concat(ops_rows, ignore_index=True)

    # Grid import = consumption − self-generation (never negative; surplus exported is ignored)
    cons_day = fact_cons.groupby(["date_key", "plant_code"])["energy_kwh"].sum()
    gen_day = fact_gen.groupby(["date_key", "plant_code"])["energy_kwh"].sum().reindex(cons_day.index, fill_value=0)
    grid = (cons_day - gen_day).clip(lower=0).round(1).rename("energy_kwh").reset_index()
    grid["energy_source_id"] = 1
    fact_gen = pd.concat([fact_gen, grid[fact_gen.columns]], ignore_index=True)
    fact_gen = fact_gen.rename(columns={"energy_kwh": "energy_supplied_kwh"})
    fact_gen = fact_gen.sort_values(["date_key", "plant_code", "energy_source_id"]).reset_index(drop=True)
    return fact_cons, fact_gen, fact_ops


def build_tariff(dim_date: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    months = sorted(dim_date["year_month"].unique())
    rows = []
    for i, ym in enumerate(months):
        price = TARIFF_BASE_EUR_PER_KWH * (1 + 0.06 * np.sin(i / 2.2)) * (1 - 0.004 * i) * rng.normal(1, 0.02)
        rows.append({"year_month": ym, "grid_price_eur_per_kwh": round(price, 4)})
    return pd.DataFrame(rows)


def build_targets(dim_date: pd.DataFrame) -> pd.DataFrame:
    # Annual specific-energy target per plant (kWh per m3 treated) and self-sufficiency target
    targets = {
        "WWTP01": (0.36, 0.45), "WWTP02": (0.39, 0.40), "WWTP03": (0.52, 0.05),
        "WWTP04": (0.45, 0.00), "WWTP05": (0.40, 0.38),
    }
    rows = []
    for year in sorted(dim_date["year"].unique()):
        tighten = 1 - 0.03 * (year - dim_date["year"].min())
        for code, (kwh_m3, ss) in targets.items():
            rows.append({"year": int(year), "plant_code": code,
                         "target_kwh_per_m3": round(kwh_m3 * tighten, 3),
                         "target_self_sufficiency_pct": ss})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=DATA_DIR)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)

    dim_date = build_dim_date(args.start, args.end)
    dim_plant, dim_process, dim_source = build_dims()
    fact_cons, fact_gen, fact_ops = simulate(dim_date, rng)
    tariff = build_tariff(dim_date, rng)
    targets = build_targets(dim_date)

    outputs = {
        "dim_date": dim_date, "dim_plant": dim_plant, "dim_process_area": dim_process,
        "dim_energy_source": dim_source, "fact_energy_consumption": fact_cons,
        "fact_energy_supply": fact_gen, "fact_operations": fact_ops,
        "fact_energy_tariff": tariff, "fact_targets": targets,
    }
    for name, df in outputs.items():
        df.to_csv(args.out / f"{name}.csv", index=False)
        print(f"  {name:<26} {len(df):>7,} rows")
    print(f"Synthetic data written to {args.out}")


if __name__ == "__main__":
    main()
