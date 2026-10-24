# Humanoid Gardening Queues

**A mass-bearing humanoid waters three plants in GPU physics, while three task
coordinators handle the same missing receipts and observation failures.**

[![Watch the GPU humanoid watering comparison](physical_garden/output/preview_300.jpg)](https://github.com/rbajaj5/humanoid-gardening-queues/releases/download/gpu-watering-2026-10-24/humanoid_gardening_gpu.mp4)

**[Watch the new narrated, captioned MP4 (88 seconds, 1080p)](https://github.com/rbajaj5/humanoid-gardening-queues/releases/download/gpu-watering-2026-10-24/humanoid_gardening_gpu.mp4)**

Synthetic simulation only. The humanoid's free base, joints, actuator limits,
mass distribution and ground contacts are integrated with **MuJoCo Warp on an
NVIDIA GeForce RTX 5070 Ti Laptop GPU**. A 0.18 kg wrist-mounted watering tool is
part of the dynamics. CUDA ballistic water parcels depart from the measured
nozzle position and count as delivered only when they cross a pot's capture region.
This is **not CFD, soil simulation, a learned manipulation policy or hardware evidence**.
Rendering and video encoding are separate from the GPU physics.

## What the Comparison Tests

All arms use the same articulated robot controller, scene, seed, disturbances,
60 ml targets, 500 ml external reservoir and serial executor. Only coordination changes:

| Policy | Retry identity | Advances to next plant using |
|---|---|---|
| Timeout baseline | New command ID | Completion receipt |
| Idempotent ablation | Same command ID | Completion receipt |
| Queue-aware | Same command ID | Fresh observed water delivery |

When a completion receipt is lost, a new ID can produce a second physical pour.
A stable ID prevents duplicate work. Fresh captured-volume observations can also
allow progress to the next plant without waiting for that receipt. **These are two
separate mechanisms**, not a general claim that awareness always improves safety.

Measured delivery after 34 seconds with all completion receipts lost:

| Controller | Pot A | Pot B | Pot C | Excess delivery |
|---|---:|---:|---:|---:|
| Timeout / new ID | 300 ml | 0 ml | 0 ml | 240 ml |
| Stable ID / receipts only | 60 ml | 0 ml | 0 ml | 0 ml |
| Queue-aware / observed delivery | 60 ml | 60 ml | 60 ml | 0 ml |

The movie also shows the counterexample: when observations disappear but receipts
work, the tested queue-aware policy holds rather than advancing. A hybrid that can
use either trustworthy evidence channel is future work, not an implemented result.

**[Measured GPU results and calibration history](physical_garden/RESULTS.md)**
cover nine episodes: three policies by three communication profiles, one seed.
These are illustrative mechanism checks, **not nine independent samples of a
population**, a reliability estimate, or a new optimality theorem. The initial
alignment failures are preserved rather than omitted from the development record.

## Physical Model and Boundaries

- Unitree G1: 29 actuated joints, free base, 33.521142 kg including the fixed tool.
- Hand-authored IK targets, measured-nozzle feedback and ankle balance feedback;
  there is no scripted root motion or rendered-only robot trajectory.
- Rigid-body integration: 2 ms. Task controller and retained observations: 40 ms.
  The movie's body-tilt measurement is the free-base/pelvis tilt, not torso-joint lean.
- Water: 1 ml ballistic parcels, 10 ms CUDA integration, gravity and matched small
  velocity disturbances. No particle pressure, surface tension or leaf interception.
- Fixed wrist attachment, not dexterous finger grasping. Ideal external pump:
  no flexible hose forces, pressure dynamics, recoil or changing payload mass.
- Pots use a geometric capture plane, finite storage and overflow accounting;
  delivered volume is a synthetic dosing criterion, not horticultural advice.
- Retries every 7 s, command delay 0.12 s, observation delay 0.12 s, freshness
  limit 0.5 s. Low-level skills already underway are not aborted on observation loss.
- Receipt loss means completion receipts never arrive within the episode.
  The observation-outage profile stops observations after 1 s; receipts still work.
- Captured-volume observations are exact when available. Identity confusion,
  sensor bias, persistent ID storage, robot falls outside this calibrated setup,
  distributed ownership and hardware failures need separate experiments.

Zero excess with a stable ID follows from one bounded dose per pot, deduplication
and this executor. It is not inferred from visual appearance or an ML safety proof.

## Inspect the Evidence

- [Configuration](physical_garden/config.json), [physical scene](physical_garden/model.py),
  [CUDA runner and coordination](physical_garden/run.py), [GPU water kernel](physical_garden/water.py).
- [All nine summaries](physical_garden/output/comparison.json),
  [physical audit tests](physical_garden/test_physics.py),
  [17-test and repeatability record](physical_garden/output/validation.json).
- Every episode retains full 25 Hz joint positions, velocities and commands in
  NPZ, and observations, droplets and network events in JSON under
  [physical_garden/output](physical_garden/output).
- [Video-to-state index](physical_garden/output/movie_frames.json),
  [encoded-media validation](physical_garden/output/media_validation.json).
  The lost-receipt replay shows all 850 logged states per displayed arm. The
  observation-outage replay spans all 34 seconds but is temporally subsampled;
  exact indices are recorded. No planned poses replace measured dynamics.
- [Pinned model provenance](output/model_manifest.json) and
  [third-party license](THIRD_PARTY_NOTICES.md). Upstream meshes are fetched, not vendored.

## Reproduce

Python 3.11, compatible NVIDIA CUDA driver, FFmpeg/FFprobe, and Windows fonts/speech
for the supplied movie workflow. There is **no silent CPU physics fallback**.
The pinned Warp 1.17.0 build uses CUDA 12.9 and worked with driver 577.13 here.
Initial kernel compilation can take several minutes; later runs use the cache.

```powershell
python -m pip install -r physical_garden/requirements.txt
python fetch_model.py
python -m physical_garden.run
python -m physical_garden.check_water
python -m unittest physical_garden.test_physics test_simulate -v
python -m physical_garden.analyze
python -m physical_garden.render
.\physical_garden\narrate.ps1 -Python python
python -m physical_garden.validate_media
```

To rerun one case without overwriting the retained comparison:

```powershell
python -m physical_garden.run --profile lost_receipts --policy queue_aware --prefix rerun_
```

## Earlier Task-Level Evidence

The original **4,608 CPU protocol episodes remain unchanged**. They are a separate,
larger task-state study, not GPU physics runs. Their configuration, results,
18 full replays and original schematic movie are documented in
[TASK_COORDINATION.md](TASK_COORDINATION.md) and [RESULTS.md](RESULTS.md).
Do not combine their sample count with the nine physical episodes.

This is an independent repository. Related projects:
[Humanoid Laundry Queues](https://github.com/rbajaj5/humanoid-laundry-queues),
[Assured Autonomy Lab](https://github.com/rbajaj5/delay-aware-runtime-assurance-lab),
[Assured Autonomy RAG](https://github.com/rbajaj5/assured-autonomy-rag).
Their numerical results are not relabeled as gardening evidence.

Original code is MIT licensed. The pinned G1 model is BSD-3-Clause; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Neither Unitree nor Google DeepMind
endorses this project. [CHECKPOINT.md](CHECKPOINT.md) records the implementation state.
