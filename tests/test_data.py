"""Data-quality tests for the synthetic dataset (run: pytest -q)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kpis import load, plant_year_kpis, portfolio_year_kpis  # noqa: E402


@pytest.fixture(scope="module")
def t():
    return load()


def test_primary_keys_unique(t):
    assert t["dim_date"]["date_key"].is_unique
    assert t["dim_plant"]["plant_code"].is_unique
    assert t["dim_process_area"]["process_area_id"].is_unique
    assert t["dim_energy_source"]["energy_source_id"].is_unique
    assert not t["fact_energy_consumption"].duplicated(["date_key", "plant_code", "process_area_id"]).any()
    assert not t["fact_energy_supply"].duplicated(["date_key", "plant_code", "energy_source_id"]).any()
    assert not t["fact_operations"].duplicated(["date_key", "plant_code"]).any()


@pytest.mark.parametrize("fact,key,dim", [
    ("fact_energy_consumption", "date_key", "dim_date"),
    ("fact_energy_consumption", "plant_code", "dim_plant"),
    ("fact_energy_consumption", "process_area_id", "dim_process_area"),
    ("fact_energy_supply", "energy_source_id", "dim_energy_source"),
    ("fact_operations", "plant_code", "dim_plant"),
    ("fact_targets", "plant_code", "dim_plant"),
])
def test_referential_integrity(t, fact, key, dim):
    assert set(t[fact][key]) <= set(t[dim][key])


def test_no_negative_or_missing_values(t):
    for name in ["fact_energy_consumption", "fact_energy_supply", "fact_operations"]:
        df = t[name]
        assert not df.isna().any().any(), name
        num = df.select_dtypes("number").drop(columns=["avg_temperature_c"], errors="ignore")  # can be < 0 °C
        assert (num >= 0).all().all(), name


def test_every_month_has_a_tariff(t):
    assert set(t["dim_date"]["year_month"]) == set(t["fact_energy_tariff"]["year_month"])


def test_supply_balances_consumption(t):
    cons = t["fact_energy_consumption"].groupby(["date_key", "plant_code"])["energy_kwh"].sum()
    sup = t["fact_energy_supply"].groupby(["date_key", "plant_code"])["energy_supplied_kwh"].sum()
    # Supply covers demand (surplus self-generation is allowed, shortfall is not)
    assert ((sup - cons.reindex(sup.index)) >= -1.0).all()


def test_kpis_in_realistic_ranges(t):
    k = plant_year_kpis(t)
    assert k.kwh_per_m3.between(0.25, 0.75).all()          # typical municipal WWTP range
    assert k.aeration_share.between(0.45, 0.70).all()      # aeration is the dominant load
    assert k.self_sufficiency.between(0, 0.7).all()
    p = portfolio_year_kpis(k)
    assert isinstance(p, pd.DataFrame) and len(p) >= 1
