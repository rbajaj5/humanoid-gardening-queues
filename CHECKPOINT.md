# Gardening GPU Checkpoint

Updated 2026-10-24. Separate public repository:
https://github.com/rbajaj5/humanoid-gardening-queues

## Completed Physics and Evidence

- Preserved the original CPU task study: 4,608 episodes, 18 full replays,
  original source/config/results and schematic movie. See TASK_COORDINATION.md.
- Added independent physical_garden/: pinned G1, 29 joints, free base, ground
  contacts, 33.521142 kg robot-plus-tool. No scripted root trajectory.
- Robot dynamics: MuJoCo Warp CUDA, 2 ms. Water: Warp CUDA, ballistic 1 ml parcels,
  10 ms. Task control and retained state: 40 ms.
- Ran all nine final episodes: 3 policies x 3 communication profiles, seed 45100,
  34 s each, identical exogenous noise hash. Full qpos/qvel/ctrl and JSON retained.
- Timely: all policies delivered [60,60,60] ml.
- Lost receipts: timeout/new-ID [300,0,0], stable-ID/receipt-only [60,0,0],
  queue-aware [60,60,60]. Baseline excess 240 ml, overflow accounting 120 ml.
- Permanent observation loss: receipt arms [60,60,60], queue-aware [60,0,0].
- 17 tests passed, including every-frame conservation/capacity, freshness,
  idempotence, mass/inertia, source hashes and all original protocol tests.
- Independent CUDA capture check: one parcel into each pot, one deliberate miss.
- Repeated featured GPU episode: all dose/decision metrics and task events equal;
  max qpos difference 2.03e-6, max qvel difference 1.78e-5 (not bitwise identical).
  See physical_garden/output/validation.json.

## Calibration, Not Hidden Success Selection

- ad51426: original physical pilot stopped at [60,60,0] because nozzle failed
  alignment at pot C. Full failed pilot retained.
- c57c933: measured-nozzle feedback and explicit tool inertia; still [60,60,0].
- Contact inspection identified bench-to-hip interference. Final bench front
  edge is x=0.18 m, previously 0.11 m. Pot centers and valve gate unchanged.
- Final clearance pilot and all nine final comparisons succeed physically.
  Task completion is still policy/profile dependent.
- Initial tool geom did not add mass to an explicitly inertial parent. Corrected
  with a separate fixed child body; tested 0.18 kg. This is disclosed in RESULTS.

## Boundaries

One calibrated scene, not reliability statistics or hardware validation.
Fixed wrist tool, ideal external pump, no hose tension/recoil/variable water mass.
Ballistic capture plane, not CFD, leaf interception, soil or plant growth.
Hand-authored IK plus feedback, not a trained policy.
Synthetic exact delivered-volume observations. In-memory IDs; no restart or
multi-owner guarantee. Freshness gates new coordination, not an underway dose.
No general claim that queue awareness is always superior.

## Media and Publishing

The new narrated/captioned movie is complete: 88 s, 1920x1080, 25 fps H264/AAC.
All 2,200 encoded frames decode; source hashes, speech/caption windows and frame
links pass. Both lost-receipt arms show all 850 retained observations; outage
replay shows 301/850 observations per arm, spanning the entire 34 s episode.
The third stable-ID arm is summarized from its retained run, not animated.
Movie: physical_garden/output/humanoid_gardening_gpu.mp4 (7,222,375 bytes).
SHA256: 76d0f127bbe9e8110759120ff6bca64f5cc6e66cdd7d42fd2156d0b3eb0081d9
Render/device distinctions are in movie_frames.json; encoding is CPU libx264.
Published release: gpu-watering-2026-10-24, targeting source commit
71d94b26e3c4ba9cf78b85c20ec8ff3952d7b0aa. GitHub's asset digest and size match
the local MP4 above. The remote README was read back and its featured image,
MP4 URL and measured comparison table verified. Publishing is complete.
https://github.com/rbajaj5/humanoid-gardening-queues/releases/tag/gpu-watering-2026-10-24

## Exact Resume / Reproduce Commands

Run from this repository. Local interpreter:
../.venv-laundry-gpu/Scripts/python.exe

```powershell
python -m pip install -r physical_garden/requirements.txt
python fetch_model.py
python -m physical_garden.run
python -m physical_garden.check_water
python -m unittest physical_garden.test_physics test_simulate -v
python -m physical_garden.analyze
python -m physical_garden.run --profile lost_receipts --policy queue_aware --prefix reproducibility_
python -m physical_garden.audit
python -m physical_garden.render
.\physical_garden\narrate.ps1 -Python python
python -m physical_garden.validate_media
```

CUDA requires the real NVIDIA device; the sandbox may require escalation.
No CPU fallback exists. Warp 1.17.0/CUDA12.9 works with driver577.13 here.
Do not update to Warp1.18/CUDA13 without checking driver compatibility.
Rendering uses Intel OpenGL and CPU libx264, independently of CUDA physics.
Initial CUDA compilation takes minutes. Later comparisons reuse the cache.
Do not launch duplicate rendering/simulation jobs; inspect running sessions first.

No changes were made to the laundry repo or the original RAG/Assured Autonomy
repositories. No private class corpus or credentials are included.
