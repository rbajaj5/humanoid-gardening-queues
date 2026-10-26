# Engineering Memory and Queue-Aware Physical Actions

One 60-second, 1920x1080, 25 fps MP4 with bilingual labels and English explanatory
captions (silent). Robot dynamics and ballistic water use CUDA; task logic,
rendering and encoding are separate. Synthetic simulation, not hardware or
vendor validation.

The reproducible suite contains 40 episodes: five scenarios, four execution
policies, two matched seeds. It separates stable command identity, evidence-age
checks and shared queued-dose budgets. Both seeds produced these mechanism checks:

- Plan replay: stable IDs prevent a second dose.
- Shared snapshot: two planners with distinct IDs need a shared committed-dose
  budget to avoid delivering 120 ml to each 60 ml target.
- Stale recall: timestamps prevent an old observation from authorizing a new dose.
- Observation outage: freshness-gated policies deliver 60/0/0 ml and hold 34.28 s;
  unguarded policies deliver 60/60/60 ml. This availability cost is retained.

The shared-planner case uses one physical humanoid. The video shows seed 45110
only, sampling 251/1000 states per illustrated episode across its full duration.
Results for both seeds, all trajectories, code, configuration and audit artifacts
are in `memory_study/` at the release source commit. The root README links them.

Validation: 27 tests; independent audit of 40,000 states; all 1,500 encoded frames
decode; source links and ten sampled decoded-frame comparisons checked.

MP4: `engineering_memory_gpu.mp4` (4,941,150 bytes).
SHA256: `238c1c137859a9584f7087706bf813c1e8954bba5c3ce70d0d04ab8592898549`.

Exploratory mechanism evidence, not a reliability estimate or a claim that
queue awareness is always better. All earlier repository studies are preserved.
