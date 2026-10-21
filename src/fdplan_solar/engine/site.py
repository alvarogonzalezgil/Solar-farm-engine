"""Site location helpers: timezone, default tilt/azimuth."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fdplan_solar.schemas import SiteInput


@dataclass(frozen=True)
class ResolvedSite:
    latitude: float
    longitude: float
    timezone_offset_hours: float
    elevation_m: float
    tilt_deg: float
    azimuth_deg: float
    timezone_inferred: bool
    elevation_defaulted: bool
    warnings: tuple[str, ...]


def infer_timezone_offset_hours(longitude: float) -> float:
    """Approximate standard-time UTC offset from longitude (15° per hour)."""
    return round(longitude / 15.0 * 2.0) / 2.0


def default_tilt_deg(latitude: float) -> float:
    return abs(latitude)


def default_azimuth_deg(latitude: float) -> float:
    return 180.0 if latitude >= 0 else 0.0


def resolve_site(
    site: SiteInput,
    tilt_deg: float | None,
    azimuth_deg: float | None,
) -> ResolvedSite:
    warnings: list[str] = []
    tz_inferred = False
    elev_defaulted = False

    if site.timezone_offset_hours is None:
        tz = infer_timezone_offset_hours(site.longitude)
        tz_inferred = True
        warnings.append(
            f"timezone_offset_hours inferred as {tz} from longitude; set explicitly for accuracy."
        )
    else:
        tz = site.timezone_offset_hours

    elev = site.elevation_m
    if elev == 0.0 and site.elevation_m == 0.0:
        elev_defaulted = True
        warnings.append("elevation_m defaulted to 0; set site elevation for air-mass accuracy.")

    tilt = tilt_deg if tilt_deg is not None else default_tilt_deg(site.latitude)
    azimuth = azimuth_deg if azimuth_deg is not None else default_azimuth_deg(site.latitude)

    return ResolvedSite(
        latitude=site.latitude,
        longitude=site.longitude,
        timezone_offset_hours=tz,
        elevation_m=elev,
        tilt_deg=tilt,
        azimuth_deg=azimuth,
        timezone_inferred=tz_inferred,
        elevation_defaulted=elev_defaulted,
        warnings=tuple(warnings),
    )


def peak_sun_hours_from_daily_kwh_per_kwdc(daily_kwh_per_kwdc: float) -> float:
    """Equivalent peak sun hours (kWh/kWp per day)."""
    return daily_kwh_per_kwdc
