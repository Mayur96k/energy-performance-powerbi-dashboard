// =====================================================================
//  Power Query (M) — WWTP Energy Performance
//  Create each block below as a separate query in Power BI Desktop
//  (Home → Transform data → New Source → Blank Query → Advanced Editor).
//  Query names must match the comment headers.
// =====================================================================


// ---------------------------------------------------------------------
// Query: DataFolder   (Manage Parameters → New Parameter, type Text)
// Point it at the repo's /data folder on your machine.
// ---------------------------------------------------------------------
"C:\Projects\energy-performance-powerbi-dashboard\data\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]


// ---------------------------------------------------------------------
// Query: fnLoadCsv   (helper function)
// ---------------------------------------------------------------------
(fileName as text) as table =>
let
    Source   = Csv.Document(File.Contents(DataFolder & fileName),
                            [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    Promoted


// ---------------------------------------------------------------------
// Query: Date
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("dim_date.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"date", type date}, {"date_key", Int64.Type}, {"year", Int64.Type},
        {"quarter", type text}, {"month_num", Int64.Type}, {"month_name", type text},
        {"year_month", type text}, {"week_iso", Int64.Type}, {"day_of_week", type text},
        {"is_weekend", type logical}, {"season", type text}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Plant
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("dim_plant.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"plant_code", type text}, {"plant_name", type text}, {"region", type text},
        {"treatment_process", type text}, {"design_capacity_pe", Int64.Type},
        {"design_flow_m3_per_day", Int64.Type}, {"has_anaerobic_digestion", type logical},
        {"solar_pv_kwp", Int64.Type}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Process Area
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("dim_process_area.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"process_area_id", Int64.Type}, {"process_area", type text}, {"process_group", type text}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Energy Source
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("dim_energy_source.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"energy_source_id", Int64.Type}, {"energy_source", type text}, {"source_type", type text},
        {"is_renewable", type logical}, {"co2_factor_kg_per_kwh", type number}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Energy Consumption   (fact, grain: day × plant × process area)
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("fact_energy_consumption.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"date_key", Int64.Type}, {"plant_code", type text},
        {"process_area_id", Int64.Type}, {"energy_kwh", type number}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Energy Supply   (fact, grain: day × plant × energy source)
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("fact_energy_supply.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"date_key", Int64.Type}, {"plant_code", type text},
        {"energy_source_id", Int64.Type}, {"energy_supplied_kwh", type number}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Operations   (fact, grain: day × plant)
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("fact_operations.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"date_key", Int64.Type}, {"plant_code", type text}, {"influent_flow_m3", type number},
        {"rainfall_mm", type number}, {"avg_temperature_c", type number},
        {"cod_load_in_kg", type number}, {"cod_removed_kg", type number},
        {"effluent_cod_mg_l", type number}, {"effluent_nh4_mg_l", type number},
        {"biogas_produced_nm3", type number}, {"sludge_produced_t_ds", type number}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Energy Tariff   (grain: month)
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("fact_energy_tariff.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"year_month", type text}, {"grid_price_eur_per_kwh", type number}}, "en-US")
in
    Typed


// ---------------------------------------------------------------------
// Query: Targets   (grain: year × plant)
// ---------------------------------------------------------------------
let
    Source = fnLoadCsv("fact_targets.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"year", Int64.Type}, {"plant_code", type text},
        {"target_kwh_per_m3", type number}, {"target_self_sufficiency_pct", type number}}, "en-US")
in
    Typed
