# GPU humanoid watering: queue-aware task coordination

One new narrated/captioned 88-second 1080p MP4, rendered from retained CUDA states.

- MuJoCo Warp integrates a free-base, 29-actuator G1 with a 0.18 kg wrist tool.
- Warp integrates ballistic water parcels. Actual capture-plane crossings, not
  commanded plant labels, determine delivered volumes.
- Nine matched final episodes: three coordination policies, three communication
  profiles, one calibrated scene and seed 45100. Full joint states and logs retained.
- With completion receipts lost: new-ID retries delivered [300,0,0] ml;
  stable-ID/receipt-only delivered [60,0,0]; queue-aware delivered [60,60,60].
- With observations permanently lost but receipts working, queue-aware delivered
  only [60,0,0], while receipt-driven arms delivered [60,60,60].
- 17 tests passed, plus an independent GPU capture/miss check. Repeated featured
  episode reproduced every task event, decision and dose metric within documented
  floating-point state tolerances.

The original 4,608 CPU protocol episodes remain separate and unchanged. Two failed
physical calibration pilots are retained, with their source commits and explanations.

Limitations: fixed wrist attachment, hand-authored control, ideal external pump,
ballistic water rather than CFD, no soil/leaf/plant-growth modeling, synthetic exact
delivery observations, in-memory deduplication, no hardware validation or reliability
estimate. Unitree and Google DeepMind do not endorse this project. The G1 model is
BSD-3-Clause; see THIRD_PARTY_NOTICES.md in the repository.

The MP4 is the single featured movie. comparison.json contains measured summaries;
validation.json and media_validation.json record checks and provenance. For full
traces, source and exact reproduction commands, see the repository README.
