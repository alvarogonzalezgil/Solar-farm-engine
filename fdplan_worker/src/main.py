#!/usr/bin/env python
"""FDPlan event worker for solar sizing compute."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

# Allow running without package install when repo root is on PYTHONPATH.
_REPO_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from fdplan_solar.engine.runner import run_sizing  # noqa: E402
from fdplan_solar.schemas import SizingInput  # noqa: E402

from worker.config import load_config  # noqa: E402
from worker.fdplan_client import FdplanEvaluationClient  # noqa: E402


def process_computation(client: FdplanEvaluationClient, computation_id: str, work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    comp = client.get_computation(computation_id)
    input_container = client.find_input_container(comp)
    output_container = client.find_output_container(comp)

    input_path = work_dir / os.environ.get("SOLAR_INPUT_FILENAME", "solar-input.json")
    client.download_input_file(input_container, input_path)

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    inp = SizingInput.model_validate(raw)
    result = run_sizing(inp)
    output_path = work_dir / os.environ.get("SOLAR_OUTPUT_FILENAME", "solar-output.json")
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    client.post_progress(computation_id, "Solar sizing complete; uploading results.")
    client.upload_output_file(output_container, output_path)
    client.complete_success(computation_id)


def main() -> None:
    cfg = load_config()
    client = FdplanEvaluationClient(cfg)
    work_dir = Path(cfg["LOCAL_DIRECTORY"])
    iterations = int(cfg.get("ITERATIONS", "10"))
    wait_min = int(cfg.get("WAIT_TIME_IN_MINUTES", "5"))

    for i in range(iterations):
        print(f"Poll iteration {i + 1}/{iterations}")
        events = client.poll_computation_events()
        computation_ids = client.computation_ids_from_events(events)
        if not computation_ids:
            print("No solar computation events.")
        for cid in computation_ids:
            print(f"Processing computation {cid}")
            try:
                process_computation(client, cid, work_dir / cid)
            except Exception as exc:  # noqa: BLE001 — worker reports failure to FDPlan
                print(f"Error: {exc}")
                client.complete_with_errors(cid, str(exc))
        time.sleep(wait_min * 60)


if __name__ == "__main__":
    main()
