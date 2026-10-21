"""PySAM PVWatts v8 adapter for normalized hourly yield."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from fdplan_solar.engine.clear_sky_weather import write_sam_clear_sky_csv
from fdplan_solar.engine.site import ResolvedSite
from fdplan_solar.schemas import PvTechnologyInput, WeatherMode


@dataclass(frozen=True)
class NormalizedYield:
    """Hourly AC output in kW per kW DC installed."""

    hourly_ac_kw_per_kwdc: list[float]
    annual_kwh_per_kwdc: float
    daily_kwh_per_kwdc: float
    weather_file: Path | None


def _run_pvwatts(
    weather_path: Path,
    site: ResolvedSite,
    pv: PvTechnologyInput,
) -> list[float]:
    import PySAM.Pvwattsv8 as pvwatts  # noqa: PLC0415 — optional heavy import

    model = pvwatts.default("PVWattsNone")
    model.SolarResource.solar_resource_file = str(weather_path)
    model.SystemDesign.system_capacity = 1.0
    model.SystemDesign.dc_ac_ratio = pv.dc_ac_ratio
    model.SystemDesign.array_type = pv.array_type
    model.SystemDesign.tilt = pv.tilt_deg
    model.SystemDesign.azimuth = pv.azimuth_deg
    model.SystemDesign.module_type = pv.module_type
    model.SystemDesign.losses = pv.system_losses_percent
    model.SystemDesign.gcr = pv.gcr
    model.execute()

    # Outputs.ac is hourly AC power in watts for system_capacity kW.
    ac_w = list(model.Outputs.ac)
    if len(ac_w) != 8760:
        raise RuntimeError(f"PVWatts returned {len(ac_w)} hourly values, expected 8760")
    return [w / 1000.0 for w in ac_w]


def compute_normalized_yield(
    site: ResolvedSite,
    pv: PvTechnologyInput,
    weather_mode: WeatherMode,
    reference_year: int,
    sunny_day_capacity_factor: float | None = None,
    weather_dir: Path | None = None,
) -> NormalizedYield:
    if weather_mode == WeatherMode.CAPACITY_FACTOR:
        if sunny_day_capacity_factor is None:
            raise ValueError("sunny_day_capacity_factor required for capacity_factor mode")
        # Annual average capacity factor → flat hourly output (kW per kWdc).
        hourly = [sunny_day_capacity_factor] * 8760
        annual = sunny_day_capacity_factor * 8760.0
        daily = annual / 365.0
        return NormalizedYield(
            hourly_ac_kw_per_kwdc=hourly,
            annual_kwh_per_kwdc=annual,
            daily_kwh_per_kwdc=daily,
            weather_file=None,
        )

    base_dir = weather_dir or Path(tempfile.gettempdir()) / "fdplan_solar"
    base_dir.mkdir(parents=True, exist_ok=True)
    weather_path = base_dir / (
        f"clearsky_{site.latitude:.4f}_{site.longitude:.4f}_{reference_year}.csv"
    )
    write_sam_clear_sky_csv(site, weather_path, reference_year)
    hourly = _run_pvwatts(weather_path, site, pv)
    annual = sum(hourly)
    # Average daily yield across the sunny-year profile (location-specific).
    daily = annual / 365.0
    return NormalizedYield(
        hourly_ac_kw_per_kwdc=hourly,
        annual_kwh_per_kwdc=annual,
        daily_kwh_per_kwdc=daily,
        weather_file=weather_path,
    )

