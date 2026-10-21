"""PV and battery storage sizing."""

from __future__ import annotations

from fdplan_solar.engine.pysam_pvwatts import NormalizedYield
from fdplan_solar.schemas import DemandInput, SizingMode, SizingInput, StorageInput


def size_pv_dc_kw(
    inp: SizingInput,
    yield_data: NormalizedYield,
) -> float:
    if inp.sizing_mode == SizingMode.FIXED_CAPACITY:
        assert inp.fixed_dc_capacity_kw is not None
        return inp.fixed_dc_capacity_kw

    daily_per_kw = yield_data.daily_kwh_per_kwdc
    if daily_per_kw <= 0:
        raise ValueError("Normalized daily yield per kW DC is zero; check site and weather.")

    margin = 1.0 + inp.design_margin
    return inp.demand.daily_energy_kwh * margin / daily_per_kw


def size_storage_kwh(
    demand: DemandInput,
    storage: StorageInput,
    pv_dc_kw: float,
    yield_data: NormalizedYield,
) -> tuple[float, float]:
    """
    Return (usable_kwh, nameplate_kwh) accounting for DoD and round-trip efficiency.
    """
    if storage.storage_hours is not None:
        avg_load_kw = demand.daily_energy_kwh / 24.0
        usable = avg_load_kw * storage.storage_hours
    else:
        usable = demand.daily_energy_kwh * storage.storage_fraction_of_daily_load

    # Optional refinement: energy deficit vs hourly PV at sized plant (scalar load spread evenly).
    avg_load_kw = demand.daily_energy_kwh / 24.0
    deficit = 0.0
    running = 0.0
    for ac_per_kw in yield_data.hourly_ac_kw_per_kwdc:
        gen_kw = ac_per_kw * pv_dc_kw
        net = gen_kw - avg_load_kw
        running += net
        if running < deficit:
            deficit = running
    if deficit < 0:
        usable = max(usable, -deficit)

    nameplate = usable / (storage.depth_of_discharge * storage.round_trip_efficiency)
    return usable, nameplate


def ac_capacity_kw(pv_dc_kw: float, dc_ac_ratio: float) -> float:
    return pv_dc_kw / dc_ac_ratio
