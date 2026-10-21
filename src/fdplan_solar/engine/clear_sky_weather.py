"""Location-specific clear-sky hourly weather (SAM CSV) for PySAM."""

from __future__ import annotations

import calendar
import math
from datetime import datetime
from pathlib import Path

from fdplan_solar.engine.site import ResolvedSite


def _day_of_year(year: int, month: int, day: int) -> int:
    return datetime(year, month, day).timetuple().tm_yday


def solar_declination_deg(day_of_year: int) -> float:
    b_deg = (360.0 / 365.0) * (day_of_year - 81)
    return 23.45 * math.sin(math.radians(b_deg))


def equation_of_time_minutes(day_of_year: int) -> float:
    b_deg = (360.0 / 365.0) * (day_of_year - 81)
    b_rad = math.radians(b_deg)
    return (
        9.87 * math.sin(2.0 * b_rad)
        - 7.53 * math.cos(b_rad)
        - 1.5 * math.sin(b_rad)
    )


def local_solar_time_hours(
    local_time_h: float, lon_deg: float, tz_h: float, eot_min: float
) -> float:
    lsm_deg = 15.0 * tz_h
    return local_time_h + (eot_min + 4.0 * (lon_deg - lsm_deg)) / 60.0


def hour_angle_deg(lst_h: float) -> float:
    return 15.0 * (lst_h - 12.0)


def solar_elevation_rad(lat_deg: float, dec_deg: float, h_deg: float) -> float:
    p = math.radians(lat_deg)
    d = math.radians(dec_deg)
    h = math.radians(h_deg)
    s = math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(h)
    s = max(-1.0, min(1.0, s))
    return math.asin(s)


def kasten_young_air_mass(zenith_deg: float) -> float:
    if zenith_deg >= 90.0 or zenith_deg < 0.0:
        return 0.0
    z_rad = math.radians(zenith_deg)
    denom = math.cos(z_rad) + 0.50572 * ((96.07995 - zenith_deg) ** -1.6364)
    if denom <= 0:
        return 0.0
    return 1.0 / denom


def dni_clearsky_wm2(air_mass: float, elevation_m: float) -> float:
    """Direct normal irradiance (W/m²), clear sky with simple elevation correction."""
    if air_mass <= 0.0:
        return 0.0
    # Scale extraterrestrial constant slightly with site elevation (thinner atmosphere).
    elev_factor = math.exp(-elevation_m / 8500.0)
    i0 = 1361.0 * elev_factor
    trans = 0.7 ** (air_mass**0.678)
    return max(0.0, i0 * trans)


def horizontal_irradiance_wm2(
    lat_deg: float,
    lon_deg: float,
    tz_h: float,
    elevation_m: float,
    year: int,
    month: int,
    day: int,
    hour: int,
) -> tuple[float, float, float]:
    """
    Return DNI, GHI, DHI in W/m² for the hour starting at local clock hour.
    """
    doy = _day_of_year(year, month, day)
    eot = equation_of_time_minutes(doy)
    dec = solar_declination_deg(doy)
    lst = local_solar_time_hours(float(hour) + 0.5, lon_deg, tz_h, eot)
    h_deg = hour_angle_deg(lst)
    el_rad = solar_elevation_rad(lat_deg, dec, h_deg)
    if el_rad <= 0:
        return 0.0, 0.0, 0.0

    zenith = 90.0 - math.degrees(el_rad)
    am = kasten_young_air_mass(zenith)
    dni = dni_clearsky_wm2(am, elevation_m)
    cos_z = math.cos(math.radians(zenith))
    dhi = 0.15 * dni * cos_z
    ghi = dni * cos_z + dhi
    return dni, ghi, dhi


def ambient_temperature_c(lat_deg: float, month: int, hour: int, elevation_m: float) -> float:
    """Simple diurnal + latitude/season temperature model (°C)."""
    seasonal = 12.0 * math.cos(math.radians((month - 1) * 30.0 - 180.0))
    lat_cool = -0.3 * abs(lat_deg)
    diurnal = 8.0 * math.sin(math.radians((hour - 14) * 15.0))
    lapse = -0.0065 * elevation_m
    return 20.0 + seasonal + lat_cool + diurnal + lapse


SAM_HEADER_ROW1 = (
    "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation,"
    "Local Time Zone,Clearsky DHI Units,Clearsky DNI Units,Clearsky GHI Units,"
    "Dew Point Units,DHI Units,DNI Units,GHI Units,Solar Zenith Angle Units,"
    "Temperature Units,Pressure Units,Wind Direction Units,Wind Speed Units,"
    "Surface Albedo Units,Interval"
)


def write_sam_clear_sky_csv(
    site: ResolvedSite,
    path: Path,
    reference_year: int = 2023,
) -> None:
    """Write an 8760-row SAM-compatible CSV for the given site (non-leap year)."""
    if calendar.isleap(reference_year):
        raise ValueError(
            f"reference_year {reference_year} is a leap year; use a non-leap year for 8760 hours."
        )
    header2 = (
        f"FDPlanSolar,0,,-,-,{site.latitude},{site.longitude},"
        f"{site.timezone_offset_hours},{site.elevation_m},{site.timezone_offset_hours},"
        "W/m2,W/m2,W/m2,C,W/m2,W/m2,W/m2,Degree,C,mbar,Degree,m/s,Dimensionless,60"
    )
    rows: list[str] = [SAM_HEADER_ROW1, header2, "Year,Month,Day,Hour,Minute,DNI,GHI,DHI,Temperature,Wind Speed"]
    for month in range(1, 13):
        days_in_month = calendar.monthrange(reference_year, month)[1]
        for day in range(1, days_in_month + 1):
            for hour in range(24):
                dni, ghi, dhi = horizontal_irradiance_wm2(
                    site.latitude,
                    site.longitude,
                    site.timezone_offset_hours,
                    site.elevation_m,
                    reference_year,
                    month,
                    day,
                    hour,
                )
                temp = ambient_temperature_c(site.latitude, month, hour, site.elevation_m)
                rows.append(
                    f"{reference_year},{month},{day},{hour},0,"
                    f"{dni:.2f},{ghi:.2f},{dhi:.2f},{temp:.2f},3.0"
                )

    if len(rows) - 3 != 8760:
        raise RuntimeError(f"Expected 8760 weather rows, got {len(rows) - 3}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
