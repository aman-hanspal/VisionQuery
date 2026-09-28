# Research preparation: baseline repair

Base: `620335b933757dcd4d14d95c0544b7dd54923996` on `main`.
Working branch: `research-prep`. Merge only after laptop acceptance.

## Changes

- Restore missing frontend utilities and correct the setup docs from Vite to Next.js.
- Replace the MPS default with automatic device selection; support explicit CPU/CUDA/MPS configuration.
- Remove silent video prefix limits. Full scans reach decoder EOF; budgeted scans distribute distinct frames across the decoded timeline.
- Keep result limits separate from coverage and expose truncation, completion, stop reason, timestamps and detector calls.
- Use timestamp-driven sampling rather than rounding native/requested FPS to a fixed integer step. Report timestamp fallbacks and estimated duration.
- Bind class resolution to the exact current query and ignore aborted/out-of-order replies; allow retry after resolution failure.
- Fix React lint errors, late webcam stream leaks, cancellation of obsolete live requests, confidence=0 handling, and stale/overlapping snapshot overlays.
- Validate video IDs, limit and validate uploads, preserve supported file extensions/MIME, remove invalid files, and return a client error for unreadable saved videos.
- Inject the model through the application factory so tests do not load real YOLO during lifespan startup. Keep model vocabulary mutation and prediction under one shared lock.
- Add run logs and an environment manifest; add regression tests and CI.

## Tests and their limits

`backend/tests/` covers API upload/playback byte ranges, real encoded-video timing, full/budget coverage, explicit stop semantics, VFR-style timestamps, missing timestamps, class consistency, result caps, malformed class-provider responses, and resource cleanup. The detector is mocked, so these are correctness tests, not evidence of detector accuracy or GPU compatibility.

`frontend/tests/` covers query resolution races, empty/error states, readable API errors, snapshot selection, and webcam cleanup including React Strict Mode's setup/cleanup cycle. Build, lint and TypeScript checks validate the application code. Tests cannot prove camera permission/device behavior in a real browser.

No adaptive selector, tracker, accuracy claim, novelty claim or performance benchmark is introduced by these repairs.

## Laptop acceptance checklist

1. Check out `research-prep`. Install dependencies following the root README. Run the backend from `backend/` and frontend from `frontend/`.
2. Verify `torch.cuda.is_available()` and the reported RTX 3060 device. Set `DEVICE=cuda` in `backend/.env`. Start the backend; resolve any first-run CLIP/weight downloads before measuring anything.
3. Open the UI on port 3000. Upload a short H.264 MP4 with known objects near the beginning, middle and end. Query explicit comma-separated classes at 1 FPS. Confirm the scan completes, timestamps reach late footage, results can seek, and boxes align with the source frame.
4. Run the same clip in budget mode with 3 frames. In the run JSON, verify exactly 3 unique selected indices/timestamps spanning the first and last decoded frame (unless the video has fewer frames). Inspect the extra decode pass in the counters.
5. Change `car` to `person` quickly. Confirm the button waits for current classes and the completed response logs the intended classes. Disconnect the backend temporarily and verify the class-resolution error and retry control.
6. Enable Live Webcam, change classes, then return to Video System. Confirm camera access ends and old boxes/results do not remain. Repeat once; check confidence 0 is accepted. Inspect a backend/network failure message if the API is unavailable.
7. Upload a non-video/empty file and a supported video whose browser codec is incompatible. The former should be rejected; the latter may decode on the backend but fail browser preview because there is no transcoding.
8. Optionally set `MAX_DETECTIONS=1`, restart, and scan a clip with repeated hits. Confirm result truncation is clearly reported while frames continue to the end. Restore the intended limit before experiments.
9. Save one full and one budget run JSON plus `uv pip freeze` from the laptop environment. Check `checkpoint_sha256`, device, source commit, and dirty state. Restart the server after switching commits or settings so startup metadata is current.
10. Rerun the automated checks and review the diff. Merge only after these checks pass and the user approves.

## Remaining limits

- OpenCV cannot reliably distinguish EOF from every decode failure when frame-count metadata is missing or wrong. Metadata states the completion basis and timestamp fallback use.
- Budget mode reads the full timeline before inference, then decodes again. Include that cost in comparisons; it is not an optimized seek-based/adaptive method.
- Returned/logged detections are capped and explicitly flagged. No paginated full-results store is implemented.
- Inference requests are serialized because vocabulary changes mutate shared model state. This is a local research prototype, with no authentication, background job queue, cancellation of server-side scans, or automatic retention policy.
- Sparse detections are snapshots and do not establish presence between frames. Attribute phrases are prompts to the detector, not guaranteed attribute understanding.
- Real checkpoint inference, CUDA/driver setup, free-form OpenRouter behavior, physical webcam and browser codec playback must be verified locally.
