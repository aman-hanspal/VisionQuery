# Stabilize VisionQuery before research experiments

The prototype can silently scan only an early portion of a video, reuse classes from a previous prompt, and fail frontend builds due to a missing utility module. Its device default and setup instructions also assume a different development environment. Those defects make demo behavior unreliable and would confound subsequent research comparisons.

This change repairs the baseline:

- Full-video scans no longer inherit the 900-frame cutoff. A separate budget mode spreads selected frames over the decoded timeline. Detection result limits do not stop scanning.
- Responses and saved run logs expose completion, selected timestamps/indices, truncation, timing, input/inference resolution, exact classes, environment versions and checkpoint identity.
- Query resolution is tied to the current prompt; stale replies cannot replace it. Snapshot overlays, webcam cleanup and user-visible error handling are corrected.
- Uploads are bounded and validated, IDs are strict, file types are preserved, and unreadable videos return client errors.
- Device selection is configurable with automatic CUDA/MPS/CPU selection. Test model injection removes YOLO startup from the test suite.
- Documentation reflects the Next.js frontend and app.main:app backend; regression tests and CI are included.

Validation: 44 backend tests and 10 frontend tests pass, along with Ruff, ESLint, TypeScript, and the Next.js production build. The tests use a mocked detector, real encoded video fixtures, and simulated timing/camera cases. No detector-accuracy or GPU-performance claim follows from these checks.

Before merging: complete docs/RESEARCH_PREP.md on the RTX 3060 laptop, including real YOLO inference, CUDA, browser playback/seek, and webcam cleanup. Budget mode includes two decode passes; results above MAX_DETECTIONS are explicitly discarded and counted. There is no adaptive sampling, tracking, background job system or full-results pagination in this PR.

Merge requires the user's review and approval.
