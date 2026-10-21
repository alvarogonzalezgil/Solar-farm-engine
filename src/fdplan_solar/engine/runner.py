"""Orchestrate sizing run."""

from __future__ import annotations

from pathlib import Path

from fdplan_solar.engine.cost import compute_capex, compute_lcoe
from fdplan_solar.engine.pysam_pvwatts import compute_normalized_yield
from fdplan_solar.engine.site import peak_sun_hours_from_daily_kwh_per_kwdc, resolve_site
from fdplan_solar.engine.sizing import ac_capacity_kw, size_pv_dc_kw, size_storage_kwh
from fdplan_solar.schemas import (
    AssumptionsRecord,
    SizingInput,
    SizingOutput,
    SizingRunOptions,
    SiteSummary,
)


def run_sizing(
    inp: SizingInput,
    options: SizingRunOptions | None = None,
    weather_dir: Path | None = None,
) -> SizingOutput:
    opts = options or SizingRunOptions()
    resolved = resolve_site(inp.site, inp.pv.tilt_deg, inp.pv.azimuth_deg)

    pv_tech = inp.pv.model_copy(
        update={
            "tilt_deg": resolved.tilt_deg,
            "azimuth_deg": resolved.azimuth_deg,
        }
    )

    yield_data = compute_normalized_yield(
        site=resolved,
        pv=pv_tech,
        weather_mode=inp.weather_mode,
        reference_year=inp.reference_year,
        sunny_day_capacity_factor=inp.sunny_day_capacity_factor,
        weather_dir=weather_dir,
    )

    pv_dc = size_pv_dc_kw(inp, yield_data)
    usable_storage, nameplate_storage = size_storage_kwh(
        inp.demand, inp.storage, pv_dc, yield_data
    )
    pv_ac = ac_capacity_kw(pv_dc, pv_tech.dc_ac_ratio)
    daily_gen = yield_data.daily_kwh_per_kwdc * pv_dc
    annual_gen = yield_data.annual_kwh_per_kwdc * pv_dc

    capex = compute_capex(pv_dc, nameplate_storage, inp.costs)
    lcoe = compute_lcoe(capex.total_usd, annual_gen, pv_dc, inp.costs)

    land_m2 = None
    if inp.costs.land_m2_per_mw_dc:
        land_m2 = (pv_dc / 1000.0) * inp.costs.land_m2_per_mw_dc

    warnings = list(resolved.warnings)
    site_summary = SiteSummary(
        latitude=resolved.latitude,
        longitude=resolved.longitude,
        timezone_offset_hours=resolved.timezone_offset_hours,
        elevation_m=resolved.elevation_m,
        tilt_deg=resolved.tilt_deg,
        azimuth_deg=resolved.azimuth_deg,
        peak_sun_hours_equivalent=peak_sun_hours_from_daily_kwh_per_kwdc(
            yield_data.daily_kwh_per_kwdc
        ),
        daily_generation_kwh_per_kwdc=yield_data.daily_kwh_per_kwdc,
        annual_generation_kwh_per_kwdc=yield_data.annual_kwh_per_kwdc,
        timezone_inferred=resolved.timezone_inferred,
        elevation_defaulted=resolved.elevation_defaulted,
    )

    assumptions = AssumptionsRecord(
        weather_mode=inp.weather_mode.value,
        sizing_mode=inp.sizing_mode.value,
        design_margin=inp.design_margin,
        system_losses_percent=pv_tech.system_losses_percent,
        dc_ac_ratio=pv_tech.dc_ac_ratio,
        pv_cost_usd_per_w_dc=inp.costs.pv_cost_usd_per_w_dc,
        storage_cost_usd_per_kwh=inp.costs.storage_cost_usd_per_kwh,
        warnings=warnings,
    )

    hourly = None
    if opts.include_hourly_profile:
        hourly = yield_data.hourly_ac_kw_per_kwdc

    return SizingOutput(
        pv_dc_capacity_kw=pv_dc,
        pv_ac_capacity_kw=pv_ac,
        storage_capacity_kwh=usable_storage,
        storage_nameplate_kwh=nameplate_storage,
        land_area_m2=land_m2,
        daily_generation_kwh=daily_gen,
        annual_energy_kwh=annual_gen,
        capex=capex,
        lcoe_usd_per_kwh=lcoe,
        site_summary=site_summary,
        assumptions=assumptions,
        hourly_ac_kw_per_kwdc=hourly,
    )
