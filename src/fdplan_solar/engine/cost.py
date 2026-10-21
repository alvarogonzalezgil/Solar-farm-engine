"""Parametric CAPEX and simple LCOE."""

from __future__ import annotations

from fdplan_solar.schemas import CapexBreakdown, CostInput


def compute_capex(
    pv_dc_kw: float,
    storage_nameplate_kwh: float,
    costs: CostInput,
) -> CapexBreakdown:
    pv_usd = pv_dc_kw * 1000.0 * costs.pv_cost_usd_per_w_dc
    storage_usd = storage_nameplate_kwh * costs.storage_cost_usd_per_kwh
    subtotal = pv_usd + storage_usd
    bos_usd = subtotal * costs.bos_and_install_pct
    total = subtotal + bos_usd
    return CapexBreakdown(
        pv_usd=pv_usd,
        storage_usd=storage_usd,
        bos_usd=bos_usd,
        total_usd=total,
    )


def compute_lcoe(
    capex_total_usd: float,
    annual_energy_kwh: float,
    pv_dc_kw: float,
    costs: CostInput,
) -> float | None:
    if not costs.project_lifetime_years or annual_energy_kwh <= 0:
        return None
    years = costs.project_lifetime_years
    om = 0.0
    if costs.annual_om_usd_per_kw_dc is not None:
        om = costs.annual_om_usd_per_kw_dc * pv_dc_kw
    total_energy = annual_energy_kwh * years
    total_cost = capex_total_usd + om * years
    return total_cost / total_energy
