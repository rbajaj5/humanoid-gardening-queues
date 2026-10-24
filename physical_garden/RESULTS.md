# GPU Humanoid Watering Results

One calibrated scene, seed 45100; nine GPU episodes.
These are mechanism demonstrations, not success-rate estimates.

| Receipt / observation profile | Policy | Pots at target | Delivered ml (A, B, C) | Excess ml | Dose-safe task |
|---|---|---:|---|---:|---|
| timely | timeout_new_id | 3/3 | [60, 60, 60] | 0 | True |
| timely | idempotent_receipt_only | 3/3 | [60, 60, 60] | 0 | True |
| timely | queue_aware | 3/3 | [60, 60, 60] | 0 | True |
| lost_receipts | timeout_new_id | 1/3 | [300, 0, 0] | 240 | False |
| lost_receipts | idempotent_receipt_only | 1/3 | [60, 0, 0] | 0 | False |
| lost_receipts | queue_aware | 3/3 | [60, 60, 60] | 0 | True |
| permanent_observation_loss | timeout_new_id | 3/3 | [60, 60, 60] | 0 | True |
| permanent_observation_loss | idempotent_receipt_only | 3/3 | [60, 60, 60] | 0 | True |
| permanent_observation_loss | queue_aware | 1/3 | [60, 0, 0] | 0 | False |

The identical joint controller executes all arms. Only task coordination changes.
Stable IDs prevent repeated pours. Fresh captured-volume observations allow advancement
without a completion receipt. That combination is not intrinsically always better:
when observations disappear permanently, the tested queue-aware policy stops advancing
even when completion receipts remain available. This is a deliberate, retained limitation.

The nozzle is a 0.18 kg rigid wrist attachment. Water comes from an external ideal
reservoir and is represented by CUDA ballistic 1 ml parcels, not a fluid solver. Capture
is computed from soil-plane crossings, not from the desired pot label. No hardware,
plant growth, flexible hose, tactile grasp, or trained policy validation is claimed.

Full qpos/qvel/control arrays and every 25 Hz observation are retained. The movie
replays the lost-receipt case and the observation-outage counterexample, with every
video frame mapped to a retained state; it is not a separate animation of planned poses.

## Calibration history

The first pilot delivered [60, 60, 0] ml and failed the third-pot tool alignment
gate. A feedback pilot also failed [60, 60, 0] ml. Both logs are retained; the
original sources are commits ad51426 and c57c933. Inspection found bench-to-hip
contact. The final bench's front edge moved from x=0.11 to x=0.18 m; pot
locations and the 0.025 m valve gate did not change. Measured-nozzle feedback
also remains in the final controller. These are calibrated exploratory results.

The first pilot's tool geom did not add mass because its parent had explicit
inertia. The final tool has its own fixed child body with 0.18 kg mass, which
is included in the 33.521142 kg robot-plus-tool mass and checked by a test.
