"""Pydantic models for solar sizing input and output."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class WeatherMode(str, Enum):
    CLEAR_SKY = "clear_sky"
    CAPACITY_FACTOR = "capacity_factor"


class SizingMode(str, Enum):
    MEET_LOAD = "meet_load"
    FIXED_CAPACITY = "fixed_capacity"


class SiteInput(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timezone_offset_hours: float | None = Field(
        default=None,
        description="UTC offset in hours (e.g. 4 for Gulf). Inferred from longitude if omitted.",
    )
    elevation_m: float = Field(default=0.0, ge=-500, le=9000)
    country: str | None = None
    oil_field_name: str | None = None


class DemandInput(BaseModel):
    daily_energy_kwh: float = Field(..., gt=0)
    peak_power_kw: float | None = Field(default=None, gt=0)


class PvTechnologyInput(BaseModel):
    dc_ac_ratio: float = Field(default=1.2, gt=0)
    array_type: int = Field(
        default=0,
        ge=0,
        le=4,
        description="PVWatts array_type: 0=fixed open rack, 1=roof, 2=1-axis, etc.",
    )
    tilt_deg: float | None = Field(
        default=None,
        ge=0,
        le=90,
        description="Panel tilt; default ≈ |latitude| when omitted.",
    )
    azimuth_deg: float | None = Field(
        default=None,
        ge=0,
        le=360,
        description="Azimuth from north clockwise; default 180° N hemisphere, 0° S.",
    )
    system_losses_percent: float = Field(default=14.0, ge=0, le=99)
    module_type: int = Field(default=0, ge=0, le=2)
    gcr: float = Field(default=0.4, ge=0, le=0.99)


class StorageInput(BaseModel):
    storage_hours: float | None = Field(
        default=None,
        gt=0,
        description="Energy storage duration at average load (kWh/day / 24).",
    )
    storage_fraction_of_daily_load: float = Field(
        default=0.5,
        gt=0,
        le=1.5,
        description="Usable storage as fraction of daily load when storage_hours not set.",
    )
    round_trip_efficiency: float = Field(default=0.9, gt=0, le=1)
    depth_of_discharge: float = Field(default=0.9, gt=0, le=1)


class CostInput(BaseModel):
    pv_cost_usd_per_w_dc: float = Field(default=0.85, gt=0)
    storage_cost_usd_per_kwh: float = Field(default=200.0, gt=0)
    bos_and_install_pct: float = Field(
        default=0.0,
        ge=0,
        description="Extra CAPEX as fraction of PV + storage subtotal.",
    )
    land_m2_per_mw_dc: float = Field(default=20_000.0, gt=0)
    project_lifetime_years: int | None = Field(default=None, gt=0)
    annual_om_usd_per_kw_dc: float | None = Field(default=None, ge=0)


class SizingInput(BaseModel):
    site: SiteInput
    demand: DemandInput
    pv: PvTechnologyInput = Field(default_factory=PvTechnologyInput)
    weather_mode: WeatherMode = WeatherMode.CLEAR_SKY
    sunny_day_capacity_factor: float | None = Field(
        default=None,
        gt=0,
        le=1,
        description="Only for weather_mode=capacity_factor.",
    )
    sizing_mode: SizingMode = SizingMode.MEET_LOAD
    fixed_dc_capacity_kw: float | None = Field(default=None, gt=0)
    design_margin: float = Field(
        default=0.1,
        ge=0,
        le=0.5,
        description="Fractional oversize on PV for meet_load mode.",
    )
    storage: StorageInput = Field(default_factory=StorageInput)
    costs: CostInput = Field(default_factory=CostInput)
    reference_year: int = Field(
        default=2023,
        ge=2000,
        le=2100,
        description="Non-leap year for 8760-hour weather (leap years have 8784 hours).",
    )

    @model_validator(mode="after")
    def fixed_capacity_requires_kw(self) -> SizingInput:
        if self.sizing_mode == SizingMode.FIXED_CAPACITY and not self.fixed_dc_capacity_kw:
            raise ValueError("fixed_dc_capacity_kw is required when sizing_mode is fixed_capacity")
        if self.weather_mode == WeatherMode.CAPACITY_FACTOR and not self.sunny_day_capacity_factor:
            raise ValueError(
                "sunny_day_capacity_factor is required when weather_mode is capacity_factor"
            )
        return self


class SiteSummary(BaseModel):
    latitude: float
    longitude: float
    timezone_offset_hours: float
    elevation_m: float
    tilt_deg: float
    azimuth_deg: float
    peak_sun_hours_equivalent: float
    daily_generation_kwh_per_kwdc: float
    annual_generation_kwh_per_kwdc: float
    timezone_inferred: bool = False
    elevation_defaulted: bool = False


class CapexBreakdown(BaseModel):
    pv_usd: float
    storage_usd: float
    bos_usd: float
    total_usd: float


class AssumptionsRecord(BaseModel):
    weather_mode: str
    sizing_mode: str
    design_margin: float
    system_losses_percent: float
    dc_ac_ratio: float
    pv_cost_usd_per_w_dc: float
    storage_cost_usd_per_kwh: float
    warnings: list[str] = Field(default_factory=list)


class SizingOutput(BaseModel):
    pv_dc_capacity_kw: float
    pv_ac_capacity_kw: float
    storage_capacity_kwh: float
    storage_nameplate_kwh: float
    land_area_m2: float | None = None
    daily_generation_kwh: float
    annual_energy_kwh: float
    capex: CapexBreakdown
    lcoe_usd_per_kwh: float | None = None
    site_summary: SiteSummary
    assumptions: AssumptionsRecord
    hourly_ac_kw_per_kwdc: list[float] | None = Field(
        default=None,
        description="8760 normalized AC power (kW per kW DC) when include_hourly_profile=true.",
    )


class SizingRunOptions(BaseModel):
    include_hourly_profile: bool = False


def export_input_json_schema() -> dict[str, Any]:
    return SizingInput.model_json_schema()


def export_output_json_schema() -> dict[str, Any]:
    return SizingOutput.model_json_schema()
