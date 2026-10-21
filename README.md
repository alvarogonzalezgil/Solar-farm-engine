# FDPlan Solar Engine

Python engine and CLI to size utility-scale solar and battery storage for oil & gas electricity demand. Yield is **location-specific**: clear-sky hourly weather is generated from latitude, longitude, timezone, and elevation, then simulated with **NREL PySAM PVWatts v8**.

## Requirements

- Python 3.10–3.12 (PySAM wheels are platform-specific)
- Windows: [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if `NREL-PySAM` fails to import

## Install

```bash
cd Solar
python -m pip install -e ".[dev]"
```

## Quick start

```bash
fdplan-solar run -i examples/sample_input_uae.json -o out/uae.json --pretty
fdplan-solar run -i examples/sample_input_norway.json -o out/norway.json --pretty
fdplan-solar validate -i examples/sample_input_uae.json
```

Compare `pv_dc_capacity_kw` between UAE and Norway for the same `daily_energy_kwh` — Norway requires more DC capacity under the same sunny-day assumption.

## Input highlights

| Section | Fields |
|---------|--------|
| `site` | `latitude`, `longitude` (required); `timezone_offset_hours`, `elevation_m`; optional `country`, `oil_field_name` |
| `demand` | `daily_energy_kwh` (required) |
| `pv` | `dc_ac_ratio`, `array_type`, `tilt_deg`, `azimuth_deg`, `system_losses_percent` |
| `weather_mode` | `clear_sky` (default) or `capacity_factor` (+ `sunny_day_capacity_factor`) |
| `sizing_mode` | `meet_load` (default) or `fixed_capacity` (+ `fixed_dc_capacity_kw`) |
| `storage` | `storage_hours` or `storage_fraction_of_daily_load`, RTE, DoD |
| `costs` | `pv_cost_usd_per_w_dc`, `storage_cost_usd_per_kwh`, optional LCOE inputs |

## Sunny-day assumption

`clear_sky` builds an 8760-hour SAM CSV from solar geometry and clear-sky DNI/GHI/DHI at the site. This is optimistic (no clouds) by design for v1. Use `capacity_factor` only as a fallback when PySAM is unavailable.

## Output highlights

- `pv_dc_capacity_kw`, `pv_ac_capacity_kw`, `storage_capacity_kwh`, `capex`, optional `lcoe_usd_per_kwh`
- `site_summary`: equivalent peak sun hours and kWh/kWp/day at the site
- `assumptions.warnings`: e.g. inferred timezone

## Tests

```bash
pytest
```

## FDPlan integration

See [fdplan_worker/README.md](fdplan_worker/README.md). Export JSON schemas for data-type registration:

```bash
fdplan-solar export-schemas --out-dir schemas
```

## Project layout

- `src/fdplan_solar/` — engine, schemas, CLI
- `examples/` — sample JSON inputs
- `fdplan_worker/` — phase-2 event worker (poll FDPlan, run same `run_sizing`)
