"""
Python reference implementation of the dashboard KPIs.

Used to (1) render the dashboard previews, (2) produce the KPI summary in
docs/kpi-summary.md, and (3) cross-check the DAX measures: the numbers
Power BI shows should match these.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load(data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    names = [
        "dim_date", "dim_plant", "dim_process_area", "dim_energy_source",
        "fact_energy_consumption", "fact_energy_supply", "fact_operations",
        "fact_energy_tariff", "fact_targets",
    ]
    t = {n: pd.read_csv(data_dir / f"{n}.csv") for n in names}
    t["dim_date"]["date"] = pd.to_datetime(t["dim_date"]["date"])
    return t


def enriched(t: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Facts joined to the dimensions they need."""
    d = t["dim_date"][["date_key", "date", "year", "month_num", "year_month"]]
    cons = (t["fact_energy_consumption"].merge(d, on="date_key")
            .merge(t["dim_process_area"], on="process_area_id")
            .merge(t["dim_plant"][["plant_code", "plant_name"]], on="plant_code"))
    sup = (t["fact_energy_supply"].merge(d, on="date_key")
           .merge(t["dim_energy_source"], on="energy_source_id")
           .merge(t["fact_energy_tariff"], on="year_month")
           .merge(t["dim_plant"][["plant_code", "plant_name"]], on="plant_code"))
    ops = (t["fact_operations"].merge(d, on="date_key")
           .merge(t["dim_plant"][["plant_code", "plant_name"]], on="plant_code"))
    return cons, sup, ops


def plant_year_kpis(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cons, sup, ops = enriched(t)
    keys = ["plant_code", "plant_name", "year"]
    e = cons.groupby(keys)["energy_kwh"].sum().rename("energy_kwh")
    aer = (cons[cons.process_area_id == 4].groupby(keys)["energy_kwh"].sum().rename("aeration_kwh"))
    v = ops.groupby(keys)[["influent_flow_m3", "cod_removed_kg"]].sum()
    self_gen = (sup[sup.source_type == "Self-generated"].groupby(keys)["energy_supplied_kwh"]
                .sum().rename("self_generated_kwh"))
    grid = sup[sup.energy_source == "Grid Electricity"]
    grid_kwh = grid.groupby(keys)["energy_supplied_kwh"].sum().rename("grid_kwh")
    grid_cost = (grid.assign(c=grid.energy_supplied_kwh * grid.grid_price_eur_per_kwh)
                 .groupby(keys)["c"].sum().rename("grid_cost_eur"))
    co2 = (sup.assign(c=sup.energy_supplied_kwh * sup.co2_factor_kg_per_kwh / 1000)
           .groupby(keys)["c"].sum().rename("co2_t"))
    k = pd.concat([e, aer, v, self_gen, grid_kwh, grid_cost, co2], axis=1).fillna(0).reset_index()
    k = k.merge(t["fact_targets"], on=["plant_code", "year"])
    k["kwh_per_m3"] = k.energy_kwh / k.influent_flow_m3
    k["kwh_per_kg_cod"] = k.energy_kwh / k.cod_removed_kg
    k["self_sufficiency"] = k.self_generated_kwh / k.energy_kwh
    k["aeration_share"] = k.aeration_kwh / k.energy_kwh
    k["variance_vs_target"] = k.kwh_per_m3 / k.target_kwh_per_m3 - 1
    return k


def portfolio_year_kpis(k: pd.DataFrame) -> pd.DataFrame:
    s = k.groupby("year")[["energy_kwh", "influent_flow_m3", "cod_removed_kg", "self_generated_kwh",
                           "grid_kwh", "grid_cost_eur", "co2_t", "aeration_kwh"]].sum()
    s["target_kwh_per_m3"] = (k.assign(w=k.target_kwh_per_m3 * k.influent_flow_m3)
                              .groupby("year")["w"].sum() / s.influent_flow_m3)
    s["kwh_per_m3"] = s.energy_kwh / s.influent_flow_m3
    s["self_sufficiency"] = s.self_generated_kwh / s.energy_kwh
    s["aeration_share"] = s.aeration_kwh / s.energy_kwh
    s["cost_per_m3"] = s.grid_cost_eur / s.influent_flow_m3
    return s


if __name__ == "__main__":
    tables = load()
    k = plant_year_kpis(tables)
    pd.set_option("display.width", 160)
    print(k[["plant_name", "year", "kwh_per_m3", "target_kwh_per_m3", "variance_vs_target",
             "self_sufficiency", "aeration_share"]].round(3).to_string(index=False))
    print()
    print(portfolio_year_kpis(k).round(3).T.to_string())
