# Synthetic Watering Results

18 complete replays of 4608 episodes: preselected seed 45100

CPU task-level simulation only. No humanoid, soil biology or fluid dynamics.

Success means all three requested doses delivered with at most 1 ml excess per pot at the 50 s endpoint.
Completion times below condition on reaching all requested doses, even if excess is later delivered;
they are not safe-completion times. SD describes seeded variation, not uncertainty about real gardens.

| Condition | Policy | Dose-safe completion | Excess ml, mean (SD) | Time to all doses, completed only |
| --- | --- | ---: | ---: | ---: |
| timely | timeout_new_id | 256/256 | 0.00 (0.00) | 8.20 s |
| timely | idempotent_receipt_only | 256/256 | 0.00 (0.00) | 8.20 s |
| timely | queue_aware | 256/256 | 0.00 (0.00) | 8.10 s |
| late_receipts | timeout_new_id | 0/256 | 295.80 (46.29) | 15.88 s |
| late_receipts | idempotent_receipt_only | 256/256 | 0.00 (0.00) | 14.91 s |
| late_receipts | queue_aware | 256/256 | 0.00 (0.00) | 8.10 s |
| lost_receipts | timeout_new_id | 0/256 | 895.86 (17.16) | not reached |
| lost_receipts | idempotent_receipt_only | 0/256 | 0.00 (0.00) | not reached |
| lost_receipts | queue_aware | 256/256 | 0.00 (0.00) | 8.10 s |
| temporary_sensor_outage | timeout_new_id | 256/256 | 0.00 (0.00) | 8.20 s |
| temporary_sensor_outage | idempotent_receipt_only | 256/256 | 0.00 (0.00) | 8.20 s |
| temporary_sensor_outage | queue_aware | 256/256 | 0.00 (0.00) | 15.39 s |
| permanent_sensor_outage | timeout_new_id | 256/256 | 0.00 (0.00) | 8.20 s |
| permanent_sensor_outage | idempotent_receipt_only | 256/256 | 0.00 (0.00) | 8.20 s |
| permanent_sensor_outage | queue_aware | 0/256 | 0.00 (0.00) | not reached |
| combined | timeout_new_id | 0/256 | 419.45 (145.76) | 20.67 s |
| combined | idempotent_receipt_only | 256/256 | 0.00 (0.00) | 17.92 s |
| combined | queue_aware | 256/256 | 0.00 (0.00) | 14.78 s |

## Interpretation

Stable command identity plus receiver deduplication removes duplicate dose execution in this model. Zero excess in the idempotent arms is structural under the fixed-dose and reliable-executor assumptions, not a learned discovery.

Fresh observed delivery permits progression without completion receipts. The receipt-only ablation shows that deduplication alone does not solve a lost-feedback liveness problem.

Observation gating also has a cost: a temporary outage delays the queue-aware controller; a permanent outage leaves the first dose delivered but unverified and two plants unfinished. Here truthful receipts could support a less conservative hybrid, but that hybrid was not tested.

The baseline treats a timeout as justification for a new action ID. It is an explicit failure-mode baseline, not a claim about every non-queue-aware controller. All arms share receiver deduplication, a serial executor, tank limits and the same exogenous message tape. No queued pour is silently canceled.

Profiles, seeds, doses and thresholds are in config.json. Per-episode outcomes are in output/episodes.csv. Missing completion times denote unfinished episodes and must not be replaced by zero. The first 18 complete replays were selected by seed before outcome analysis. No parameter search was performed.
