# VisionQuery

Timestamped object search in uploaded videos and webcam frames, using **FastAPI + Ultralytics YOLO-World v2** and a **Next.js 16 / React 19** frontend.

This is an independent-frame detector baseline. It does not implement tracking, adaptive sampling, embeddings, or a generative video VLM. Bounding boxes are observations on sampled frames, not continuous object tracks.

## Start locally

Use Python 3.11+ (3.12 recommended), uv, and Node.js 22.12+ (or 20.19+). Run the backend from `backend/` so relative model, storage and `.env` paths resolve correctly.

```bash
cd backend
uv venv --python 3.12
uv pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and choose a device:

- `DEVICE=auto` selects available CUDA, then MPS, otherwise CPU.
- For an RTX 3060, install a CUDA-enabled PyTorch build appropriate to your driver using the [official PyTorch installer](https://pytorch.org/get-started/locally/), then set `DEVICE=cuda`. A CPU-only PyTorch installation will not gain CUDA support from changing this setting.
- `DEVICE=cpu` runs without a GPU; `DEVICE=mps` targets supported Apple hardware.

Check the installed runtime and start the API:

```bash
uv run --no-sync python -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA device')"
uv run --no-sync python -m uvicorn app.main:app --reload --port 8000
```

Weights are included in this repository. The default is `yolov8m-worldv2.pt`; set `MODEL_PATH=yolov8s-worldv2.pt` to use the smaller checkpoint. Initial vocabulary encoding may need a CLIP dependency/checkpoint download. Keep internet access available for the first real-model run. API docs: <http://localhost:8000/docs>.

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. To change the backend URL, copy `frontend/.env.example` to `frontend/.env.local` and edit `NEXT_PUBLIC_BACKEND_URL`. Restart the dev server or rebuild the frontend after changing it. Set `CORS_ORIGINS` in the backend to the actual frontend origin if using a different host/port.

`bash setup.sh` performs the dependency/template setup on macOS, Linux, or WSL. It does not configure NVIDIA drivers or a CUDA-specific PyTorch build.

## Query behavior

Upload MP4, WebM, MOV, AVI or MKV footage supported by the installed OpenCV decoder. Preview also requires a browser-supported container/codec; uploads are **not transcoded**. MP4 with H.264 is a useful playback choice. Uploads default to a 1 GiB limit and invalid/empty/partially saved files are removed.

Without `OPENROUTER_API_KEY`, enter comma-separated object phrases such as `person, car, red helmet`. With a key, `/classes` attempts free-form prompt conversion; provider failures fall back to comma-separated parsing. The UI shows the classes and waits for the current query's resolution. Explicit API `classes` take precedence over `prompt`; use explicit frozen classes for experiments.

| Scan mode | Behavior |
|---|---|
| `full` (default) | Decode through the video and run the detector at the requested sample FPS. There is no implicit 900-frame cutoff. |
| `budget` | First decode the timeline, then distribute a fixed number of distinct sampled frames across presentation time, including first and last frames. This uses two decode passes, whose cost is recorded. |

Full scans still sample frames: a completed scan is not exhaustive object coverage. In budget mode, `fps` is not applied. `frame_budget` must be at least 2; shorter videos use all available frames. `MAX_SAMPLED_FRAMES` supplies only the default budget (900). An explicit `max_sampled_frames` in full mode stops early and reports `scan_complete=false` if another sampled frame remains.

Example request to `POST /query`:

```json
{
  "video_id": "ID_FROM_UPLOAD",
  "classes": ["person", "car"],
  "scan_mode": "budget",
  "frame_budget": 100,
  "conf": 0.25
}
```

Responses include `detections`, the exact `classes`, and `metadata`. Metadata records selected timestamps/indices, decoder FPS, timestamp fallbacks, source resolution, inference image size, decoded frames, detector calls, timing, completion/stop reason, and result truncation. The original `detections` field remains available to existing clients.

`MAX_DETECTIONS` limits returned and logged boxes, **not frames scanned**. Extra boxes are counted and discarded, with `detections_truncated` and `dropped_detections` reported. This is not pagination; raise the limit deliberately for experiments that require every box. Never score a truncated run as a complete result set.

Each successful query writes `backend/storage/runs/<run_id>.json` with the returned detections, metadata, environment/package versions, source commit/dirty state, checkpoint SHA-256 and available GPU name. Logs include actual classes but never the OpenRouter key. Storage is local and requires manual housekeeping. Failed log writes are surfaced through `run_log_saved=false`.

Timing definitions:

- `elapsed_seconds`: video open, decode, selection and detector calls, after class encoding.
- `selection_seconds`: budget timeline prepass and selection (included in elapsed time).
- `inference_seconds`: prediction and extraction of its boxes (included in elapsed time).
- `processing_seconds`: request processing through scan completion, including class resolution, lock wait and class encoding; excludes JSON serialization/log write/network delivery.
- Model loading and checkpoint hashing happen once at startup and are not query latency. Initial inference/text-encoder warmup can still affect the first query. Use separate warmup and measured runs for research.

OpenCV presentation timestamps are preferred; missing/nonmonotonic timestamps fall back to nominal FPS and are reported. Duration is an estimate. EOF is checked against reported frame counts when available; with unknown/unreliable counts, decoder EOF alone cannot certify an uncorrupted full file. Inspect `completion_basis` and timestamp fallback fields before evaluating VFR/corrupt footage.

## Checks

The API/sampling suite uses an injected detector, real encoded video fixtures, and simulated timing edge cases. It does not download weights or require PyTorch.

```bash
cd backend
uv venv --python 3.12
uv pip install -r requirements-test.txt
uv run --no-sync python -m pytest -q
uv run --no-sync ruff check app tests
```

Use a separate environment for these lightweight dependencies if you already have the full inference stack: `opencv-python` and `opencv-python-headless` both provide `cv2` and should not be installed together. In an existing inference environment, use `requirements-dev.txt` instead.

```bash
cd frontend
npm ci
npm run lint
npm test
npm run typecheck
npm run build
```

GitHub Actions runs the backend checks and frontend lint/tests/build. Real YOLO/CUDA inference and physical webcam behavior remain laptop acceptance checks; see [docs/RESEARCH_PREP.md](docs/RESEARCH_PREP.md).

## Screenshots from the original prototype

![Upload mode](assets/upload_mode.png)
![Live mode](assets/live_mode.png)
