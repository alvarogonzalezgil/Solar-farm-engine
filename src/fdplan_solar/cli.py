"""CLI for solar farm sizing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from fdplan_solar.engine.runner import run_sizing
from fdplan_solar.schemas import SizingInput, SizingRunOptions, export_input_json_schema

app = typer.Typer(
    name="fdplan-solar",
    help="Size solar farms and storage from location and daily energy demand.",
)


@app.command("run")
def run_cmd(
    input: Annotated[Path, typer.Option("--input", "-i", help="JSON sizing input file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="JSON sizing output file.")],
    pretty: Annotated[bool, typer.Option("--pretty", help="Indented JSON output.")] = False,
    hourly: Annotated[
        bool, typer.Option("--hourly", help="Include normalized 8760 hourly profile in output.")
    ] = False,
    weather_dir: Annotated[
        Optional[Path],
        typer.Option("--weather-dir", help="Directory for generated SAM weather CSV files."),
    ] = None,
) -> None:
    """Run solar + storage sizing."""
    raw = json.loads(input.read_text(encoding="utf-8"))
    inp = SizingInput.model_validate(raw)
    result = run_sizing(
        inp,
        options=SizingRunOptions(include_hourly_profile=hourly),
        weather_dir=weather_dir,
    )
    text = json.dumps(
        result.model_dump(mode="json"),
        indent=2 if pretty else None,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + ("\n" if pretty else ""), encoding="utf-8")
    typer.echo(f"Wrote {output}")


@app.command("validate")
def validate_cmd(
    input: Annotated[Path, typer.Option("--input", "-i", help="JSON sizing input file.")],
) -> None:
    """Validate input JSON against the sizing schema."""
    raw = json.loads(input.read_text(encoding="utf-8"))
    SizingInput.model_validate(raw)
    typer.echo("Input is valid.")


@app.command("export-schemas")
def export_schemas_cmd(
    out_dir: Annotated[Path, typer.Option("--out-dir", "-d", help="Output directory.")] = Path(
        "schemas"
    ),
) -> None:
    """Write JSON Schema files for FDPlan data-type registration."""
    from fdplan_solar.schemas import export_output_json_schema

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "solar-input.schema.json").write_text(
        json.dumps(export_input_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "solar-output.schema.json").write_text(
        json.dumps(export_output_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Wrote schemas to {out_dir}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
