"""Minimal FDPlan Evaluation + Events API client for solar worker."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


_ENV_BASE = {
    "p4d": "https://api.p4d.cloud.slb-ds.com",
    "prod_eu": "https://api.eu.cloud.slb.com",
    "prod_us": "https://api.us.cloud.slb.com",
}


class FdplanEvaluationClient:
    def __init__(self, cfg: dict[str, str]) -> None:
        self.cfg = cfg
        env = cfg.get("ENVIRONMENT", "p4d")
        base = _ENV_BASE.get(env, _ENV_BASE["p4d"])
        self.eval_base = f"{base}/fdplan/evaluation/v1"
        self.events_base = f"{base}/fdplan/events/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "appKey": cfg["APP_KEY"],
                "authorization": cfg["TOKEN"],
                "slb-data-partition-id": cfg["DATA_PARTITION"],
                "Content-Type": "application/json",
                "accept": "application/json",
            }
        )
        spec_id = cfg["SOLAR_COMPUTE_SPEC_ID"]
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", spec_id.split(":")[-1])
        self.event_type = f"com.slb.cloud.fdplan.evaluation.computation_required_{safe}_v1.v1"
        self.input_type_id = cfg.get("SOLAR_INPUT_DATA_TYPE_ID", "")
        self.output_type_id = cfg.get("SOLAR_OUTPUT_DATA_TYPE_ID", "")

    def poll_computation_events(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        frm = (now - timedelta(hours=1)).isoformat()
        to = now.isoformat()
        url = f"{self.events_base}/cloud-events"
        params = {"from": frm, "to": to, "type": self.event_type}
        resp = self.session.get(url, params=params, timeout=120)
        resp.raise_for_status()
        return resp.json().get("events", [])

    def computation_ids_from_events(self, events: list[dict[str, Any]]) -> list[str]:
        ids: list[str] = []
        for ev in events:
            data = ev.get("data") or {}
            cid = data.get("computationID")
            if cid and cid not in ids:
                ids.append(cid)
        return ids

    def get_computation(self, computation_id: str) -> dict[str, Any]:
        url = f"{self.eval_base}/computations/{quote(computation_id, safe='')}"
        resp = self.session.get(url, params={"includeDataLinkContent": "true"}, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def find_input_container(self, comp: dict[str, Any]) -> dict[str, Any]:
        return self._find_container(comp.get("inputContainers", []), self.input_type_id)

    def find_output_container(self, comp: dict[str, Any]) -> dict[str, Any]:
        return self._find_container(comp.get("outputContainers", []), self.output_type_id)

    @staticmethod
    def _find_container(containers: list[dict[str, Any]], type_id: str) -> dict[str, Any]:
        for c in containers:
            if c.get("dataTypeId") == type_id or not type_id:
                return c
        if containers:
            return containers[0]
        raise ValueError("No matching container on computation")

    def download_input_file(self, container: dict[str, Any], dest: Path) -> None:
        container_id = container["id"]
        filename = os.environ.get("SOLAR_INPUT_FILENAME", "solar-input.json")
        url = f"{self.eval_base}/containers/{quote(container_id, safe='')}/files/{filename}"
        resp = self.session.get(url, timeout=120)
        resp.raise_for_status()
        dest.write_bytes(resp.content)

    def upload_output_file(self, container: dict[str, Any], path: Path) -> None:
        container_id = container["id"]
        url = f"{self.eval_base}/containers/{quote(container_id, safe='')}/files"
        with path.open("rb") as fh:
            resp = self.session.post(
                url,
                files={"uploadFile": (path.name, fh, "application/json")},
                timeout=300,
            )
        resp.raise_for_status()

    def post_progress(self, computation_id: str, message: str) -> None:
        url = f"{self.eval_base}/computations/{quote(computation_id, safe='')}/status"
        body = {"type": "ComputationLogEvent", "message": message}
        self.session.post(url, json=body, timeout=60)

    def complete_success(self, computation_id: str) -> None:
        url = f"{self.eval_base}/computations/{quote(computation_id, safe='')}/status"
        body = {"type": "CompletedSuccessfully"}
        self.session.post(url, json=body, timeout=60)

    def complete_with_errors(self, computation_id: str, message: str) -> None:
        url = f"{self.eval_base}/computations/{quote(computation_id, safe='')}/status"
        body = {
            "type": "CompletedWithErrors",
            "computationErrors": [{"message": message}],
        }
        self.session.post(url, json=body, timeout=60)
