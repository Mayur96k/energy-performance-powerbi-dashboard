"""
Render static previews of the four dashboard pages from the sample data.

These PNGs are layout previews for the README (built with matplotlib so the
repo shows the dashboard without opening Power BI). After building the
report in Power BI Desktop, you can replace them with real screenshots.

Usage:  python src/render_previews.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

from kpis import enriched, load, plant_year_kpis, portfolio_year_kpis  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"

# Palette (validated reference palette; categorical slots in fixed order)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, PAGE = "#fcfcfb", "#f9f9f7"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, BORDER = "#e1e0d9", "#c3c2b7", "#e1e0d9"
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
GOOD_TEXT = "#006300"
HEADER = "#0d366b"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.facecolor": SURFACE, "legend.frameon": False, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 10,
})

PLANT_ORDER = ["Riverside WWTP", "Lakeview WWTP", "Greenfield WWTP", "Hillcrest WWTP", "Bayside WWTP"]
PLANT_COLOR = dict(zip(PLANT_ORDER, SERIES))
GROUP_ORDER = ["Biological", "Pumping", "Sludge", "Auxiliary", "Pre-treatment"]
GROUP_COLOR = dict(zip(GROUP_ORDER, SERIES))
SOURCE_COLOR = {"Grid Electricity": SERIES[0], "Biogas CHP": SERIES[1], "Solar PV": SERIES[2]}


# ----------------------------------------------------------------------------
# Page scaffolding
# ----------------------------------------------------------------------------
def page(title: str, subtitle: str, active: int):
    fig = plt.figure(figsize=(16, 9), dpi=110, facecolor=PAGE)
    # header bar
    hdr = fig.add_axes([0, 0.925, 1, 0.075]); hdr.axis("off")
    hdr.add_patch(plt.Rectangle((0, 0), 1, 1, color=HEADER, transform=hdr.transAxes))
    hdr.text(0.012, 0.5, "WWTP Energy Performance", color="white", fontsize=15, weight="bold",
             va="center", transform=hdr.transAxes)
    hdr.text(0.232, 0.5, f"|   {title}", color="#cde2fb", fontsize=13, va="center", transform=hdr.transAxes)
    tabs = ["Executive Overview", "Process Energy", "Plant Benchmarking", "Supply, Cost & Carbon"]
    x = 0.555
    for i, tname in enumerate(tabs, 1):
        hdr.text(x, 0.5, tname, color="white" if i == active else "#9ec5f4", fontsize=9.5,
                 weight="bold" if i == active else "normal", va="center", transform=hdr.transAxes)
        if i == active:
            hdr.plot([x, x + len(tname) * 0.0052], [0.12, 0.12], color="white", lw=2.5, transform=hdr.transAxes)
        x += len(tname) * 0.0052 + 0.02
    # slicer row
    sl = fig.add_axes([0, 0.875, 1, 0.045]); sl.axis("off")
    for i, (lab, val) in enumerate([("Period", "Jan 2024 – Dec 2025"), ("Plant", "All plants (5)"),
                                    ("Region", "All"), ("Process", "All")]):
        x0 = 0.012 + i * 0.16
        sl.add_patch(plt.Rectangle((x0, 0.12), 0.15, 0.76, facecolor=SURFACE, edgecolor=BORDER,
                                   transform=sl.transAxes))
        sl.text(x0 + 0.006, 0.5, f"{lab}:", color=MUTED, fontsize=8.5, va="center", transform=sl.transAxes)
        sl.text(x0 + 0.045, 0.5, val, color=INK, fontsize=8.5, va="center", transform=sl.transAxes)
        sl.text(x0 + 0.141, 0.5, "▾", color=MUTED, fontsize=8, va="center", transform=sl.transAxes)
    sl.text(0.988, 0.5, subtitle, color=MUTED, fontsize=8, ha="right", va="center", transform=sl.transAxes)
    fig.text(0.988, 0.008, "Synthetic sample data · fictional plants · layout preview",
             color=MUTED, fontsize=7.5, ha="right")
    return fig


def card(fig, rect):
    """Background card behind a visual."""
    bg = fig.add_axes(rect, zorder=0); bg.axis("off")
    bg.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=SURFACE, edgecolor=BORDER, lw=1, transform=bg.transAxes))


def kpi(fig, rect, label, value, delta=None, delta_good=None, note=None):
    card(fig, rect)
    ax = fig.add_axes(rect, zorder=1); ax.axis("off")
    ax.text(0.07, 0.78, label, color=INK2, fontsize=9, transform=ax.transAxes)
    ax.text(0.07, 0.40, value, color=INK, fontsize=21, weight="bold", transform=ax.transAxes)
    if delta:
        col = GOOD_TEXT if delta_good else CRIT
        icon = "▼" if delta.startswith("-") else "▲"
        ax.text(0.07, 0.13, f"{icon} {delta.lstrip('+-')}", color=col, fontsize=8.5, weight="bold",
                transform=ax.transAxes)
        if note:
            char = 0.072 / (rect[2] * 16)
            ax.text(0.07 + char * (len(delta.lstrip('+-')) + 3), 0.13, note, color=MUTED, fontsize=8, transform=ax.transAxes)
    elif note:
        ax.text(0.07, 0.13, note, color=MUTED, fontsize=8, transform=ax.transAxes)


def visual(fig, rect, title, subtitle=None, left=0.045):
    card(fig, rect)
    l, b, w, h = rect
    ax = fig.add_axes([l + left, b + 0.06, w - left - 0.02, h - 0.15], zorder=1)
    fig.text(l + 0.01, b + h - 0.032, title, fontsize=10.5, weight="bold", color=INK)
    if subtitle:
        fig.text(l + 0.01, b + h - 0.055, subtitle, fontsize=8, color=MUTED)
    return ax


def fmt_month(ax, months):
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels([m[2:].replace("-", "/") if i % 3 == 0 else "" for i, m in enumerate(months)], fontsize=8)
    ax.tick_params(length=0)
    ax.margins(x=0.01)


def legend_row(ax, items, y=1.02):
    handles = [plt.Line2D([], [], marker="s", ls="", color=c, markersize=8) for _, c in items]
    ax.legend(handles, [n for n, _ in items], loc="lower left", bbox_to_anchor=(0, y), ncol=len(items),
              fontsize=8, handletextpad=0.3, columnspacing=1.2, borderaxespad=0)


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page1(t, k, p, cons, sup, ops):
    fig = page("Executive Overview", "Data to 31 Dec 2025", 1)
    y25, y24 = p.loc[2025], p.loc[2024]
    savings = (y24.kwh_per_m3 - y25.kwh_per_m3) * y25.influent_flow_m3
    tiles = [
        ("Total energy 2025", f"{y25.energy_kwh/1e6:.1f} GWh", f"{(y25.energy_kwh/y24.energy_kwh-1)*100:+.1f}%", True, "vs 2024"),
        ("Specific energy", f"{y25.kwh_per_m3:.3f} kWh/m³", f"+{(y25.kwh_per_m3/y25.target_kwh_per_m3-1)*100:.1f}%", False, f"vs target {y25.target_kwh_per_m3:.3f}"),
        ("Energy self-sufficiency", f"{y25.self_sufficiency*100:.1f} %", f"+{(y25.self_sufficiency-y24.self_sufficiency)*100:.1f} pts", True, "vs 2024"),
        ("Grid energy cost", f"€{y25.grid_cost_eur/1e6:.2f} M", f"{(y25.grid_cost_eur/y24.grid_cost_eur-1)*100:+.1f}%", True, "vs 2024"),
        ("Carbon (scope 2)", f"{y25.co2_t:,.0f} tCO₂e", f"{(y25.co2_t/y24.co2_t-1)*100:+.1f}%", True, "vs 2024"),
        ("Normalised savings", f"{savings/1e3:,.0f} MWh", None, None, "volume-adjusted vs 2024"),
    ]
    for i, (lab, val, d, g, n) in enumerate(tiles):
        kpi(fig, [0.012 + i * 0.1635, 0.715, 0.155, 0.145], lab, val, d, g, n)

    # Monthly specific energy, portfolio, 2024 vs 2025 + target reference
    ax = visual(fig, [0.012, 0.045, 0.56, 0.655], "Specific energy by month",
                "kWh per m³ treated · all plants · dashed line = 2025 target · lower in wet months (higher flow)")
    e = cons.groupby(["year", "month_num"]).energy_kwh.sum()
    v = ops.groupby(["year", "month_num"]).influent_flow_m3.sum()
    se = (e / v).unstack(0)
    months = range(1, 13)
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for yr, col in [(2024, SERIES[0]), (2025, SERIES[1])]:
        ax.plot(list(months), se[yr].values, color=col, lw=2, marker="o", markersize=4.5,
                markeredgecolor=SURFACE, markeredgewidth=1.2)
        ax.text(12.15, se[yr].values[-1], str(yr), color=INK2, fontsize=8.5, va="center", weight="bold")
    ax.axhline(y25.target_kwh_per_m3, color=MUTED, lw=1.2, ls=(0, (4, 3)))
    ax.text(1, y25.target_kwh_per_m3 + 0.002, f"Target {y25.target_kwh_per_m3:.3f}", color=INK2, fontsize=8)
    ax.set_xticks(list(months)); ax.set_xticklabels(names, fontsize=8.5); ax.tick_params(length=0)
    ax.set_xlim(0.6, 12.8)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))
    legend_row(ax, [("2024", SERIES[0]), ("2025", SERIES[1])])
    # Plant status table
    ax2 = visual(fig, [0.582, 0.385, 0.406, 0.315], "Plant performance 2025", "Specific energy vs annual target")
    ax2.axis("off")
    k25 = k[k.year == 2025].set_index("plant_name").loc[PLANT_ORDER]
    cols = [("Plant", 0.0), ("kWh/m³", 0.36), ("Target", 0.52), ("Variance", 0.67), ("Status", 0.83)]
    for c, x in cols:
        ax2.text(x, 0.98, c, fontsize=8, color=MUTED, weight="bold", transform=ax2.transAxes, va="top")
    ax2.plot([0, 1], [0.86, 0.86], color=GRID, lw=1, transform=ax2.transAxes)
    for i, (name, r) in enumerate(k25.iterrows()):
        y = 0.74 - i * 0.165
        var = r.variance_vs_target
        status, col = (("✔ On target", GOOD) if var <= 0 else ("▲ Within 5%", WARN) if var <= 0.05 else ("✖ Above", CRIT))
        ax2.add_patch(plt.Rectangle((0, y - 0.035), 0.012, 0.07, color=PLANT_COLOR[name], transform=ax2.transAxes))
        ax2.text(0.025, y, name, fontsize=9, va="center", transform=ax2.transAxes)
        ax2.text(0.36, y, f"{r.kwh_per_m3:.3f}", fontsize=9, va="center", transform=ax2.transAxes)
        ax2.text(0.52, y, f"{r.target_kwh_per_m3:.3f}", fontsize=9, va="center", color=INK2, transform=ax2.transAxes)
        ax2.text(0.67, y, f"{var*100:+.1f}%", fontsize=9, va="center", transform=ax2.transAxes,
                 color=GOOD_TEXT if var <= 0 else INK)
        ax2.text(0.83, y, status, fontsize=8.5, va="center", color=col if col != WARN else "#8a5c00",
                 weight="bold", transform=ax2.transAxes)

    # Energy by process group (horizontal bars)
    ax3 = visual(fig, [0.582, 0.045, 0.406, 0.325], "Where the energy goes (2025)", "Share of consumption by process group", left=0.075)
    g = cons[cons.year == 2025].groupby("process_group").energy_kwh.sum().reindex(GROUP_ORDER)
    share = g / g.sum()
    yy = range(len(share))[::-1]
    ax3.barh(list(yy), share.values, color=SERIES[0], height=0.55)
    for yv, (n, s) in zip(yy, share.items()):
        ax3.text(s + 0.008, yv, f"{s*100:.0f}%", va="center", fontsize=8.5, color=INK)
    ax3.set_yticks(list(yy)); ax3.set_yticklabels(share.index, fontsize=8.5, color=INK2)
    ax3.grid(False); ax3.set_xticks([]); ax3.tick_params(length=0); ax3.set_xlim(0, 0.68)
    ax3.spines["bottom"].set_visible(False)
    return fig


def page2(t, k, p, cons, sup, ops):
    fig = page("Process Energy", "Biological treatment drives >50 % of demand", 2)
    months = sorted(cons.year_month.unique())
    m = cons.groupby(["year_month", "process_group"]).energy_kwh.sum().unstack()[GROUP_ORDER] / 1e6
    ax = visual(fig, [0.012, 0.36, 0.62, 0.50], "Monthly consumption by process group", "GWh · all plants")
    bottom = None
    x = range(len(months))
    for gname in GROUP_ORDER:
        ax.bar(x, m[gname].values, bottom=bottom, color=GROUP_COLOR[gname], width=0.72,
               edgecolor=SURFACE, linewidth=1.5)
        bottom = m[gname].values if bottom is None else bottom + m[gname].values
    fmt_month(ax, months)
    legend_row(ax, [(g, GROUP_COLOR[g]) for g in GROUP_ORDER])

    # Process area ranking 2025
    ax2 = visual(fig, [0.642, 0.36, 0.346, 0.50], "Process areas ranked (2025)", "MWh and share of total", left=0.135)
    a = cons[cons.year == 2025].groupby(["process_area", "process_group"]).energy_kwh.sum().reset_index()
    a = a.sort_values("energy_kwh")
    tot = a.energy_kwh.sum()
    ax2.barh(range(len(a)), a.energy_kwh / 1e3, color=[GROUP_COLOR[g] for g in a.process_group], height=0.6)
    for i, r in enumerate(a.itertuples()):
        ax2.text(r.energy_kwh / 1e3 + 150, i, f"{r.energy_kwh/1e3:,.0f}  ({r.energy_kwh/tot*100:.0f}%)",
                 va="center", fontsize=8, color=INK)
    ax2.set_yticks(range(len(a))); ax2.set_yticklabels(a.process_area, fontsize=8, color=INK2)
    ax2.grid(False); ax2.set_xticks([]); ax2.tick_params(length=0)
    ax2.set_xlim(0, a.energy_kwh.max() / 1e3 * 1.45)

    # Aeration intensity per plant (small multiples)
    ax3 = visual(fig, [0.012, 0.045, 0.62, 0.30], "Aeration energy per kg COD removed",
                 "kWh/kg · monthly · per plant")
    aer = cons[cons.process_area_id == 4].groupby(["plant_name", "year_month"]).energy_kwh.sum()
    cod = ops.groupby(["plant_name", "year_month"]).cod_removed_kg.sum()
    r = (aer / cod).unstack(0)[PLANT_ORDER]
    for pn in PLANT_ORDER:
        ax3.plot(range(len(months)), r[pn].values, color=PLANT_COLOR[pn], lw=2)
    fmt_month(ax3, months)
    legend_row(ax3, [(p_, PLANT_COLOR[p_]) for p_ in PLANT_ORDER])
    i_f = months.index("2025-02")
    ax3.annotate("Hillcrest: diffuser fouling\nFeb–Apr 2025", xy=(i_f + 1, r["Hillcrest WWTP"].values[i_f + 1]),
                 xytext=(i_f - 7, r["Hillcrest WWTP"].values[i_f + 1] + 0.02), fontsize=7.5, color=INK2,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    kpi(fig, [0.642, 0.20, 0.17, 0.145], "Aeration share 2025", f"{p.loc[2025].aeration_share*100:.1f} %",
        f"-{(p.loc[2024].aeration_share-p.loc[2025].aeration_share)*100:.1f} pts", True, "vs 2024")
    kpi(fig, [0.818, 0.20, 0.17, 0.145], "Energy per kg COD",
        f"{p.loc[2025].energy_kwh/p.loc[2025].cod_removed_kg:.3f} kWh",
        f"{((p.loc[2025].energy_kwh/p.loc[2025].cod_removed_kg)/(p.loc[2024].energy_kwh/p.loc[2024].cod_removed_kg)-1)*100:+.1f}%", True, "vs 2024")
    card(fig, [0.642, 0.045, 0.346, 0.145])
    fig.text(0.652, 0.155, "Insight", fontsize=9.5, weight="bold", color=INK)
    fig.text(0.652, 0.075, "Blower upgrades at Riverside and Bayside (Jul 2025)\ncut aeration energy by ~12 %. "
             "Hillcrest's diffuser\nfouling added ~22 % to aeration for three months.", fontsize=8.5, color=INK2)
    return fig


def page3(t, k, p, cons, sup, ops):
    fig = page("Plant Benchmarking", "Volume-weighted targets per plant and year", 3)
    k25 = k[k.year == 2025].set_index("plant_name").loc[PLANT_ORDER]
    ax = visual(fig, [0.012, 0.45, 0.42, 0.41], "Specific energy vs target (2025)", "kWh/m³ · tick = target", left=0.085)
    order = k25.sort_values("kwh_per_m3").index
    yy = range(len(order))
    ax.barh(list(yy), k25.loc[order].kwh_per_m3, color=[PLANT_COLOR[n] for n in order], height=0.55)
    for yv, n in zip(yy, order):
        r = k25.loc[n]
        ax.plot([r.target_kwh_per_m3] * 2, [yv - 0.38, yv + 0.38], color=INK, lw=2)
        ax.text(max(r.kwh_per_m3, r.target_kwh_per_m3) + 0.01, yv,
                f"{r.kwh_per_m3:.3f}  ({r.variance_vs_target*100:+.1f}%)", va="center", fontsize=8.5)
    ax.set_yticks(list(yy)); ax.set_yticklabels(order, fontsize=8.5, color=INK2)
    ax.grid(False); ax.set_xticks([]); ax.tick_params(length=0); ax.set_xlim(0, 0.8)

    # Plant comparison matrix
    ax2 = visual(fig, [0.442, 0.45, 0.546, 0.41], "Plant comparison (2025)", "Key efficiency indicators")
    ax2.axis("off")
    plant = t["dim_plant"].set_index("plant_name")
    cols = [("Plant", 0.0), ("Process", 0.19), ("Design PE", 0.47), ("kWh/m³", 0.59), ("kWh/kg COD", 0.70),
            ("kWh/PE/yr", 0.82), ("Self-suff.", 0.92)]
    for c, x in cols:
        ax2.text(x, 0.98, c, fontsize=8, color=MUTED, weight="bold", transform=ax2.transAxes, va="top")
    ax2.plot([0, 1], [0.87, 0.87], color=GRID, lw=1, transform=ax2.transAxes)
    for i, n in enumerate(PLANT_ORDER):
        r, pl = k25.loc[n], plant.loc[n]
        y = 0.76 - i * 0.16
        proc = pl.treatment_process.replace("Activated sludge", "AS").replace("anaerobic digestion", "AD")
        vals = [n, proc[:26], f"{pl.design_capacity_pe:,}", f"{r.kwh_per_m3:.3f}", f"{r.kwh_per_kg_cod:.3f}",
                f"{r.energy_kwh/pl.design_capacity_pe:.1f}", f"{r.self_sufficiency*100:.0f}%"]
        for (c, x), v in zip(cols, vals):
            ax2.text(x, y, v, fontsize=8.5, va="center", transform=ax2.transAxes, color=INK if c != "Process" else INK2)

    # Monthly trend small multiples per plant
    months = sorted(cons.year_month.unique())
    e = cons.groupby(["plant_name", "year_month"]).energy_kwh.sum()
    v = ops.groupby(["plant_name", "year_month"]).influent_flow_m3.sum()
    se = (e / v).unstack(0)
    tg = t["fact_targets"].merge(t["dim_plant"][["plant_code", "plant_name"]], on="plant_code")
    card(fig, [0.012, 0.045, 0.976, 0.39])
    fig.text(0.022, 0.40, "Monthly specific energy by plant", fontsize=10.5, weight="bold")
    fig.text(0.022, 0.378, "kWh/m³ · dashed = target · shared y-axis", fontsize=8, color=MUTED)
    ymin, ymax = se.min().min() * 0.9, se.max().max() * 1.05
    for i, n in enumerate(PLANT_ORDER):
        ax3 = fig.add_axes([0.035 + i * 0.192, 0.085, 0.165, 0.26], zorder=1)
        ax3.plot(range(len(months)), se[n].values, color=PLANT_COLOR[n], lw=2)
        for yr in (2024, 2025):
            tv = tg[(tg.plant_name == n) & (tg.year == yr)].target_kwh_per_m3.iloc[0]
            idx = [j for j, mm in enumerate(months) if mm.startswith(str(yr))]
            ax3.plot([idx[0], idx[-1]], [tv, tv], color=MUTED, lw=1.1, ls=(0, (4, 3)))
        ax3.set_ylim(ymin, ymax)
        ax3.set_title(n, fontsize=9, color=INK, pad=4)
        ax3.set_xticks([0, 12]); ax3.set_xticklabels(["2024", "2025"], fontsize=8); ax3.tick_params(length=0)
        if i:
            ax3.set_yticklabels([])
        else:
            ax3.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))
    return fig


def page4(t, k, p, cons, sup, ops):
    fig = page("Supply, Cost & Carbon", "Grid price: monthly average tariff", 4)
    y25, y24 = p.loc[2025], p.loc[2024]
    kp = [
        ("Self-generated 2025", f"{y25.self_generated_kwh/1e6:.1f} GWh", f"+{(y25.self_generated_kwh/y24.self_generated_kwh-1)*100:.1f}%", True, "vs 2024"),
        ("Self-sufficiency", f"{y25.self_sufficiency*100:.1f} %", f"+{(y25.self_sufficiency-y24.self_sufficiency)*100:.1f} pts", True, "vs 2024"),
        ("Grid cost per m³", f"€{y25.cost_per_m3:.4f}", f"{(y25.cost_per_m3/y24.cost_per_m3-1)*100:+.1f}%", True, "vs 2024"),
        ("Avoided cost (self-gen.)", f"€{(sup[(sup.year==2025)&(sup.source_type=='Self-generated')].eval('energy_supplied_kwh*grid_price_eur_per_kwh').sum())/1e6:.2f} M", None, None, "at grid tariff"),
    ]
    for i, (lab, val, d, g, n) in enumerate(kp):
        kpi(fig, [0.012 + i * 0.2465, 0.715, 0.238, 0.145], lab, val, d, g, n)

    months = sorted(sup.year_month.unique())
    m = sup.groupby(["year_month", "energy_source"]).energy_supplied_kwh.sum().unstack()[list(SOURCE_COLOR)] / 1e6
    ax = visual(fig, [0.012, 0.045, 0.56, 0.655], "Energy supply mix by month", "GWh · grid import vs on-site generation")
    bottom = None
    for s, col in SOURCE_COLOR.items():
        ax.bar(range(len(months)), m[s].values, bottom=bottom, color=col, width=0.72, edgecolor=SURFACE, linewidth=1.5)
        bottom = m[s].values if bottom is None else bottom + m[s].values
    fmt_month(ax, months)
    legend_row(ax, list(SOURCE_COLOR.items()))
    io = months.index("2024-10")
    ax.annotate("Lakeview CHP overhaul\n(3 weeks, Oct 2024)", xy=(io, bottom[io]), xytext=(io - 6.5, bottom[io] + 0.12),
                fontsize=7.5, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_ylim(0, bottom.max() * 1.18)

    ax2 = visual(fig, [0.582, 0.385, 0.406, 0.315], "Self-sufficiency by plant (2025)", "% of demand met on site · tick = target", left=0.085)
    k25 = k[k.year == 2025].set_index("plant_name").loc[PLANT_ORDER]
    order = k25.sort_values("self_sufficiency").index
    ax2.barh(range(len(order)), k25.loc[order].self_sufficiency, color=[PLANT_COLOR[n] for n in order], height=0.55)
    for i, n in enumerate(order):
        r = k25.loc[n]
        ax2.plot([r.target_self_sufficiency_pct] * 2, [i - 0.38, i + 0.38], color=INK, lw=2)
        ax2.text(max(r.self_sufficiency, r.target_self_sufficiency_pct) + 0.012, i, f"{r.self_sufficiency*100:.0f}%",
                 va="center", fontsize=8.5)
    ax2.set_yticks(range(len(order))); ax2.set_yticklabels(order, fontsize=8.5, color=INK2)
    ax2.grid(False); ax2.set_xticks([]); ax2.tick_params(length=0); ax2.set_xlim(0, 0.7)

    ax3 = visual(fig, [0.582, 0.045, 0.406, 0.325], "Scope 2 emissions by month", "tCO₂e · grid electricity")
    c = sup.assign(c=sup.energy_supplied_kwh * sup.co2_factor_kg_per_kwh / 1000).groupby("year_month").c.sum()
    ax3.plot(range(len(months)), c.values, color=SERIES[0], lw=2)
    ax3.fill_between(range(len(months)), c.values, color=SERIES[0], alpha=0.08)
    fmt_month(ax3, months)
    ax3.set_ylim(0, c.max() * 1.2)
    return fig


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = load()
    k = plant_year_kpis(t)
    p = portfolio_year_kpis(k)
    cons, sup, ops = enriched(t)
    for i, fn in enumerate([page1, page2, page3, page4], 1):
        fig = fn(t, k, p, cons, sup, ops)
        name = ["01-executive-overview", "02-process-energy", "03-plant-benchmarking", "04-supply-cost-carbon"][i - 1]
        fig.savefig(OUT / f"{name}.png", facecolor=PAGE)
        plt.close(fig)
        print(f"  wrote docs/screenshots/{name}.png")


if __name__ == "__main__":
    main()
