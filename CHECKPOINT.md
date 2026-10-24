# Gardening Project Checkpoint

Created 2026-10-24 at the user's request as a separate public repository.

## Completed

- Established the project scope: humanoid gardening, starting with pot watering.
- Defined the task-level queue-awareness question and proposed evaluation metrics.
- Kept it independent of the laundry, Assured Autonomy and RAG repositories.
- Implemented CPU task-level watering simulation, common exogenous tapes, three
  policies, six profiles and 256 matched seeds: 4,608 episodes.
- All 18 preselected full replays regenerate exactly; nine tests pass for pairing,
  conservation, capacity, timestamp causality, deduplication and outage tradeoffs.
- Generated RESULTS.md from saved results. Preserved permanent-observation-loss
  failures, not only successful queue-aware cases.
- Added one schematic 42 s narrated/captioned MP4 and its frame index. This is
  task-level accounting/coordination, NOT a humanoid or fluid physics video.

## Not Yet Implemented

No articulated robot, realistic soil/fluid physics, GPU dynamics, hardware or
learned policy. Do not describe the task-level experiment as a gardening robot.

## Next Work

Integrate the laundry project's pinned humanoid model as a reference, with a new
gardening environment, actual tool states and realistic observation errors.
Keep the current protocol results separate. Investigate a hybrid that can use
trustworthy completion receipts during an observation outage; not tested yet.

Only publish assets with verified redistribution rights. No hardware commands,
real irrigation control, paid API calls or external accounts are configured.

## Resume / Reproduce

```powershell
git status --short
git log -5 --oneline
python simulate.py
python -m unittest -v
python analyze.py
python render.py
.\narrate.ps1 -Python python
python validate_media.py
```

Local development Python: ../.venv-laundry-gpu/Scripts/python.exe. This interpreter
is reused, but the gardening simulation itself runs on CPU and needs no GPU packages.
Render needs Pillow/FFmpeg and Windows fonts. Release: watering-coordination-v1.
Input seed 45100 was selected in config.json before outcomes; no parameter sweep.
Do not change retained results without rerunning analysis, tests, movie and hashes.
