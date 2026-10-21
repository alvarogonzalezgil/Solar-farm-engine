"""Tests for solar sizing engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fdplan_solar.engine.clear_sky_weather import write_sam_clear_sky_csv
from fdplan_solar.engine.runner import run_sizing
from fdplan_solar.engine.site import resolve_site
from fdplan_solar.schemas import (
    DemandInput,
    SiteInput,
    SizingInput,
    SizingMode,
    WeatherMode,
)


EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _base_input(**overrides) -> SizingInput:
    data = json.loads((EXAMPLES / "sample_input_uae.json").read_text(encoding="utf-8"))
    data.update(overrides)
    return SizingInput.model_validate(data)


def test_clear_sky_csv_has_8760_rows(tmp_path: Path) -> None:
    site = resolve_site(
        SiteInput(latitude=25.0, longitude=55.0, timezone_offset_hours=4, elevation_m=10),
        None,
        None,
    )
    path = tmp_path / "weather.csv"
    write_sam_clear_sky_csv(site, path, 2023)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8760 + 3


def test_uae_meet_load_produces_positive_sizing() -> None:
    inp = _base_input()
    out = run_sizing(inp)
    assert out.pv_dc_capacity_kw > 0
    assert out.storage_capacity_kwh > 0
    assert out.capex.total_usd > out.capex.pv_usd


def test_different_latitudes_change_required_pv() -> None:
    uae = _base_input()
    norway = SizingInput.model_validate(
        json.loads((EXAMPLES / "sample_input_norway.json").read_text(encoding="utf-8"))
    )
    out_uae = run_sizing(uae)
    out_no = run_sizing(norway)
    assert out_uae.pv_dc_capacity_kw != out_no.pv_dc_capacity_kw
    assert out_no.pv_dc_capacity_kw > out_uae.pv_dc_capacity_kw


def test_fixed_capacity_mode() -> None:
    inp = _base_input(
        sizing_mode="fixed_capacity",
        fixed_dc_capacity_kw=5000,
    )
    out = run_sizing(inp)
    assert out.pv_dc_capacity_kw == 5000


def test_capacity_factor_fallback() -> None:
    inp = _base_input(
        weather_mode="capacity_factor",
        sunny_day_capacity_factor=0.22,
    )
    out = run_sizing(inp)
    assert out.pv_dc_capacity_kw > 0


def test_validate_rejects_fixed_capacity_without_kw() -> None:
    inp = _base_input()
    data = inp.model_dump()
    data["sizing_mode"] = "fixed_capacity"
    data.pop("fixed_dc_capacity_kw", None)
    with pytest.raises(ValueError):
        SizingInput.model_validate(data)


def test_site_inference_warning() -> None:
    inp = _base_input()
    inp.site.timezone_offset_hours = None
    out = run_sizing(inp)
    assert any("timezone" in w.lower() for w in out.assumptions.warnings)
