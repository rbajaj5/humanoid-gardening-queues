# GPU Memory Study: Measured Results

Exploratory synthetic physics, not vendor or hardware validation.

| Profile | Policy | Runs | Target-dose successes | Mean excess ml | Mean shortfall ml | Mean hold s |
|---|---|---:|---:|---:|---:|---:|
| nominal | memory_only | 2 | 2 | 0.0 | 0.0 | 0.00 |
| nominal | idempotent | 2 | 2 | 0.0 | 0.0 | 0.00 |
| nominal | identity_freshness | 2 | 2 | 0.0 | 0.0 | 0.00 |
| nominal | queue_aware | 2 | 2 | 0.0 | 0.0 | 0.00 |
| checkpoint_replay | memory_only | 2 | 0 | 180.0 | 0.0 | 0.00 |
| checkpoint_replay | idempotent | 2 | 2 | 0.0 | 0.0 | 0.00 |
| checkpoint_replay | identity_freshness | 2 | 2 | 0.0 | 0.0 | 0.00 |
| checkpoint_replay | queue_aware | 2 | 2 | 0.0 | 0.0 | 0.00 |
| shared_snapshot | memory_only | 2 | 0 | 180.0 | 0.0 | 0.00 |
| shared_snapshot | idempotent | 2 | 0 | 180.0 | 0.0 | 0.00 |
| shared_snapshot | identity_freshness | 2 | 0 | 180.0 | 0.0 | 0.00 |
| shared_snapshot | queue_aware | 2 | 2 | 0.0 | 0.0 | 0.00 |
| stale_recall | memory_only | 2 | 0 | 180.0 | 0.0 | 0.00 |
| stale_recall | idempotent | 2 | 0 | 180.0 | 0.0 | 0.00 |
| stale_recall | identity_freshness | 2 | 2 | 0.0 | 0.0 | 0.00 |
| stale_recall | queue_aware | 2 | 2 | 0.0 | 0.0 | 0.00 |
| observation_outage | memory_only | 2 | 2 | 0.0 | 0.0 | 0.00 |
| observation_outage | idempotent | 2 | 2 | 0.0 | 0.0 | 0.00 |
| observation_outage | identity_freshness | 2 | 0 | 0.0 | 120.0 | 34.28 |
| observation_outage | queue_aware | 2 | 0 | 0.0 | 120.0 | 34.28 |
