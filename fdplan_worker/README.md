# FDPlan solar sizing worker (phase 2)

Event-driven worker that registers against FDPlan Evaluation + Events APIs and runs `fdplan_solar.run_sizing` on each computation.

## Prerequisites

1. Register data types and computation spec (see FDPlan tutorials):
   - [compute-specifications.md](https://github.com/slb-swt/Cybertron/blob/master/bumblebee-skills/plugins/fdplan/external/tutorials/compute-specifications.md)
   - [compute-evaluation.md](https://github.com/slb-swt/Cybertron/blob/master/bumblebee-skills/plugins/fdplan/external/tutorials/compute-evaluation.md)
2. Export JSON schemas from the engine:

   ```bash
   fdplan-solar export-schemas --out-dir schemas
   ```

3. Use authority-prefixed IDs, for example:
   - `{authority}:data-types:solar-input` → `solar-input.json` (schema in `schemas/solar-input.schema.json`)
   - `{authority}:data-types:solar-output` → `solar-output.json`
   - `{authority}:computation-specs:solar-sizing`

## Configuration

Copy `.env.sample` to `src/.env` and set credentials and spec IDs (pattern follows `bumblebee-economics-exemplar`).

| Variable | Purpose |
|----------|---------|
| `APP_KEY`, `TOKEN`, `DATA_PARTITION`, `ENVIRONMENT` | FDPlan API auth |
| `SOLAR_COMPUTE_SPEC_ID` | Computation spec to poll |
| `SOLAR_INPUT_DATA_TYPE_ID`, `SOLAR_OUTPUT_DATA_TYPE_ID` | Container file mapping |
| `ITERATIONS`, `WAIT_TIME_IN_MINUTES` | Poll loop |
| `LOCAL_DIRECTORY` | Temp download/upload folder |

## Run locally

```bash
pip install -e ..
py fdplan_worker/src/main.py
```

The worker downloads `solar-input.json`, validates with `SizingInput`, writes `solar-output.json`, uploads to the output container, and posts `CompletedSuccessfully`.
