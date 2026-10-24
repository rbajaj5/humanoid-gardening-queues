# Humanoid Gardening Queues

A separate, simulation-only project for a humanoid performing useful gardening
tasks with queue-aware task coordination.

**Status: project scaffold. No gardening simulation, GPU result, learned policy
or hardware demonstration has been validated yet.** The first task will be
watering potted plants. A verified gardening MP4 will be featured here when the
physical task works; laundry footage will not be relabeled as gardening.

## First Task: Inspect, Water, Verify

Assume a capable humanoid body controller within a stated operating envelope.
Focus on task-level coordination, not arbitrary delays inside every joint:

1. Associate each pot with a persistent identity and a timestamped moisture reading.
2. Select a plant and reserve a bounded water dose from the available supply.
3. Pick up the watering tool, approach the pot, and deliver the authorized dose.
4. Verify delivered water and tool state before releasing the reservation.
5. Re-observe the plant before authorizing another dose.

A missing acknowledgement must not be interpreted as "no water was delivered."
Retransmission should preserve command identity; an uncertain in-progress dose
should block a conflicting second watering action. Expired sensor readings
should cause a new observation or an explicit hold, not an invented moisture value.

## Planned Experiment

Compare a receipt-timeout baseline with a queue-aware supervisor under the same
initial plant states, command schedule and disturbance tape. Measure delivered
dose error, duplicate watering, spill volume, tank conservation, completion time
and holds. Use synthetic plant/water models with explicit units and limitations.

The first physical demonstration should show one mass-bearing humanoid, one
watering tool and a few fixed pots. GPU dynamics, if used, will be identified
separately from rendering. A simple measured-dose surrogate should be labeled as
such; it is not fluid dynamics or a validated plant-health model.

## Related but Independent

- [Humanoid Laundry Queues](https://github.com/rbajaj5/humanoid-laundry-queues):
  predecessor for articulated-body modeling and task receipt/completion separation.
- [Assured Autonomy Lab](https://github.com/rbajaj5/delay-aware-runtime-assurance-lab):
  queue-aware assurance research; its numerical results are not gardening results.
- [Assured Autonomy RAG](https://github.com/rbajaj5/assured-autonomy-rag):
  literature retrieval and source provenance, not a robot controller.

This is not a subdirectory or branch of those repositories. No private class
corpus, credentials, external model weights or results have been copied here.

See [CHECKPOINT.md](CHECKPOINT.md) for the current implementation boundary.

## License

MIT for original project material. Any future robot models, meshes, datasets and
learned weights must retain their own licenses and pinned provenance.
