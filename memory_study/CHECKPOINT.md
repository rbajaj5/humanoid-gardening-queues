# Memory Study Checkpoint

2026-10-26. Experiment code and evidence are confined to `memory_study/` in the gardening repository.
The root README and checkpoint now feature this study for public release.
Earlier GPU garden, laundry, RAG, and registered assurance results are unchanged.

## Purpose and current design

Read Chinese engineering docs from Alibaba AgentRun/Bailian and Tencent Agent
Memory/Memory Hub. Interpret task-state restoration, shared knowledge, stale
retrieval, and execution preconditions as testable coordination mechanisms.
No psychology sources or actual vendor implementations are tested.

Configuration: two seeds 45110/45111; five profiles; four policy ablations;
40 seconds each; target 60 ml per pot; 500 ml source; freshness 0.5 s.
Reuses calibrated G1 body at CUDA 2 ms and ballistic water at CUDA 10 ms.
Two software planners share one humanoid in the shared-snapshot profile.

## Completed

- All 40 CUDA episodes completed; no simulation job remains running.
- 27 tests passed: 10 new protocol tests and all 17 existing gardening tests.
- Full analysis independently checked 40,000 physical states, all task summaries,
  conservation, source/config/model fingerprints and matched input arrays.
- Both seeds give the same dose outcomes:
  - nominal: all arms [60,60,60] ml;
  - checkpoint replay: memory-only [120,120,120], all other arms [60,60,60];
  - shared snapshot: first three arms [120,120,120], queue-aware [60,60,60];
  - stale recall: memory-only/idempotent [120,120,120], freshness/full [60,60,60];
  - observation outage: first two arms [60,60,60], freshness/full [60,0,0].
- Outage holds last 34.28 seconds in both guarded arms. No body-envelope or tool
  timeout failure. Maximum measured body tilt 1.288411 degrees.
- Nominal trajectory differences across policy arms are small floating-point
  differences: max qpos 4.77e-6 and max qvel 2.14e-5; not bitwise equality.
- One 60 s 1920x1080 25 fps silent, captioned movie completed. All 1,500 encoded
  frames decode. Ten decoded-frame comparisons have mean pixel error below 1.25.
  Each illustrated run shows 251/1000 retained samples spanning its full duration;
  only seed 45110 is illustrated, while both seeds remain in the results.
- MP4 SHA256: 238c1c137859a9584f7087706bf813c1e8954bba5c3ce70d0d04ab8592898549.
- Evidence is in `memory_study/output/`. Publishing target is GitHub release
  `engineering-memory-gpu-2026-10-26`; verify its asset digest before reporting
  publication complete. The MP4 is a release asset, not a Git-tracked binary.
- Final visual inspection covered encoded frames in all five cases: robot and
  plants visible, bilingual labels legible, no text overlap, and dose/queue/hold
  telemetry agrees with the retained comparison. No visual repairs were needed.

## Remaining

- Generalization to other robots, moving pots, noisy sensing, learned planners,
  and executor crash recovery is not tested. The output is exploratory evidence,
  not a vendor benchmark, safety certificate or hardware demonstration.

## Exact commands (from gardening repository)

```powershell
../.venv-laundry-gpu/Scripts/python.exe -m unittest memory_study.test_protocol -v
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.run --resume
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.analyze
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.render
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.verify_media
```

Before restarting, inspect active Python processes and output names. `--resume`
skips only matching source/config/model fingerprints with NPZ present. Existing
results are not overwritten. CUDA is mandatory. Do not update Warp or drivers.

The executor persists across a simulated planner checkpoint replay; this is not
process-crash recovery. Exact observations, trusted messages, fixed plants,
centralized reservation, no LLM learning, no hardware or fluid validation.
